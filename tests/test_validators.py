"""Модульные тесты для depviz.validators."""
import os
import tempfile
import unittest

from depviz.validators import (validate_filter, validate_mode,
                               validate_output, validate_package,
                               validate_repo, validate_version)


class ModeTest(unittest.TestCase):
    """Проверка режима работы."""

    def test_valid(self):
        """Допустимы режимы remote и test."""
        self.assertEqual(validate_mode("remote"), "")
        self.assertEqual(validate_mode("test"), "")

    def test_invalid(self):
        """Любой другой режим — ошибка, регистр важен."""
        for mode in ("", "local", "TEST"):
            with self.subTest(mode=mode):
                self.assertIn("неизвестный режим", validate_mode(mode))


class PackageTest(unittest.TestCase):
    """Проверка имени пакета."""

    def test_remote_valid(self):
        """Имена по правилам crates.io допустимы."""
        for name in ("serde", "tokio-util", "serde_json", "a", "x" * 64):
            with self.subTest(name=name):
                self.assertEqual(validate_package(name, "remote"), "")

    def test_remote_invalid(self):
        """Пустое, длинное и имя с недопустимыми символами — ошибки."""
        cases = [
            ("", "не может быть пустым"),
            ("x" * 65, "длиннее 64"),
            ("1serde", "первый символ"),
            ("-serde", "первый символ"),
            ("serde json", "недопустимое имя"),
            ("пакет", "недопустимое имя"),
        ]
        for name, text in cases:
            with self.subTest(name=name):
                self.assertIn(text, validate_package(name, "remote"))

    def test_test_mode(self):
        """В тестовом режиме имя — большие латинские буквы."""
        self.assertEqual(validate_package("A", "test"), "")
        self.assertEqual(validate_package("ABC", "test"), "")
        for name in ("a", "A1", "serde", "Б"):
            with self.subTest(name=name):
                self.assertIn("больших латинских букв",
                              validate_package(name, "test"))


class RepoTest(unittest.TestCase):
    """Проверка URL-адреса или файла тестового репозитория."""

    def test_remote_valid(self):
        """URL со схемой http или https и сервером допустим."""
        for url in ("https://index.crates.io", "http://localhost:8080/x"):
            with self.subTest(url=url):
                self.assertEqual(validate_repo(url, "remote"), "")

    def test_remote_invalid(self):
        """Пустой адрес, другая схема, нет сервера, пробелы — ошибки."""
        cases = [
            ("", "не может быть пустым"),
            ("ftp://example.com", "http:// или https://"),
            ("index.crates.io", "http:// или https://"),
            ("https://", "не указан сервер"),
            ("https://crates .io", "пробелы"),
        ]
        for url, text in cases:
            with self.subTest(url=url):
                self.assertIn(text, validate_repo(url, "remote"))

    def test_test_mode(self):
        """Файл должен существовать и не быть каталогом."""
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "graph.txt")
            with open(path, "w", encoding="utf-8") as graph_file:
                graph_file.write("A: B\n")
            self.assertEqual(validate_repo(path, "test"), "")
            self.assertIn("не найден", validate_repo(path + ".x", "test"))
            self.assertIn("не является файлом",
                          validate_repo(directory, "test"))

    def test_test_mode_rejects_url(self):
        """В тестовом режиме URL считается отсутствующим файлом."""
        self.assertIn("не найден",
                      validate_repo("https://index.crates.io", "test"))


class VersionTest(unittest.TestCase):
    """Проверка версии пакета."""

    def test_valid(self):
        """SemVer с пререлизом и сборкой, а также latest."""
        for version in ("1.0.0", "0.4.10", "1.0.0-beta.1",
                        "2.1.3+build.5", "1.0.0-rc.1+abc", "latest"):
            with self.subTest(version=version):
                self.assertEqual(validate_version(version), "")

    def test_invalid(self):
        """Неполная версия, ведущие нули, требования Cargo — ошибки."""
        for version in ("", "1", "1.0", "01.0.0", "^1.0.0", "v1.0.0",
                        "1.0.0.0", "1.0.x", "Latest"):
            with self.subTest(version=version):
                self.assertTrue(validate_version(version))


class OutputTest(unittest.TestCase):
    """Проверка имени файла с изображением."""

    def setUp(self):
        """Создать временный каталог для файлов изображения."""
        self.temp = tempfile.TemporaryDirectory()
        self.directory = self.temp.name

    def tearDown(self):
        """Удалить временный каталог."""
        self.temp.cleanup()

    def test_valid(self):
        """Имя .svg в существующем каталоге, регистр расширения любой."""
        for name in ("graph.svg", "GRAPH.SVG"):
            with self.subTest(name=name):
                path = os.path.join(self.directory, name)
                self.assertEqual(validate_output(path), "")
        self.assertEqual(validate_output("graph.svg"), "")

    def test_invalid(self):
        """Пустое имя, другое расширение, каталог, нет каталога."""
        folder = os.path.join(self.directory, "dir.svg")
        os.mkdir(folder)
        cases = [
            ("", "не может быть пустым"),
            ("graph.png", "расширение .svg"),
            ("graph", "расширение .svg"),
            (folder, "находится каталог"),
            (os.path.join(self.directory, "nope", "g.svg"),
             "не существует"),
        ]
        for path, text in cases:
            with self.subTest(path=path):
                self.assertIn(text, validate_output(path))


class FilterTest(unittest.TestCase):
    """Проверка подстроки фильтрации."""

    def test_valid(self):
        """Фильтр не задан или состоит из допустимых символов."""
        for value in (None, "B", "serde", "tokio-", "_derive"):
            with self.subTest(value=value):
                self.assertEqual(validate_filter(value), "")

    def test_invalid(self):
        """Пустая подстрока и недопустимые символы — ошибки."""
        self.assertIn("не может быть пустой", validate_filter(""))
        for value in ("a b", "serde*", "пакет", "a/b"):
            with self.subTest(value=value):
                self.assertIn("недопустимая подстрока",
                              validate_filter(value))


if __name__ == "__main__":
    unittest.main()
