"""Проверка параметров, заданных пользователем в командной строке.

Каждая функция проверяет одно значение и возвращает текст ошибки на
русском языке или пустую строку, если значение допустимо. Функции не
обращаются к сети: на этапе 1 проверяется только форма значений и
наличие локальных файлов и каталогов.
"""
import os
import re
from urllib.parse import urlparse

MODE_REMOTE = "remote"
MODE_TEST = "test"
MODES = (MODE_REMOTE, MODE_TEST)
LATEST_VERSION = "latest"
IMAGE_EXTENSION = ".svg"
URL_SCHEMES = ("http", "https")
MAX_CRATE_NAME_LENGTH = 64

CRATE_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
TEST_PACKAGE_RE = re.compile(r"[A-Z]+")
FILTER_RE = re.compile(r"[A-Za-z0-9_-]+")
SEMVER_RE = re.compile(
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?"
    r"(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?"
)


def validate_mode(mode):
    """Проверить режим работы: remote (URL) или test (файл)."""
    if mode not in MODES:
        return ("неизвестный режим «" + mode + "», допустимые значения: "
                + ", ".join(MODES))
    return ""


def validate_package(name, mode):
    """Проверить имя пакета с учётом режима работы.

    В режиме remote имя должно соответствовать правилам crates.io:
    от 1 до 64 символов, латинские буквы, цифры, ``-`` и ``_``, первый
    символ — буква. В режиме test пакеты называются большими
    латинскими буквами.
    """
    if not name:
        return "имя пакета не может быть пустым"
    if mode == MODE_TEST:
        if not TEST_PACKAGE_RE.fullmatch(name):
            return ("в тестовом режиме имя пакета состоит из больших "
                    "латинских букв, получено «" + name + "»")
        return ""
    if len(name) > MAX_CRATE_NAME_LENGTH:
        return ("имя пакета длиннее " + str(MAX_CRATE_NAME_LENGTH)
                + " символов")
    if not CRATE_NAME_RE.fullmatch(name):
        return ("недопустимое имя пакета «" + name + "»: разрешены "
                "латинские буквы, цифры, «-» и «_», первый символ — буква")
    return ""


def validate_repo(repo, mode):
    """Проверить источник данных с учётом режима работы.

    В режиме remote это URL-адрес со схемой http или https, в режиме
    test — путь к существующему файлу тестового репозитория, доступному
    для чтения.
    """
    if not repo:
        return "адрес репозитория не может быть пустым"
    if mode == MODE_TEST:
        return validate_test_file(repo)
    return validate_url(repo)


def validate_url(url):
    """Проверить, что строка — URL-адрес со схемой http или https."""
    if any(char.isspace() for char in url):
        return "URL-адрес не может содержать пробелы: «" + url + "»"
    parsed = urlparse(url)
    if parsed.scheme not in URL_SCHEMES:
        return ("URL-адрес должен начинаться с http:// или https://, "
                "получено «" + url + "»")
    if not parsed.netloc:
        return "в URL-адресе не указан сервер: «" + url + "»"
    return ""


def validate_test_file(path):
    """Проверить файл тестового репозитория: существует и читается."""
    if not os.path.exists(path):
        return "файл тестового репозитория не найден: " + path
    if not os.path.isfile(path):
        return "путь к тестовому репозиторию не является файлом: " + path
    if not os.access(path, os.R_OK):
        return "нет прав на чтение файла тестового репозитория: " + path
    return ""


def validate_version(version):
    """Проверить версию пакета: SemVer ``X.Y.Z`` или ``latest``."""
    if not version:
        return "версия пакета не может быть пустой"
    if version == LATEST_VERSION or SEMVER_RE.fullmatch(version):
        return ""
    return ("неверная версия «" + version + "»: ожидается формат "
            "X.Y.Z (например, 1.0.2 или 0.4.0-beta.1) или " + LATEST_VERSION)


def validate_output(path):
    """Проверить имя файла с изображением графа.

    Файл должен иметь расширение .svg, не быть каталогом, а каталог,
    в котором он будет создан, должен существовать и быть доступен
    для записи.
    """
    if not path:
        return "имя файла с изображением не может быть пустым"
    if not path.lower().endswith(IMAGE_EXTENSION):
        return ("файл с изображением должен иметь расширение "
                + IMAGE_EXTENSION + ", получено «" + path + "»")
    if os.path.isdir(path):
        return "по пути файла с изображением находится каталог: " + path
    directory = os.path.dirname(path) or os.curdir
    if not os.path.isdir(directory):
        return "каталог для файла с изображением не существует: " + directory
    if not os.access(directory, os.W_OK):
        return "нет прав на запись в каталог: " + directory
    return ""


def validate_filter(substring):
    """Проверить подстроку фильтрации пакетов.

    Подстрока необязательна (None — фильтр не задан). Заданная
    подстрока должна быть непустой и состоять из символов, допустимых
    в именах пакетов, иначе она не совпадёт ни с одним пакетом.
    """
    if substring is None:
        return ""
    if not substring:
        return "подстрока фильтрации не может быть пустой"
    if not FILTER_RE.fullmatch(substring):
        return ("недопустимая подстрока фильтрации «" + substring
                + "»: разрешены латинские буквы, цифры, «-» и «_»")
    return ""
