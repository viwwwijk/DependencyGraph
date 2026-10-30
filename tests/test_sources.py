"""Модульные тесты для depviz.sources (без обращения к сети)."""
import json
import os
import unittest

from depviz.graph import Package, build_graph
from depviz.registry import ConnectionFailed, DataError, index_path
from depviz.sources import FileSource, RemoteSource

REPO = "https://index.example.org"
GRAPHS = os.path.join(os.path.dirname(__file__), os.pardir, "examples",
                      "graphs")


def dep(name, req, **extra):
    """Описание зависимости в формате индекса."""
    return dict({"name": name, "req": req, "kind": "normal",
                 "optional": False, "target": None}, **extra)


def lines(name, *versions):
    """Файл индекса: пары (версия, зависимости[, yanked])."""
    return "\n".join(json.dumps({"name": name, "vers": item[0],
                                 "deps": item[1],
                                 "yanked": item[2] if item[2:] else False})
                     for item in versions)


class FakeRepo:
    """Подмена загрузки с подсчётом запросов."""

    def __init__(self, packages):
        """packages — {имя: текст файла индекса}."""
        self.files = {REPO + "/config.json": '{"dl": "x"}'}
        for name, text in packages.items():
            self.files[REPO + "/" + index_path(name)] = text
        self.urls = []

    def __call__(self, url):
        """Вернуть файл или сообщить, что пакета нет."""
        self.urls.append(url)
        if url not in self.files:
            raise DataError("пакет не найден в репозитории")
        return self.files[url]


class RemoteSourceTest(unittest.TestCase):
    """Проверка источника данных из индекса Cargo."""

    def setUp(self):
        """Репозиторий с пакетами app, core, util, mock."""
        self.fetch = FakeRepo({
            "app": lines("app", ("1.0.0", [
                dep("core", "^1.1"),
                dep("util_alias", "^0.2", package="util"),
                dep("mock", "^1", kind="dev"),
                dep("opt", "^1", optional=True),
                dep("never", "^1", target="cfg(any())"),
                dep("win", "^1", target="cfg(windows)"),
                dep("core", "^1.1", kind="build"),
            ])),
            "core": lines("core", ("1.0.0", []), ("1.1.0", []),
                          ("1.2.0", [dep("util", "~0.2.0")]),
                          ("1.3.0", [], True), ("2.0.0", [])),
            "util": lines("util", ("0.2.0", []), ("0.2.5", []),
                          ("0.3.0", [])),
            "win": lines("win", ("1.0.0", [])),
        })
        self.source = RemoteSource(REPO, self.fetch)

    def test_followed_dependencies(self):
        """Учитываются normal и build, кроме optional и cfg(any())."""
        deps = self.source.dependencies(Package("app", "1.0.0"))
        self.assertEqual(deps, [("core", "^1.1"), ("util", "^0.2"),
                                ("win", "^1"), ("core", "^1.1")])

    def test_resolve_highest_matching(self):
        """Выбирается наибольшая подходящая неотозванная версия."""
        self.assertEqual(self.source.resolve("core", "^1.1"),
                         Package("core", "1.2.0"))
        self.assertEqual(self.source.resolve("util", "^0.2"),
                         Package("util", "0.2.5"))

    def test_resolve_problems(self):
        """Нет пакета или версии — None и запись в problems."""
        self.assertIsNone(self.source.resolve("core", "^3"))
        self.assertIsNone(self.source.resolve("nope", "^1"))
        self.assertIsNone(self.source.resolve("core", "not a req"))
        self.assertEqual(len(self.source.problems), 3)

    def test_connection_failure_aborts(self):
        """Ошибка подключения прерывает построение графа."""
        def broken(url):
            """Имитировать обрыв связи после проверки индекса."""
            raise ConnectionFailed("не удалось подключиться")
        self.source.fetch = broken
        with self.assertRaises(ConnectionFailed):
            self.source.resolve("other", "^1")

    def test_graph_and_cache(self):
        """Граф целиком; каждый файл индекса загружается один раз."""
        graph = build_graph(self.source, "app", "latest")
        self.assertEqual([str(p) for p in graph.nodes],
                         ["app 1.0.0", "core 1.2.0", "util 0.2.5",
                          "win 1.0.0"])
        self.assertEqual(len(self.fetch.urls), len(set(self.fetch.urls)))

    def test_not_an_index(self):
        """Без config.json источник не создаётся."""
        def empty(url):
            """Пустой сервер."""
            raise DataError("пакет не найден в репозитории")
        with self.assertRaisesRegex(DataError, "нет индекса"):
            RemoteSource(REPO, empty)


class FileSourceTest(unittest.TestCase):
    """Проверка источника данных из файла тестового репозитория."""

    def path(self, name):
        """Путь к примеру из examples/graphs."""
        return os.path.join(GRAPHS, name)

    def test_examples(self):
        """Граф примеров: ромб, циклы, фильтр."""
        diamond = build_graph(FileSource(self.path("diamond.txt")), "A", "")
        self.assertEqual(len(diamond.nodes), 5)
        cycles = build_graph(FileSource(self.path("cycles.txt")), "A", "")
        self.assertEqual(len(cycles.cycles), 3)
        filtered = build_graph(FileSource(self.path("filter.txt")), "APP",
                               "", "TEST")
        self.assertEqual([p.name for p in filtered.nodes],
                         ["APP", "CORE", "UI", "UTIL"])

    def test_unreachable_not_included(self):
        """Описанный, но недостижимый пакет не попадает в граф."""
        graph = build_graph(FileSource(self.path("bfs_order.txt")), "A", "")
        self.assertNotIn(Package("X"), graph.nodes)

    def test_missing_package(self):
        """Неописанная зависимость — ошибка, если её не исключил фильтр."""
        source = FileSource(self.path("missing.txt"))
        with self.assertRaisesRegex(DataError, "C \\(зависимость A\\)"):
            build_graph(source, "A", "")
        graph = build_graph(FileSource(self.path("missing.txt")), "A", "",
                            "C")
        self.assertEqual(graph.excluded, ["C"])
        with self.assertRaisesRegex(DataError, "не описан"):
            build_graph(source, "Z", "")


if __name__ == "__main__":
    unittest.main()
