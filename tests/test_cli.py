"""Модульные тесты для depviz.cli."""
import io
import os
import unittest
from unittest import mock

from depviz.cli import (EXIT_CONFIG_ERROR, EXIT_DATA_ERROR, EXIT_OK,
                        describe_dependency, main)
from depviz.registry import DataError, Dependency

EXAMPLE = os.path.join(os.path.dirname(__file__), os.pardir, "examples",
                       "test_repo.txt")
REMOTE = ["--package", "demo", "--repo", "https://index.example.org"]


def run(argv):
    """Запустить main и вернуть (код, stdout, stderr)."""
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(argv, stdout, stderr)
    return code, stdout.getvalue(), stderr.getvalue()


class DescribeDependencyTest(unittest.TestCase):
    """Проверка строки о зависимости."""

    def test_plain(self):
        """Обычная зависимость: имя и требование к версии."""
        self.assertEqual(describe_dependency(Dependency("serde", "^1")),
                         "  serde ^1")

    def test_all_notes(self):
        """Все пометки: переименование, вид, optional, платформа."""
        dependency = Dependency("rand_old", "^0.7", "dev", True,
                                "cfg(unix)", "rand")
        self.assertEqual(describe_dependency(dependency),
                         "  rand_old ^0.7 (пакет rand, dev, "
                         "необязательная, платформа cfg(unix))")

    def test_same_package_name(self):
        """Пакет с тем же именем, что и зависимость, не помечается."""
        dependency = Dependency("tokio", "^1", package="tokio")
        self.assertEqual(describe_dependency(dependency), "  tokio ^1")

    def test_test_mode(self):
        """Без требования к версии выводится только имя."""
        self.assertEqual(describe_dependency(Dependency("B", "")), "  B")


class MainTest(unittest.TestCase):
    """Проверка запуска из командной строки."""

    @mock.patch("depviz.cli.remote_dependencies")
    def test_remote(self, remote):
        """Вывод прямых зависимостей последней версии пакета."""
        remote.return_value = ({"vers": "1.2.0"},
                               [Dependency("serde", "^1"),
                                Dependency("cc", "^1", "build")])
        code, out, err = run(REMOTE)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(err, "")
        self.assertEqual(out, "\n".join([
            "Пакет: demo 1.2.0 (последняя версия)",
            "Репозиторий: https://index.example.org",
            "Прямые зависимости (2):",
            "  serde ^1",
            "  cc ^1 (build)",
        ]) + "\n")
        remote.assert_called_once_with("https://index.example.org",
                                       "demo", "latest")

    @mock.patch("depviz.cli.remote_dependencies")
    def test_remote_yanked_without_dependencies(self, remote):
        """Отозванная версия без зависимостей."""
        remote.return_value = ({"vers": "0.1.0", "yanked": True}, [])
        code, out, _ = run(REMOTE + ["--version", "0.1.0"])
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out, "Пакет: demo 0.1.0 (версия отозвана — "
                              "yanked)\nРепозиторий: "
                              "https://index.example.org\n"
                              "Прямые зависимости: нет\n")

    @mock.patch("depviz.cli.remote_dependencies")
    def test_data_error(self, remote):
        """Ошибка получения данных: stderr и код 1."""
        remote.side_effect = DataError("пакет не найден в репозитории")
        code, out, err = run(REMOTE)
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertEqual(out, "")
        self.assertEqual(err, "ошибка: пакет не найден в репозитории\n")

    def test_test_mode(self):
        """Тестовый режим читает файл, версия не используется."""
        code, out, err = run(["--package", "A", "--repo", EXAMPLE,
                              "--mode", "test", "--version", "1.0.0"])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("не используется", err)
        self.assertTrue(out.endswith("Прямые зависимости (2):\n  B\n"
                                     "  C\n"))

    def test_config_error(self):
        """Ошибки параметров: stderr, код 2, данные не загружаются."""
        code, out, err = run(["--package", "demo"])
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertEqual(err, "ошибка: --repo: обязательный параметр "
                              "не задан\n")


if __name__ == "__main__":
    unittest.main()
