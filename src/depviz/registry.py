"""Получение прямых зависимостей пакета Cargo из репозитория (этап 2).

Репозиторий — sparse-индекс реестра Cargo, например
``https://index.crates.io``. Файл индекса пакета содержит по одной
JSON-строке на каждую опубликованную версию, в строке перечислены
зависимости этой версии. Менеджеры пакетов и сторонние библиотеки не
используются: файл загружается модулем urllib и разбирается модулем
json из стандартной библиотеки.

Перед загрузкой файла пакета проверяется, что по URL действительно
находится индекс: в его корне должен быть файл ``config.json`` с полем
``dl`` (адрес загрузки архивов пакетов).

Путь к файлу пакета строится по правилам Cargo:
``1/{имя}``, ``2/{имя}``, ``3/{первая буква}/{имя}`` для имён из 1–3
символов и ``{ab}/{cd}/{имя}`` для остальных, имя в нижнем регистре.
"""
import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass

from depviz.semver import VersionError, is_prerelease, version_key
from depviz.validators import LATEST_VERSION

HTTP_NOT_FOUND = 404
TIMEOUT_SECONDS = 15
USER_AGENT = "depviz/0.2 (educational project, configuration management)"
SHORT_NAME_LENGTHS = (1, 2)
THREE_LETTER_NAME = 3
KIND_ORDER = ("normal", "build", "dev")
DEFAULT_KIND = "normal"
INDEX_CONFIG = "config.json"
INDEX_DOWNLOAD_KEY = "dl"
INDEX_HINT = "нужен sparse-индекс, например https://index.crates.io"


class DataError(Exception):
    """Ошибка получения или разбора данных о зависимостях."""


class ConnectionFailed(DataError):
    """Не удалось связаться с сервером репозитория."""


@dataclass
class Dependency:
    """Прямая зависимость версии пакета.

    name — имя, под которым зависимость указана в Cargo.toml, package —
    настоящее имя пакета в реестре (отличается при переименовании).
    """

    name: str
    req: str
    kind: str = DEFAULT_KIND
    optional: bool = False
    target: str = ""
    package: str = ""

    def crate(self):
        """Вернуть настоящее имя пакета в реестре."""
        return self.package or self.name


def index_path(name):
    """Вернуть путь к файлу пакета в sparse-индексе Cargo."""
    name = name.lower()
    if len(name) in SHORT_NAME_LENGTHS:
        return str(len(name)) + "/" + name
    if len(name) == THREE_LETTER_NAME:
        return "3/" + name[0] + "/" + name
    return name[:2] + "/" + name[2:4] + "/" + name


def index_url(repo, name):
    """Вернуть URL файла пакета name в репозитории repo."""
    return repo.rstrip("/") + "/" + index_path(name)


