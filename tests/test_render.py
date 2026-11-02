"""Модульные тесты для depviz.render."""
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from depviz.render import RenderError, render_svg

DOT_TEXT = 'digraph g {\n    "A" -> "B"\n}\n'


class RenderTest(unittest.TestCase):
    """Вызов программы dot."""

    @mock.patch("depviz.render.subprocess.run")
    def test_command(self, run):
        """Текст DOT передаётся на стандартный ввод dot -Tsvg -o файл."""
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        render_svg(DOT_TEXT, "out.svg")
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["dot", "-Tsvg", "-o", "out.svg"])
        self.assertEqual(kwargs["input"], DOT_TEXT)

    def test_missing_program(self):
        """Если Graphviz не установлен, сообщается, где его взять."""
        with self.assertRaises(RenderError) as context:
            render_svg(DOT_TEXT, "out.svg", "no-such-dot-program")
        self.assertIn("установите Graphviz", str(context.exception))

    @mock.patch("depviz.render.subprocess.run")
    def test_program_error(self, run):
        """Ошибка dot передаётся пользователю."""
        run.return_value = subprocess.CompletedProcess(
            [], 1, "", "Error: syntax error in line 1\n")
        with self.assertRaises(RenderError) as context:
            render_svg("bad", "out.svg")
        self.assertEqual(str(context.exception),
                         "dot не смог сохранить изображение в out.svg: "
                         "Error: syntax error in line 1")

    @mock.patch("depviz.render.subprocess.run")
    def test_error_without_message(self, run):
        """Если dot ничего не написал, выводится код завершения."""
        run.return_value = subprocess.CompletedProcess([], 2, "", "")
        with self.assertRaises(RenderError) as context:
            render_svg(DOT_TEXT, "out.svg")
        self.assertTrue(str(context.exception).endswith(": код 2"))

    @mock.patch("depviz.render.subprocess.run")
    def test_os_error(self, run):
        """Другие ошибки запуска тоже превращаются в RenderError."""
        run.side_effect = PermissionError("отказано в доступе")
        with self.assertRaises(RenderError) as context:
            render_svg(DOT_TEXT, "out.svg")
        self.assertIn("не удалось запустить dot", str(context.exception))


@unittest.skipUnless(shutil.which("dot"), "Graphviz не установлен")
class GraphvizTest(unittest.TestCase):
    """Настоящий запуск Graphviz (если он установлен)."""

    def test_svg_file(self):
        """Создаётся файл SVG с вершинами графа."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "graph.svg")
            render_svg('digraph g {\n    "Пакет" -> "B"\n}\n', path)
            with open(path, encoding="utf-8") as file:
                svg = file.read()
        self.assertIn("<svg", svg)
        self.assertIn("Пакет", svg)


if __name__ == "__main__":
    unittest.main()
