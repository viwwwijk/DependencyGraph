"""Модульные тесты для depviz.semver."""
import unittest

from depviz.semver import (VersionError, is_prerelease, parse_version,
                           version_key)


class SemverTest(unittest.TestCase):
    """Проверка разбора и сравнения версий."""

    def test_parse(self):
        """Версия разбирается на числа и части пререлиза."""
        self.assertEqual(parse_version("1.2.3"), (1, 2, 3, []))
        self.assertEqual(parse_version("1.0.0-rc.1+build.5"),
                         (1, 0, 0, ["rc", "1"]))

    def test_invalid(self):
        """Не-SemVer строки вызывают VersionError."""
        for text in ("1.0", "v1.0.0", "01.0.0", ""):
            with self.subTest(text=text):
                with self.assertRaises(VersionError):
                    parse_version(text)

    def test_order_from_specification(self):
        """Порядок из примера спецификации SemVer 2.0."""
        ordered = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta",
                   "1.0.0-beta", "1.0.0-beta.2", "1.0.0-beta.11",
                   "1.0.0-rc.1", "1.0.0", "1.0.1", "1.1.0", "1.10.0",
                   "2.0.0"]
        shuffled = list(reversed(ordered))
        self.assertEqual(sorted(shuffled, key=version_key), ordered)

    def test_build_metadata_ignored(self):
        """Метаданные сборки не влияют на порядок."""
        self.assertEqual(version_key("1.0.0+a"), version_key("1.0.0+b"))

    def test_is_prerelease(self):
        """Пререлиз определяется по части после дефиса."""
        self.assertTrue(is_prerelease("1.0.0-beta"))
        self.assertFalse(is_prerelease("1.0.0+build"))


if __name__ == "__main__":
    unittest.main()
