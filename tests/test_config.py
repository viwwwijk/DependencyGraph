"""Модульные тесты для depviz.config."""
import os
import tempfile
import unittest

from depviz.config import (ConfigError, build_parser, collect_errors,
                           load_config, translate_argparse_message)

REMOTE_ARGS = ["--package", "serde", "--repo", "https://index.crates.io"]


class LoadConfigTest(unittest.TestCase):
    """Проверка разбора и проверки опций командной строки."""

    def test_defaults(self):
        """Необязательные параметры получают значения по умолчанию."""
        config = load_config(REMOTE_ARGS)
        self.assertEqual(config.items(), [
            ("package", "serde"),
            ("repo", "https://index.crates.io"),
            ("mode", "remote"),
            ("version", "latest"),
            ("output", "graph.svg"),
            ("filter", ""),
        ])

    def test_all_options_test_mode(self):
        """Все опции вместе в тестовом режиме."""
        with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                         delete=False) as graph_file:
            graph_file.write("A: B\n")
        try:
            config = load_config([
                "--package", "A", "--repo", graph_file.name,
                "--mode", "test", "--version", "1.2.3",
                "--output", "a.svg", "--filter", "B",
            ])
        finally:
            os.remove(graph_file.name)
        self.assertEqual(config.mode, "test")
        self.assertEqual(config.version, "1.2.3")
        self.assertEqual(config.filter, "B")

    def test_required_options(self):
        """Без --package и --repo сообщаются обе ошибки."""
        with self.assertRaises(ConfigError) as context:
            load_config([])
        self.assertEqual(context.exception.errors, [
            "--package: обязательный параметр не задан",
            "--repo: обязательный параметр не задан",
        ])

    def test_all_errors_are_collected(self):
        """Ошибки всех параметров выводятся за один запуск."""
        with self.assertRaises(ConfigError) as context:
            load_config([
                "--package", "1bad", "--repo", "ftp://x",
                "--version", "1.0", "--output", "g.png", "--filter", "",
            ])
        options = [error.split(":")[0]
                   for error in context.exception.errors]
        self.assertEqual(options, ["--package", "--repo", "--version",
                                   "--output", "--filter"])

    def test_invalid_mode_skips_mode_rules(self):
        """При неверном режиме имя пакета и адрес не проверяются."""
        args = build_parser().parse_args(
            ["--mode", "local", "--package", "1bad", "--repo", "x"])
        errors = collect_errors(args)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("--mode: "))

    def test_mode_changes_rules(self):
        """Имя serde допустимо в remote, но не в test."""
        with self.assertRaises(ConfigError) as context:
            load_config(REMOTE_ARGS + ["--mode", "test"])
        options = [error.split(":")[0]
                   for error in context.exception.errors]
        self.assertEqual(options, ["--package", "--repo"])

    def test_argparse_errors(self):
        """Ошибки разбора argparse переводятся на русский."""
        cases = [
            (["--foo", "1"], "неизвестные аргументы: --foo 1"),
            (["--package"], "параметр --package: не указано значение"),
            (["--pack", "serde"], "неизвестные аргументы: --pack serde"),
            (REMOTE_ARGS + ["extra"], "неизвестные аргументы: extra"),
        ]
        for argv, text in cases:
            with self.subTest(argv=argv):
                with self.assertRaises(ConfigError) as context:
                    load_config(argv)
                self.assertEqual(context.exception.errors, [text])

    def test_unknown_message_is_kept(self):
        """Непереведённое сообщение argparse выводится как есть."""
        self.assertEqual(translate_argparse_message("something else"),
                         "something else")


if __name__ == "__main__":
    unittest.main()
