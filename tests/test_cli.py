"""Модульные тесты для depviz.cli."""
import io
import unittest

from depviz.cli import EXIT_CONFIG_ERROR, EXIT_OK, main


def run(argv):
    """Запустить main и вернуть (код, stdout, stderr)."""
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(argv, stdout, stderr)
    return code, stdout.getvalue(), stderr.getvalue()


class MainTest(unittest.TestCase):
    """Проверка запуска из командной строки."""

    def test_prints_key_value(self):
        """При успехе все параметры выводятся как ключ=значение."""
        code, out, err = run(["--package", "serde", "--repo",
                              "https://index.crates.io", "--filter", "x"])
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(err, "")
        self.assertEqual(out, "\n".join([
            "package=serde",
            "repo=https://index.crates.io",
            "mode=remote",
            "version=latest",
            "output=graph.svg",
            "filter=x",
        ]) + "\n")

    def test_errors_go_to_stderr(self):
        """Ошибки выводятся в stderr с префиксом, код завершения 2."""
        code, out, err = run(["--package", "serde"])
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertEqual(err, "ошибка: --repo: обязательный параметр "
                              "не задан\n")


if __name__ == "__main__":
    unittest.main()
