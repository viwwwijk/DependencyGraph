"""Разбор и сравнение версий по правилам Semantic Versioning 2.0.

Используется для выбора последней версии пакета (``--version latest``)
без сторонних библиотек.
"""
from depviz.validators import SEMVER_RE

NUMERIC_IDENTIFIER = 0
TEXT_IDENTIFIER = 1


class VersionError(ValueError):
    """Строка не является версией SemVer."""


def parse_version(text):
    """Разобрать версию ``X.Y.Z[-пререлиз][+сборка]``.

    Возвращает кортеж (major, minor, patch, пререлиз), где пререлиз —
    список частей после ``-``. Метаданные сборки отбрасываются: по
    SemVer они не влияют на порядок версий.
    """
    match = SEMVER_RE.fullmatch(text)
    if not match:
        raise VersionError("неверная версия: " + text)
    core, _, rest = text.partition("+")[0].partition("-")
    major, minor, patch = (int(part) for part in core.split("."))
    prerelease = rest.split(".") if rest else []
    return major, minor, patch, prerelease


def is_prerelease(text):
    """Проверить, что версия — пререлиз (например, 1.0.0-beta.1)."""
    return bool(parse_version(text)[3])


def identifier_key(identifier):
    """Ключ части пререлиза: числа меньше строк и сравниваются как числа."""
    if identifier.isdigit():
        return NUMERIC_IDENTIFIER, int(identifier), ""
    return TEXT_IDENTIFIER, 0, identifier


def version_key(text):
    """Ключ сортировки версии по правилам SemVer.

    Версия без пререлиза больше любой своей пререлизной версии:
    ``1.0.0-rc.1 < 1.0.0``. Пререлизы сравниваются по частям слева
    направо, более короткий набор частей меньше.
    """
    major, minor, patch, prerelease = parse_version(text)
    release_flag = 0 if prerelease else 1
    parts = [identifier_key(part) for part in prerelease]
    return major, minor, patch, release_flag, parts
