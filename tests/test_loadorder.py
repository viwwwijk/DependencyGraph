"""Модульные тесты для depviz.loadorder."""
import os
import unittest

from depviz.graph import Graph, Package, build_graph
from depviz.loadorder import dependent_counts, dependents_of, load_order
from depviz.sources import FileSource

GRAPHS = os.path.join(os.path.dirname(__file__), os.pardir, "examples",
                      "graphs")


def make_graph(edges):
    """Граф из словаря имён {пакет: [зависимости]}; корень — первый."""
    nodes = [Package(name) for name in edges]
    graph = Graph(nodes[0], nodes)
    for name, children in edges.items():
        graph.edges[Package(name)] = [Package(c) for c in children]
    return graph


def names(packages):
    """Имена пакетов списком."""
    return [package.name for package in packages]


def example(name, root, substring=""):
    """Граф примера из examples/graphs."""
    path = os.path.join(GRAPHS, name)
    return build_graph(FileSource(path), root, "latest", substring)


class LoadOrderTest(unittest.TestCase):
    """Проверка порядка загрузки."""

    def assert_dependencies_first(self, graph, order):
        """Каждый пакет загружается после всех своих зависимостей."""
        position = {package: index for index, package in enumerate(order)}
        for package, children in graph.edges.items():
            for child in children:
                self.assertLess(position[child], position[package])

    def test_chain(self):
        """Цепочка загружается от листа к корню."""
        graph = make_graph({"A": ["B"], "B": ["C"], "C": []})
        self.assertEqual(names(load_order(graph).order), ["C", "B", "A"])

    def test_examples_are_topological(self):
        """Для всех ациклических примеров порядок корректен."""
        for name, root in (("diamond.txt", "A"), ("bfs_order.txt", "A"),
                           ("layers.txt", "A"), ("filter.txt", "APP")):
            with self.subTest(name=name):
                graph = example(name, root)
                result = load_order(graph)
                self.assertEqual(set(result.order), set(graph.nodes))
                self.assertEqual(result.blocked, [])
                self.assert_dependencies_first(graph, result.order)

    def test_layers_matches_cargo(self):
        """Порядок для layers.txt совпадает с полученным от Cargo."""
        order = load_order(example("layers.txt", "A")).order
        self.assertEqual(names(order), ["F", "G", "E", "D", "B", "C", "A"])

    def test_priority_then_alphabet(self):
        """Сначала пакет с большим числом зависящих, затем по алфавиту."""
        graph = make_graph({"A": ["B", "C", "Z"], "B": ["Z"], "C": [],
                            "Z": []})
        self.assertEqual(names(load_order(graph).order),
                         ["Z", "B", "C", "A"])

    def test_shared_dependency_once(self):
        """Общая зависимость загружается один раз."""
        order = load_order(example("diamond.txt", "A")).order
        self.assertEqual(names(order).count("D"), 1)

    def test_all_in_cycles(self):
        """Если всё упирается в циклы, загрузить нельзя ничего."""
        result = load_order(example("cycles.txt", "A"))
        self.assertEqual(result.order, [])
        self.assertEqual(sorted(names(result.blocked)),
                         ["A", "B", "C", "D", "E", "F"])

    def test_partial_cycle(self):
        """Загружается всё, что не зависит от цикла."""
        result = load_order(example("partial_cycle.txt", "A"))
        self.assertEqual(names(result.order), ["F", "D", "B"])
        self.assertEqual(names(result.blocked), ["A", "C", "E"])

    def test_self_loop(self):
        """Петля блокирует пакет и всех, кто от него зависит."""
        graph = make_graph({"A": ["B", "C"], "B": ["B"], "C": []})
        result = load_order(graph)
        self.assertEqual(names(result.order), ["C"])
        self.assertEqual(names(result.blocked), ["A", "B"])

    def test_filter_breaks_cycle(self):
        """Фильтр, исключивший пакет из цикла, делает загрузку возможной."""
        result = load_order(example("partial_cycle.txt", "A", "E"))
        self.assertEqual(names(result.order), ["D", "B", "C", "A"])
        self.assertEqual(result.blocked, [])

    def test_duplicate_edges(self):
        """Повторное ребро не мешает загрузке."""
        graph = make_graph({"A": ["B", "B"], "B": []})
        self.assertEqual(names(load_order(graph).order), ["B", "A"])


class DependentsTest(unittest.TestCase):
    """Проверка подсчёта зависящих пакетов."""

    def test_counts(self):
        """Транзитивные зависящие пакеты считаются без повторов."""
        graph = make_graph({"A": ["B", "C"], "B": ["D"], "C": ["D"],
                            "D": []})
        dependents = dependents_of(graph.edges)
        counts = dependent_counts(graph.edges, dependents)
        self.assertEqual({p.name: n for p, n in counts.items()},
                         {"A": 0, "B": 1, "C": 1, "D": 3})

    def test_counts_with_cycle(self):
        """В цикле подсчёт завершается и пакет не считает себя."""
        graph = make_graph({"A": ["B"], "B": ["A"]})
        counts = dependent_counts(graph.edges, dependents_of(graph.edges))
        self.assertEqual({p.name: n for p, n in counts.items()},
                         {"A": 1, "B": 1})


if __name__ == "__main__":
    unittest.main()
