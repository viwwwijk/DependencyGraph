"""Модульные тесты для depviz.versionreq."""
import unittest

from depviz.versionreq import RequirementError, matches


class MatchesTest(unittest.TestCase):
    """Проверка требований к версиям по правилам Cargo."""

    def check(self, cases):
        """Проверить список (требование, версия, ожидаемый результат)."""
        for requirement, version, expected in cases:
            with self.subTest(requirement=requirement, version=version):
                self.assertEqual(matches(requirement, version), expected)

    def test_caret(self):
        """^ и требование без оператора: совместимые обновления."""
        self.check([
            ("^1.2.3", "1.9.0", True), ("^1.2.3", "2.0.0", False),
            ("^1.2.3", "1.2.2", False), ("1.2", "1.5.0", True),
            ("^0.2.3", "0.2.9", True), ("^0.2.3", "0.3.0", False),
            ("^0.0.3", "0.0.3", True), ("^0.0.3", "0.0.4", False),
            ("^0.0", "0.0.9", True), ("^0.0", "0.1.0", False),
            ("^0", "0.9.9", True), ("1", "1.99.0", True),
        ])

    def test_tilde(self):
        """~: обновления последнего указанного числа."""
        self.check([
            ("~1.2.3", "1.2.9", True), ("~1.2.3", "1.3.0", False),
            ("~1.2", "1.2.0", True), ("~1", "1.9.0", True),
            ("~1", "2.0.0", False),
        ])

    def test_wildcard_and_exact(self):
        """*, частичные версии со звёздочкой и =."""
        self.check([
            ("*", "9.9.9", True), ("1.*", "1.4.0", True),
            ("1.*", "2.0.0", False), ("1.2.*", "1.2.7", True),
            ("1.2.*", "1.3.0", False), ("=1.2.3", "1.2.3", True),
            ("=1.2.3", "1.2.4", False), ("=1.2", "1.2.9", True),
        ])

    def test_comparisons(self):
        """>, >=, <, <= и несколько условий через запятую."""
        self.check([
            (">1.2.3", "1.2.4", True), (">1.2.3", "1.2.3", False),
            (">1.2", "1.2.9", False), (">1.2", "1.3.0", True),
            (">=1.2", "1.2.0", True), ("<1.2", "1.2.0", False),
            ("<=1.2", "1.2.9", True), ("<=1.2", "1.3.0", False),
            (">=1.0, <1.5", "1.4.9", True), (">=1.0, <1.5", "1.5.0", False),
        ])

    def test_prerelease(self):
        """Пререлиз подходит только при пререлизе в требовании."""
        self.check([
            ("^1.0", "2.0.0-alpha", False), ("^1.0", "1.5.0-beta", False),
            ("^1.2.3-beta.1", "1.2.3-beta.2", True),
            ("^1.2.3-beta.1", "1.2.3", True),
            ("^1.2.3-beta.1", "1.2.4-beta", False),
            ("^1", "1.0.0+build", True),
        ])

    def test_invalid(self):
        """Неверное требование — ошибка, неверная версия — не подходит."""
        for requirement in ("", "abc", "^^1", ">=1.0, foo"):
            with self.subTest(requirement=requirement):
                with self.assertRaises(RequirementError):
                    matches(requirement, "1.0.0")
        self.assertFalse(matches("^1", "1.0"))


if __name__ == "__main__":
    unittest.main()
