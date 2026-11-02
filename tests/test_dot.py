"""Модульные тесты для depviz.dot."""
import os
import unittest

from depviz.dot import (cycle_edges, escape, graph_label, node_label,
                        quote, summary_comments, to_dot)
from depviz.graph import Graph, Package, build_graph
from depviz.sources import FileSource

GRAPHS = os.path.join(os.path.dirname(__file__), os.pardir, "examples",
                      "graphs")
A, B, C, D = (Package(name) for name in "ABCD")


def diamond():
    """Граф-ромб A -> B, C; B, C -> D."""
    return Graph(A, [A, B, C, D], {A: [B, C], B: [D], C: [D], D: []})


def body(text):
    """Строки DOT без комментариев и с убранными отступами."""
    return [line.strip() for line in text.splitlines()
            if not line.startswith("//")]


class QuoteTest(unittest.TestCase):
    """Экранирование строк DOT."""

    def test_plain(self):
        """Обычное имя просто берётся в кавычки."""
        self.assertEqual(quote("serde 1.0.0"), '"serde 1.0.0"')

    def test_special_characters(self):
        """Кавычки и обратная косая черта экранируются."""
        self.assertEqual(escape('a"b\\c'), 'a\\"b\\\\c')
        self.assertEqual(quote('"'), '"\\""')


class LabelTest(unittest.TestCase):
    """Подписи вершин и заголовок изображения."""

    def test_node_with_version(self):
        """Версия выводится на второй строке подписи."""
        self.assertEqual(node_label(Package("serde", "1.0.229")),
                         '"serde\\n1.0.229"')

    def test_node_without_version(self):
        """В тестовом режиме подпись — только имя."""
        self.assertEqual(node_label(A), '"A"')

    def test_graph_label_with_filter(self):
        """Исключённые фильтром пакеты видны в заголовке."""
        graph = diamond()
        graph.excluded = ["TESTKIT"]
        self.assertEqual(graph_label(graph, "TEST"),
                         '"Зависимости пакета A\\nисключены фильтром '
                         '«TEST»: TESTKIT"')

    def test_graph_label_without_excluded(self):
        """Если фильтр ничего не исключил, в заголовке только пакет."""
        self.assertEqual(graph_label(diamond(), "Z"),
                         '"Зависимости пакета A"')


class CycleEdgesTest(unittest.TestCase):
    """Рёбра, входящие в циклы."""

    def test_edges(self):
        """Цикл A -> B -> A даёт рёбра (A, B) и (B, A); петля — (C, C)."""
        self.assertEqual(cycle_edges([[A, B, A], [C, C]]),
                         {(A, B), (B, A), (C, C)})

    def test_no_cycles(self):
        """Без циклов множество пустое."""
        self.assertEqual(cycle_edges([]), set())


