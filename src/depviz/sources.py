"""Источники данных для построения графа: crates.io и тестовый файл.

Оба источника предоставляют методы root, dependencies и resolve,
которые использует depviz.graph.build_graph.
"""
from depviz.cfgexpr import can_be_enabled
from depviz.graph import Package
from depviz.registry import (ConnectionFailed, DataError, check_index,
                             fetch_text, index_url, is_semver, make_dependency,
                             parse_index, select_version)
from depviz.semver import version_key
from depviz.testing_repo import load_test_repo
from depviz.versionreq import RequirementError, matches

FOLLOWED_KINDS = ("normal", "build")


def is_followed(dependency):
    """Учитывать ли зависимость в графе (вид, optional, платформа)."""
    return (dependency.kind in FOLLOWED_KINDS and not dependency.optional
            and can_be_enabled(dependency.target))


class RemoteSource:
    """Пакеты из sparse-индекса Cargo по URL.

    Учитываются обычные и build-зависимости, кроме необязательных
    (optional): без разрешения features нельзя сказать, будут ли они
    подключены. dev-зависимости нужны только для тестов самого пакета
    и в граф не входят — Cargo тоже не собирает dev-зависимости
    зависимостей. Граф строится для всех платформ: зависимость с
    условием cfg(...) отбрасывается, только если условие ложно на любой
    платформе (например, cfg(any())).

    Файл индекса каждого пакета загружается один раз (кэш entries).
    """

    def __init__(self, repo, fetch=None):
        """Запомнить репозиторий и проверить, что это индекс Cargo."""
        self.repo = repo
        self.fetch = fetch or fetch_text
        self.entries = {}
        self.problems = []
        check_index(repo, self.fetch)

    def versions(self, name):
        """Записи индекса о всех версиях пакета (с кэшированием)."""
        if name not in self.entries:
            text = self.fetch(index_url(self.repo, name))
            self.entries[name] = parse_index(text, name)
        return self.entries[name]

    def root(self, name, version):
        """Корневой пакет: точная версия или последняя (latest)."""
        entry = select_version(self.versions(name), version)
        return Package(entry["name"], entry["vers"])

    def entry(self, package):
        """Запись индекса о выбранной версии пакета."""
        for entry in self.versions(package.name):
            if entry["vers"] == package.version:
                return entry
        raise DataError("версия " + package.version + " пакета "
                        + package.name + " пропала из индекса")

    def dependencies(self, package):
        """Пары (имя пакета, требование) учитываемых зависимостей."""
        result = []
        for raw in self.entry(package).get("deps", []):
            dependency = make_dependency(raw)
            if is_followed(dependency):
                result.append((dependency.crate(), dependency.req))
        return result

    def resolve(self, name, requirement):
        """Выбрать наибольшую неотозванную версию по требованию.

        Если пакета нет в индексе или ни одна версия не подходит,
        причина добавляется в problems и возвращается None. Ошибка
        подключения к серверу прерывает построение графа.
        """
        try:
            candidates = [entry for entry in self.versions(name)
                          if is_semver(entry["vers"])
                          and not entry.get("yanked")
                          and matches(requirement, entry["vers"])]
        except ConnectionFailed:
            raise
        except (DataError, RequirementError) as error:
            self.problems.append(name + " " + requirement + ": "
                                 + str(error))
            return None
        if not candidates:
            self.problems.append(name + " " + requirement
                                 + ": нет подходящей версии")
            return None
        best = max(candidates, key=lambda entry: version_key(entry["vers"]))
        return Package(best["name"], best["vers"])


class FileSource:
    """Пакеты из файла тестового репозитория (режим test).

    Версий в тестовом репозитории нет. Зависимость, которая не описана
    в файле, считается ошибкой, но только когда до неё доходит обход:
    пакет, исключённый фильтром, описывать не обязательно.
    """

    def __init__(self, path):
        """Прочитать файл тестового репозитория."""
        self.path = path
        self.graph = load_test_repo(path)
        self.problems = []

    def root(self, name, version):
        """Корневой пакет; версия в тестовом режиме не используется."""
        self.check(name, "")
        return Package(name)

    def check(self, name, parent):
        """Проверить, что пакет описан в файле."""
        if name not in self.graph:
            where = " (зависимость " + parent + ")" if parent else ""
            raise DataError("пакет " + name + where + " не описан в "
                            "тестовом репозитории " + self.path)

    def dependencies(self, package):
        """Пары (имя, пустое требование) прямых зависимостей пакета."""
        return [(name, "") for name in self.graph[package.name]]

    def resolve(self, name, requirement):
        """Пакет-зависимость; проверяется, что он описан в файле."""
        parents = [parent for parent, children in self.graph.items()
                   if name in children]
        self.check(name, parents[0] if parents else "")
        return Package(name)
