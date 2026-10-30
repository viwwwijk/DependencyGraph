"""Модульные тесты для depviz.cli."""
import io
import os
import unittest
from unittest import mock

from depviz.cli import EXIT_CONFIG_ERROR, EXIT_DATA_ERROR, EXIT_OK, main
from depviz.graph import Graph, Package
from depviz.registry import DataError

GRAPHS = os.path.join(os.path.dirname(__file__), os.pardir, "examples",
                      "graphs")


def run(argv):
    """Запустить main и вернуть (код, stdout, stderr)."""
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(argv, stdout, stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def graph_args(name, package, *extra):
    """Аргументы запуска в тестовом режиме с файлом из examples/graphs."""
    return ["--mode", "test", "--repo", os.path.join(GRAPHS, name),
            "--package", package] + list(extra)


class MainTest(unittest.TestCase):
    """Проверка вывода графа."""

    def test_graph_output(self):
        """Список смежности в порядке обхода и итоги."""
        code, out, err = run(graph_args("diamond.txt", "A"))
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(err, "")
        lines = out.splitlines()
        self.assertEqual(lines[0], "Граф зависимостей: A")
        self.assertEqual(lines[2], "Пакетов: 5, связей: 5 (обход в ширину)")
        self.assertEqual(lines[3:8], ["  A -> B, C", "  B -> D", "  C -> D",
                                      "  D -> E",
                                      "  E -> нет зависимостей"])
        self.assertEqual(lines[-1], "Циклические зависимости: нет")

    def test_cycles_and_filter(self):
        """Вывод найденных циклов и исключённых фильтром пакетов."""
        _, out, _ = run(graph_args("cycles.txt", "A", "--filter", "F"))
        self.assertIn("Исключены фильтром «F»: F", out)
        self.assertTrue(out.endswith("Циклические зависимости (2):\n"
                                     "  A -> B -> C -> A\n"
                                     "  D -> E -> D\n"))

    def test_filter_without_matches(self):
        """Если фильтр ничего не исключил, это видно в выводе."""
        _, out, _ = run(graph_args("diamond.txt", "A", "--filter", "Z"))
        self.assertIn("Исключены фильтром «Z»: нет", out)

    def test_version_warning(self):
        """В тестовом режиме версия не используется."""
        code, _, err = run(graph_args("diamond.txt", "A",
                                      "--version", "1.0.0"))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("не используется", err)

    def test_data_error(self):
        """Неописанная зависимость: stderr и код 1."""
        code, out, err = run(graph_args("missing.txt", "A"))
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertEqual(out, "")
        self.assertIn("не описан в тестовом репозитории", err)

    @mock.patch("depviz.cli.RemoteSource")
    @mock.patch("depviz.cli.build_graph")
    def test_remote_mode(self, build, source):
        """В режиме remote граф строится по индексу и выводятся проблемы."""
        root = Package("demo", "1.0.0")
        graph = Graph(root, [root], {root: []},
                      problems=["old ^9: нет подходящей версии"])
        build.return_value = graph
        code, out, _ = run(["--package", "demo", "--repo",
                            "https://index.example.org"])
        self.assertEqual(code, EXIT_OK)
        source.assert_called_once_with("https://index.example.org")
        self.assertIn("Учитываются обычные и build-зависимости", out)
        self.assertIn("  demo 1.0.0 -> нет зависимостей", out)
        self.assertTrue(out.endswith("Не удалось выбрать версию (1):\n"
                                     "  old ^9: нет подходящей версии\n"))

    @mock.patch("depviz.cli.RemoteSource")
    def test_remote_error(self, source):
        """Ошибка индекса в режиме remote: код 1."""
        source.side_effect = DataError("по адресу x нет индекса Cargo")
        code, _, err = run(["--package", "demo", "--repo",
                            "https://index.example.org"])
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertEqual(err, "ошибка: по адресу x нет индекса Cargo\n")

    def test_config_error(self):
        """Ошибки параметров: stderr, код 2."""
        code, out, err = run(["--package", "demo"])
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertIn("--repo: обязательный параметр не задан", err)


if __name__ == "__main__":
    unittest.main()