class ToDotTest(unittest.TestCase):
    """Текст графа на языке DOT."""

    def test_structure(self):
        """Ориентированный граф: вершины, затем рёбра в порядке обхода."""
        lines = body(to_dot(diamond()))
        self.assertEqual(lines[0], "digraph dependencies {")
        self.assertEqual(lines[-1], "}")
        self.assertEqual(lines[-5:-1], ['"A" -> "B"', '"A" -> "C"',
                                        '"B" -> "D"', '"C" -> "D"'])
        nodes = [line for line in lines if "[label=" in line]
        self.assertEqual([line.split()[0] for line in nodes],
                         ['"A"', '"B"', '"C"', '"D"'])

    def test_root_highlighted(self):
        """Только корневой пакет выделен цветом."""
        lines = body(to_dot(diamond()))
        highlighted = [line for line in lines if "#cfe2ff" in line]
        self.assertEqual(len(highlighted), 1)
        self.assertTrue(highlighted[0].startswith('"A" '))

    def test_cycle_edges_red(self):
        """Рёбра цикла выделяются красным, остальные — нет."""
        graph = Graph(A, [A, B], {A: [B], B: [A, B]})
        graph.cycles = [[A, B, A], [B, B]]
        lines = body(to_dot(graph))
        self.assertIn('"A" -> "B" [color="#d62728", penwidth=2]', lines)
        self.assertIn('"B" -> "B" [color="#d62728", penwidth=2]', lines)
        graph.cycles = [[B, B]]
        self.assertIn('"A" -> "B"', body(to_dot(graph)))

    def test_versions_in_names(self):
        """Идентификатор вершины — имя и версия, подпись в две строки."""
        root = Package("url", "2.5.2")
        child = Package("idna", "0.5.0")
        text = to_dot(Graph(root, [root, child], {root: [child],
                                                  child: []}))
        self.assertIn('"url 2.5.2" -> "idna 0.5.0"', text)
        self.assertIn('label="idna\\n0.5.0"', text)

    def test_graph_attributes(self):
        """Общие атрибуты графа, вершин и рёбер, затем заголовок."""
        lines = body(to_dot(diamond()))
        self.assertTrue(lines[1].startswith("graph [rankdir=TB"))
        self.assertEqual(lines[2], 'label="Зависимости пакета A"')
        self.assertTrue(lines[3].startswith("node [shape=box"))
        self.assertTrue(lines[4].startswith("edge ["))

    def test_title(self):
        """Начало заголовка изображения можно задать."""
        text = to_dot(diamond(), title="cargo tree:")
        self.assertIn('label="cargo tree: A"', text)

    def test_ends_with_newline(self):
        """Текст заканчивается переводом строки (удобно для файла)."""
        self.assertTrue(to_dot(diamond()).endswith("}\n"))


class CommentsTest(unittest.TestCase):
    """Итоги анализа в комментариях DOT."""

    def test_summary(self):
        """Источник, число пакетов и связей, циклы."""
        comments = summary_comments(diamond(), "Тестовый репозиторий: x",
                                    "")
        self.assertEqual(comments, [
            "// Граф зависимостей: A",
            "// Тестовый репозиторий: x",
            "// Пакетов: 4, связей: 4",
            "// Циклические зависимости: нет"])

    def test_filter_cycles_and_problems(self):
        """Фильтр, циклы и проблемы с версиями перечисляются."""
        graph = Graph(A, [A], {A: [A]}, ["F"], [[A, A]],
                      ["old ^9: нет подходящей версии"])
        comments = summary_comments(graph, "строка 1\nстрока 2", "F")
        self.assertEqual(comments[1:], [
            "// строка 1", "// строка 2",
            "// Пакетов: 1, связей: 1",
            "// Исключены фильтром «F»: F",
            "// Циклические зависимости (1):",
            "//     A -> A",
            "// Не удалось выбрать версию:",
            "//     old ^9: нет подходящей версии"])

    def test_all_lines_are_comments_or_dot(self):
        """Многострочное описание источника не ломает синтаксис DOT."""
        text = to_dot(diamond(), "Репозиторий: x\nУчитываются ...")
        before = text.split("digraph")[0].splitlines()
        self.assertTrue(all(line.startswith("// ") for line in before))


class FromSourceTest(unittest.TestCase):
    """DOT для графа, построенного по источнику данных."""

    def test_filter_removes_nodes(self):
        """Исключённые фильтром пакеты не попадают в DOT."""
        source = FileSource(os.path.join(GRAPHS, "filter.txt"))
        text = to_dot(build_graph(source, "APP", "latest", "TEST"),
                      substring="TEST")
        self.assertNotIn('"TESTKIT"', text)
        self.assertNotIn('"MOCK"', text)
        self.assertIn("исключены фильтром «TEST»: LOGTEST, TESTKIT", text)

    def test_example_file(self):
        """Граф из файла тестового репозитория с циклами."""
        graph = build_graph(FileSource(os.path.join(GRAPHS, "cycles.txt")),
                            "A", "latest")
        text = to_dot(graph)
        self.assertIn('"F" -> "F" [color="#d62728", penwidth=2]', text)
        self.assertIn("// Циклические зависимости (3):", text)


if __name__ == "__main__":
    unittest.main()
