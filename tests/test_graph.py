"""Модульные тесты для depviz.graph."""
import unittest

from depviz.graph import (Graph, Package, build_graph, find_cycles,
                          format_cycle)
from depviz.registry import DataError


class DictSource:
    """Источник данных из словаря {пакет: [зависимости]}."""

    def __init__(self, graph):
        """Запомнить граф и подготовить журнал запросов."""
        self.graph = graph
        self.problems = []
        self.expanded = []

    def root(self, name, version):
        """Корневой пакет."""
        return Package(name)

    def dependencies(self, package):
        """Прямые зависимости; запоминается порядок запросов."""
        self.expanded.append(package.name)
        return [(name, "") for name in self.graph[package.name]]

    def resolve(self, name, requirement):
        """Пакет-зависимость; MISSING имитирует неразрешимую версию."""
        if name == "MISSING":
            self.problems.append("MISSING: нет подходящей версии")
            return None
        return Package(name)


def names(packages):
    """Имена пакетов списком."""
    return [package.name for package in packages]


class BuildGraphTest(unittest.TestCase):
    """Проверка обхода в ширину."""

    def test_bfs_order(self):
        """Пакеты обрабатываются по уровням удаления от корня."""
        source = DictSource({"A": ["B", "C"], "B": ["D"], "C": ["E"],
                             "D": ["F"], "E": [], "F": []})
        graph = build_graph(source, "A", "latest")
        self.assertEqual(names(graph.nodes), ["A", "B", "C", "D", "E", "F"])
        self.assertEqual(source.expanded, names(graph.nodes))
        self.assertEqual(graph.edge_count(), 5)

    def test_shared_dependency_once(self):
        """Общая зависимость (ромб) обрабатывается один раз."""
        source = DictSource({"A": ["B", "C"], "B": ["D"], "C": ["D"],
                             "D": []})
        graph = build_graph(source, "A", "latest")
        self.assertEqual(source.expanded.count("D"), 1)
        self.assertEqual(names(graph.edges[Package("C")]), ["D"])

    def test_duplicate_edges_merged(self):
        """Повторная зависимость (обычная и build) даёт одно ребро."""
        source = DictSource({"A": ["B", "B"], "B": []})
        graph = build_graph(source, "A", "latest")
        self.assertEqual(names(graph.edges[Package("A")]), ["B"])

    def test_cycles_terminate(self):
        """Циклы не зацикливают обход и находятся."""
        source = DictSource({"A": ["B"], "B": ["C"], "C": ["A", "C"]})
        graph = build_graph(source, "A", "latest")
        self.assertEqual(names(graph.nodes), ["A", "B", "C"])
        self.assertEqual([format_cycle(cycle) for cycle in graph.cycles],
                         ["A -> B -> C -> A", "C -> C"])

    def test_filter(self):
        """Пакеты с подстрокой не учитываются и не загружаются."""
        source = DictSource({"A": ["B", "XB"], "B": ["C"], "XB": ["D"],
                             "C": [], "D": []})
        graph = build_graph(source, "A", "latest", "X")
        self.assertEqual(names(graph.nodes), ["A", "B", "C"])
        self.assertEqual(graph.excluded, ["XB"])
        self.assertNotIn("XB", source.expanded)

    def test_filter_excludes_root(self):
        """Если фильтр исключает корень, анализировать нечего."""
        with self.assertRaisesRegex(DataError, "исключён фильтром"):
            build_graph(DictSource({"AB": []}), "AB", "latest", "B")

    def test_problems(self):
        """Неразрешимые зависимости не попадают в граф, но сообщаются."""
        source = DictSource({"A": ["MISSING", "B"], "B": []})
        graph = build_graph(source, "A", "latest")
        self.assertEqual(names(graph.nodes), ["A", "B"])
        self.assertEqual(graph.problems, ["MISSING: нет подходящей версии"])


class FindCyclesTest(unittest.TestCase):
    """Проверка поиска циклов."""

    def graph(self, edges):
        """Создать Graph из словаря имён."""
        nodes = [Package(name) for name in edges]
        result = Graph(nodes[0], nodes)
        for name, children in edges.items():
            result.edges[Package(name)] = [Package(c) for c in children]
        return result

    def test_no_cycles(self):
        """В ромбе циклов нет."""
        edges = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        self.assertEqual(find_cycles(self.graph(edges)), [])

    def test_several_cycles(self):
        """Несколько независимых циклов и петля."""
        edges = {"A": ["B", "D"], "B": ["A"], "D": ["E"], "E": ["D", "E"]}
        cycles = [format_cycle(c) for c in find_cycles(self.graph(edges))]
        self.assertEqual(cycles, ["A -> B -> A", "D -> E -> D", "E -> E"])

    def test_same_cycle_once(self):
        """Один цикл, найденный с разных вершин, выводится один раз."""
        edges = {"A": ["B"], "B": ["C"], "C": ["A"]}
        self.assertEqual(len(find_cycles(self.graph(edges))), 1)


class PackageTest(unittest.TestCase):
    """Проверка вершины графа."""

    def test_str(self):
        """Версия выводится через пробел, если она есть."""
        self.assertEqual(str(Package("serde", "1.0.0")), "serde 1.0.0")
        self.assertEqual(str(Package("A")), "A")


if __name__ == "__main__":
    unittest.main()
