"""Требования к версиям зависимостей в формате Cargo.

Требование из Cargo.toml (``^1.2``, ``~0.4.3``, ``>=1, <2``, ``1.*``)
разбирается в список условий-диапазонов; версия подходит, если она
удовлетворяет всем условиям. Правила повторяют документацию Cargo:

- без оператора и ``^`` — совместимые обновления: ``^1.2.3`` это
  ``>=1.2.3, <2.0.0``, ``^0.2.3`` это ``>=0.2.3, <0.3.0``,
  ``^0.0.3`` это ``>=0.0.3, <0.0.4``;
- ``~`` — обновления последнего указанного числа: ``~1.2.3`` это
  ``>=1.2.3, <1.3.0``, ``~1`` это ``>=1.0.0, <2.0.0``;
- ``*``, ``1.*``, ``1.2.*`` — любые значения на месте звёздочки;
- ``=``, ``>``, ``>=``, ``<``, ``<=`` с полной или частичной версией.

Пререлиз (``1.0.0-beta``) подходит, только если в требовании есть
условие с пререлизом для тех же ``X.Y.Z``.
"""
import re
from dataclasses import dataclass, field

from depviz.semver import VersionError, identifier_key, parse_version

COMPARATOR_RE = re.compile(
    r"(?P<op>\^|~|=|>=|<=|>|<)?\s*"
    r"(?P<major>\d+|[*xX])(?:\.(?P<minor>\d+|[*xX]))?"
    r"(?:\.(?P<patch>\d+|[*xX]))?"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?")
WILDCARDS = ("*", "x", "X")
CARET = "^"


class RequirementError(ValueError):
    """Требование к версии не удалось разобрать."""


def key(major, minor=0, patch=0, pre=()):
    """Ключ сравнения версии, совместимый с semver.version_key."""
    release_flag = 0 if pre else 1
    return (major, minor, patch, release_flag,
            [identifier_key(part) for part in pre])


@dataclass
class Condition:
    """Одно условие требования: диапазон версий [low, high).

    low_inclusive — включается ли нижняя граница; high = None — нет
    верхней границы; high_inclusive — включается ли верхняя.
    triple — X.Y.Z условия с пререлизом (иначе None).
    """

    low: tuple = None
    low_inclusive: bool = True
    high: tuple = None
    high_inclusive: bool = False
    triple: tuple = None
    pre: list = field(default_factory=list)

    def contains(self, version):
        """Проверить, что ключ версии попадает в диапазон."""
        return self.above_low(version) and self.below_high(version)

    def above_low(self, version):
        """Версия не ниже нижней границы (или границы нет)."""
        if self.low is None or version > self.low:
            return True
        return version == self.low and self.low_inclusive

    def below_high(self, version):
        """Версия не выше верхней границы (или границы нет)."""
        if self.high is None or version < self.high:
            return True
        return version == self.high and self.high_inclusive


def number(text):
    """Число из части версии; None для отсутствующей части и ``*``."""
    if text is None or text in WILDCARDS:
        return None
    return int(text)


def caret_condition(major, minor, patch, pre):
    """Условие для ``^`` и требования без оператора."""
    low = key(major, minor or 0, patch or 0, pre)
    if major or minor is None:
        return Condition(low, True, key(major + 1))
    if minor or patch is None:
        return Condition(low, True, key(0, minor + 1))
    return Condition(low, True, key(0, 0, patch + 1))


def tilde_condition(major, minor, patch, pre):
    """Условие для ``~``."""
    low = key(major, minor or 0, patch or 0, pre)
    if minor is None:
        return Condition(low, True, key(major + 1))
    return Condition(low, True, key(major, minor + 1))


def partial_range(major, minor):
    """Диапазон всех версий с заданными major и (если есть) minor."""
    if minor is None:
        return key(major), key(major + 1)
    return key(major, minor), key(major, minor + 1)


def exact_condition(major, minor, patch, pre):
    """Условие для ``=`` и для частичной версии со звёздочкой."""
    if patch is not None:
        version = key(major, minor, patch, pre)
        return Condition(version, True, version, True)
    low, high = partial_range(major, minor)
    return Condition(low, True, high)


def greater_condition(op, major, minor, patch, pre):
    """Условие для ``>`` и ``>=``."""
    if op == ">=" or patch is not None:
        version = key(major, minor or 0, patch or 0, pre)
        return Condition(version, op == ">=")
    return Condition(partial_range(major, minor)[1], True)


def less_condition(op, major, minor, patch, pre):
    """Условие для ``<`` и ``<=``."""
    if op == "<" or patch is not None:
        version = key(major, minor or 0, patch or 0, pre)
        return Condition(high=version, high_inclusive=op == "<=")
    return Condition(high=partial_range(major, minor)[1])


def split_prerelease(text):
    """Части пререлиза требования (пустой список, если его нет)."""
    return text.split(".") if text else []


def comparator_parts(match):
    """Оператор, числа и пререлиз из разобранного условия.

    Звёздочка на месте числа превращает условие в «все версии с
    указанными числами» (как ``=`` с частичной версией).
    """
    parts = [match.group(name) for name in ("major", "minor", "patch")]
    major, minor, patch = (number(part) for part in parts)
    op = match.group("op") or CARET
    if any(part in WILDCARDS for part in parts):
        op, patch = "=", None
    return op, major, minor, patch, split_prerelease(match.group("pre"))


def parse_comparator(text):
    """Разобрать одно условие требования в Condition."""
    match = COMPARATOR_RE.fullmatch(text.strip())
    if not match:
        raise RequirementError("неверное требование к версии: " + text)
    op, major, minor, patch, pre = comparator_parts(match)
    if major is None:
        return Condition()
    condition = build_condition(op, major, minor, patch, pre)
    if pre and patch is not None:
        condition.triple = (major, minor, patch)
    return condition


def build_condition(op, major, minor, patch, pre):
    """Выбрать построитель условия по оператору."""
    if op == CARET:
        return caret_condition(major, minor, patch, pre)
    if op == "~":
        return tilde_condition(major, minor, patch, pre)
    if op == "=":
        return exact_condition(major, minor, patch, pre)
    if op in (">", ">="):
        return greater_condition(op, major, minor, patch, pre)
    return less_condition(op, major, minor, patch, pre)


def parse_requirement(text):
    """Разобрать требование вида ``>=1.2, <2`` в список условий."""
    parts = [part for part in text.split(",") if part.strip()]
    if not parts:
        raise RequirementError("пустое требование к версии")
    return [parse_comparator(part) for part in parts]


def matches(requirement, version):
    """Проверить, что версия удовлетворяет требованию (тексту)."""
    try:
        major, minor, patch, pre = parse_version(version)
    except VersionError:
        return False
    conditions = parse_requirement(requirement)
    version_key = key(major, minor, patch, pre)
    if not all(condition.contains(version_key)
               for condition in conditions):
        return False
    if not pre:
        return True
    return any(condition.triple == (major, minor, patch)
               for condition in conditions)
