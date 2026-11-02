"""Модульные тесты для depviz.cli."""
import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

from depviz.cli import (EXIT_CONFIG_ERROR, EXIT_DATA_ERROR, EXIT_OK,
                        EXIT_RENDER_ERROR, main)
from depviz.graph import Graph, Package
from depviz.registry import DataError
from depviz.render import RenderError

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
    """Проверка вывода графа на языке DOT и сохранения изображения."""

    def setUp(self):
        """Подменить рисование: тесты не зависят от Graphviz."""
        patcher = mock.patch("depviz.cli.render_svg")
        self.render = patcher.start()
        self.addCleanup(patcher.stop)

    def test_dot_output(self):
        """В stdout — текст DOT, в stderr — сообщение о файле."""
        code, out, err = run(graph_args("diamond.txt", "A"))
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(out.startswith("// Граф зависимостей: A\n"))
        self.assertIn("digraph dependencies {", out)
        for edge in ('"A" -> "B"', '"A" -> "C"', '"B" -> "D"',
                     '"C" -> "D"', '"D" -> "E"'):
            self.assertIn(edge, out)
        self.assertEqual(err, "Изображение графа сохранено в файл "
                         "graph.svg (пакетов: 5, связей: 5, циклов: 0)\n")

    def test_image_saved(self):
        """Изображение сохраняется в файл --output по тому же тексту."""
        code, out, _ = run(graph_args("diamond.txt", "A", "--output",
                                      "diamond.svg"))
        self.assertEqual(code, EXIT_OK)
        self.render.assert_called_once_with(out, "diamond.svg")

    def test_cycles_and_filter(self):
        """Циклы и исключённые фильтром пакеты попадают в DOT."""
        _, out, err = run(graph_args("cycles.txt", "A", "--filter", "F"))
        self.assertIn("// Исключены фильтром «F»: F", out)
        self.assertIn("//     A -> B -> C -> A", out)
        self.assertIn('"C" -> "A" [color="#d62728", penwidth=2]', out)
        self.assertNotIn('"F"', out)
        self.assertIn("циклов: 2", err)

    def test_render_error(self):
        """Если изображение сохранить нельзя, код 3, но DOT выведен."""
        self.render.side_effect = RenderError("не найдена программа dot")
        code, out, err = run(graph_args("diamond.txt", "A"))
        self.assertEqual(code, EXIT_RENDER_ERROR)
        self.assertIn("digraph", out)
        self.assertEqual(err, "ошибка: не найдена программа dot\n")

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
        self.assertIn("// Учитываются обычные и build-зависимости", out)
        self.assertIn('"demo 1.0.0" [label="demo\\n1.0.0"', out)
        self.assertIn("//     old ^9: нет подходящей версии", out)

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


@unittest.skipUnless(shutil.which("dot"), "Graphviz не установлен")
class GraphvizTest(unittest.TestCase):
    """Полный запуск с настоящим Graphviz."""

    def test_svg_created(self):
        """Файл SVG создаётся и содержит пакеты графа."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "layers.svg")
            code, _, _ = run(graph_args("layers.txt", "A", "--output",
                                        path))
            with open(path, encoding="utf-8") as file:
                svg = file.read()
        self.assertEqual(code, EXIT_OK)
        self.assertIn("<svg", svg)
        self.assertIn("Зависимости пакета A", svg)


if __name__ == "__main__":
    unittest.main()