def fetch_text(url):
    """Загрузить текст по URL-адресу, сообщая об ошибках по-русски.

    Ответ 404 означает, что пакета в репозитории нет.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as reply:
            return reply.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        if error.code == HTTP_NOT_FOUND:
            raise DataError("пакет не найден в репозитории (" + url + ")")
        raise DataError("репозиторий вернул ошибку HTTP " + str(error.code)
                        + " для " + url)
    except (urllib.error.URLError, socket.timeout, OSError) as error:
        reason = getattr(error, "reason", error)
        raise ConnectionFailed("не удалось подключиться к репозиторию: "
                               + str(reason))
    except UnicodeDecodeError:
        raise DataError("ответ репозитория не в кодировке UTF-8: " + url)


def check_index(repo, fetch=None):
    """Проверить, что repo — sparse-индекс Cargo (есть config.json с dl)."""
    fetch = fetch or fetch_text
    url = repo.rstrip("/") + "/" + INDEX_CONFIG
    try:
        config = json.loads(fetch(url))
    except ConnectionFailed:
        raise
    except (DataError, json.JSONDecodeError):
        raise DataError("по адресу " + repo + " нет индекса Cargo; "
                        + INDEX_HINT)
    if not isinstance(config, dict) or INDEX_DOWNLOAD_KEY not in config:
        raise DataError("по адресу " + repo + " нет индекса Cargo: в "
                        + INDEX_CONFIG + " нет поля " + INDEX_DOWNLOAD_KEY)


def parse_index(text, name):
    """Разобрать файл индекса пакета в список записей о версиях."""
    entries = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            raise DataError("неверный формат индекса пакета " + name
                            + ": строка " + str(number) + " не JSON; "
                            + INDEX_HINT)
        if not isinstance(entry, dict) or "vers" not in entry:
            raise DataError("неверный формат индекса пакета " + name
                            + ": в строке " + str(number) + " нет версии")
        entries.append(entry)
    if not entries:
        raise DataError("в индексе пакета " + name + " нет ни одной версии")
    return entries


def select_version(entries, version):
    """Выбрать запись о версии пакета: точную версию или ``latest``."""
    if version == LATEST_VERSION:
        return latest_version(entries)
    return exact_version(entries, version)


def exact_version(entries, version):
    """Найти запись о заданной версии или сообщить о её отсутствии."""
    for entry in entries:
        if entry["vers"] == version:
            return entry
    raise DataError("версия " + version + " не найдена, последние версии: "
                    + ", ".join(recent_versions(entries)))


def latest_version(entries):
    """Выбрать последнюю версию так же, как Cargo.

    Берётся наибольшая по SemVer неотозванная (не yanked) версия;
    пререлизы рассматриваются, только если других версий нет.
    """
    available = [entry for entry in entries
                 if is_semver(entry["vers"]) and not entry.get("yanked")]
    if not available:
        raise DataError("все версии пакета отозваны (yanked)")
    stable = [entry for entry in available
              if not is_prerelease(entry["vers"])]
    return max(stable or available, key=entry_version_key)


def entry_version_key(entry):
    """Ключ сортировки записи индекса по версии SemVer."""
    return version_key(entry["vers"])


def is_semver(text):
    """Проверить, что строка из индекса — версия SemVer."""
    try:
        version_key(text)
    except VersionError:
        return False
    return True


def recent_versions(entries, count=5):
    """Вернуть count последних по SemVer версий для подсказки."""
    versions = [entry["vers"] for entry in entries
                if is_semver(entry["vers"])]
    return sorted(versions, key=version_key)[-count:]


def make_dependency(raw):
    """Создать Dependency из JSON-описания зависимости в индексе."""
    return Dependency(
        name=raw["name"],
        req=raw.get("req", "*"),
        kind=raw.get("kind") or DEFAULT_KIND,
        optional=bool(raw.get("optional")),
        target=raw.get("target") or "",
        package=raw.get("package") or "",
    )


def dependency_sort_key(dependency):
    """Ключ сортировки: вид зависимости (normal, build, dev), имя, платформа."""
    kind = dependency.kind
    order = KIND_ORDER.index(kind) if kind in KIND_ORDER else len(KIND_ORDER)
    return order, dependency.name, dependency.target


def sort_dependencies(dependencies):
    """Упорядочить зависимости: normal, build, dev, затем по имени."""
    return sorted(dependencies, key=dependency_sort_key)


def remote_dependencies(repo, name, version, fetch=None):
    """Получить прямые зависимости пакета из репозитория.

    Возвращает пару (выбранная запись о версии, список Dependency).
    Параметр fetch позволяет подменить загрузку в тестах.
    """
    fetch = fetch or fetch_text
    check_index(repo, fetch)
    entries = parse_index(fetch(index_url(repo, name)), name)
    entry = select_version(entries, version)
    try:
        dependencies = [make_dependency(raw) for raw in entry.get("deps", [])]
    except (KeyError, TypeError, AttributeError):
        raise DataError("неверный формат зависимостей версии "
                        + entry["vers"])
    return entry, sort_dependencies(dependencies)
