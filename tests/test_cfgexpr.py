"""Модульные тесты для depviz.cfgexpr."""
import unittest

from depviz.cfgexpr import CfgError, can_be_enabled, evaluate


class EvaluateTest(unittest.TestCase):
    """Проверка трёхзначного вычисления условий cfg."""

    def test_values(self):
        """True — всегда, False — никогда, None — зависит от платформы."""
        cases = [
            ("", True), ("cfg(any())", False), ("cfg(all())", True),
            ("cfg(unix)", None), ("cfg(not(any()))", True),
            ("cfg(not(all()))", False), ("cfg(all(unix, any()))", False),
            ("cfg(any(unix, all()))", True),
            ('cfg(target_os = "linux")', None),
            ('cfg(all(unix, not(target_os = "macos")))', None),
            ("cfg(any(windows, unix,))", None),
            ("x86_64-pc-windows-gnu", None),
        ]
        for target, expected in cases:
            with self.subTest(target=target):
                self.assertIs(evaluate(target), expected)

    def test_errors(self):
        """Неверные выражения вызывают CfgError."""
        for target in ("cfg(unix", "cfg(not(unix, windows))", "cfg(a b)",
                       "cfg(unix) x", "cfg(#)"):
            with self.subTest(target=target):
                with self.assertRaises(CfgError):
                    evaluate(target)

    def test_can_be_enabled(self):
        """Отбрасывается только всегда ложное условие."""
        self.assertFalse(can_be_enabled("cfg(any())"))
        self.assertTrue(can_be_enabled("cfg(windows)"))
        self.assertTrue(can_be_enabled("cfg(unix"))


if __name__ == "__main__":
    unittest.main()
