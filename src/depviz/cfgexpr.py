"""Условия платформы ``cfg(...)`` у зависимостей Cargo.

Зависимость может быть указана только для части платформ, например
``cfg(windows)`` или ``cfg(all(unix, not(target_os = "macos")))``.
Граф строится для всех платформ сразу, поэтому условие вычисляется в
трёхзначной логике: True — истинно всегда, False — ложно на любой
платформе, None — зависит от платформы. Зависимость не учитывается,
только если её условие ложно всегда. Так отбрасываются, например,
записи ``cfg(any())``: пустой any ложен, и пакеты (serde и другие)
используют такую запись, чтобы закрепить версию зависимости, на самом
деле её не подключая.

Строка без ``cfg(``, например ``x86_64-pc-windows-gnu``, — это имя
целевой платформы; оно считается возможным (None).
"""
import re

TOKEN_RE = re.compile(r'\s*(?:(?P<word>[A-Za-z_][A-Za-z0-9_]*)'
                      r'|(?P<string>"[^"]*")|(?P<symbol>[(),=]))')
COMBINATORS = ("any", "all", "not")


class CfgError(ValueError):
    """Выражение cfg не удалось разобрать."""


def tokenize(text):
    """Разбить выражение на слова, строки и символы ``( ) , =``."""
    tokens = []
    position = 0
    text = text.strip()
    while position < len(text):
        match = TOKEN_RE.match(text, position)
        if not match or match.end() == position:
            raise CfgError("неверное выражение cfg: " + text)
        tokens.append(match.group(match.lastgroup))
        position = match.end()
    return tokens


def single(values, message):
    """Вернуть единственное значение списка или сообщить об ошибке."""
    try:
        (value,) = values
    except ValueError:
        raise CfgError(message)
    return value


def combine(name, values):
    """Вычислить any/all/not в трёхзначной логике."""
    if name == "not":
        value = single(values, "not принимает ровно одно условие")
        return None if value is None else not value
    decisive = name == "any"
    if decisive in values:
        return decisive
    if None in values:
        return None
    return not decisive


def parse_expression(tokens, position):
    """Разобрать выражение с позиции; вернуть (значение, новая позиция).

    Разбор итеративный по аргументам и рекурсивный только по
    вложенности скобок, глубина которой в реальных cfg невелика.
    """
    word = tokens[position]
    position += 1
    if word in COMBINATORS and tokens[position:position + 1] == ["("]:
        values, position = parse_arguments(tokens, position + 1)
        return combine(word, values), position
    if tokens[position:position + 1] == ["="]:
        position += 2
    return None, position


def parse_arguments(tokens, position):
    """Разобрать список условий через запятую до закрывающей скобки."""
    values = []
    while tokens[position] != ")":
        value, position = parse_expression(tokens, position)
        values.append(value)
        if tokens[position] == ",":
            position += 1
    return values, position + 1


def evaluate(target):
    """Вычислить условие платформы: True, False или None.

    Пустая строка (зависимость для всех платформ) — True.
    """
    if not target:
        return True
    if not target.startswith("cfg("):
        return None
    tokens = tokenize(target)
    try:
        values, position = parse_arguments(tokens, 2)
    except IndexError:
        raise CfgError("неверное выражение cfg: " + target)
    if position != len(tokens):
        raise CfgError("неверное выражение cfg: " + target)
    return single(values, "неверное выражение cfg: " + target)


def can_be_enabled(target):
    """Может ли зависимость с таким условием быть подключена.

    Неразборчивое условие считается возможным, чтобы не потерять
    зависимость.
    """
    try:
        return evaluate(target) is not False
    except CfgError:
        return True
