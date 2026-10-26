"""Модульные тесты для depviz.testing_repo."""
import os
import tempfile
import unittest

from depviz.registry import DataError
from depviz.testing_repo import (file_dependencies, load_test_repo,
                                 parse_test_repo)

EXAMPLE = os.path.join(os.path.dirname(__file__), os.pardir, "examples",
                       "test_repo.txt")


class ParseTestRepoTest(unittest.TestCase):
    """Проверка разбора файла тестового репозитория."""

    def test_parse(self):
        """Пакеты, зависимости, пустые строки и комментарии."""
        text = "# граф\nA: B C\n\nB:\n  C :  \n"
        self.assertEqual(parse_test_repo(text),
                         {"A": ["B", "C"], "B": [], "C": []})

    def test_errors(self):
        """Ошибки формата с номером строки."""
        cases = [
            ("A B\n", "строка 1: ожидается формат"),
            ("a: B\n", "строка 1: имя пакета «a»"),
            ("A: B c\n", "строка 1: имя пакета «c»"),
            (": B\n", "строка 1: имя пакета «»"),
            ("A: B B\n", "строка 1: зависимость указана дважды"),
            ("A: B\nA: C\n", "строка 2: пакет A описан повторно"),
        ]
        for text, message in cases:
            with self.subTest(text=text):
                with self.assertRaisesRegex(DataError, message):
                    parse_test_repo(text)


class FileDependenciesTest(unittest.TestCase):
    """Проверка получения прямых зависимостей из файла."""

    def test_example(self):
        """Прямые зависимости пакета из examples/test_repo.txt."""
        deps = file_dependencies(EXAMPLE, "A")
        self.assertEqual([(d.name, d.req) for d in deps],
                         [("B", ""), ("C", "")])
        self.assertEqual(file_dependencies(EXAMPLE, "D"), [])

    def test_missing_package(self):
        """Пакет, не описанный в файле, — ошибка."""
        with self.assertRaisesRegex(DataError, "не описан"):
            file_dependencies(EXAMPLE, "Z")

    def test_unreadable_file(self):
        """Отсутствующий файл и файл не в UTF-8 — ошибки."""
        with self.assertRaisesRegex(DataError, "не удалось прочитать"):
            load_test_repo(EXAMPLE + ".missing")
        with tempfile.NamedTemporaryFile(delete=False) as bad_file:
            bad_file.write(b"A: \xff\n")
        try:
            with self.assertRaisesRegex(DataError, "UTF-8"):
                load_test_repo(bad_file.name)
        finally:
            os.remove(bad_file.name)


if __name__ == "__main__":
    unittest.main()
