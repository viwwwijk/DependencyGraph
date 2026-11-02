"""Параметры приложения из опций командной строки (этап 1).

Опции разбираются стандартным модулем argparse, после чего каждое
значение проверяется функциями из модуля validators. Все найденные
ошибки собираются вместе, чтобы пользователь увидел их за один запуск.
"""
import argparse
import re
from dataclasses import dataclass

from depviz.validators import (LATEST_VERSION, MODE_REMOTE, MODE_TEST,
                               validate_filter, validate_mode,
                               validate_output, validate_package,
                               validate_repo, validate_version)

DEFAULT_OUTPUT = "graph.svg"
REQUIRED_OPTIONS = (("package", "--package"), ("repo", "--repo"))
ARGPARSE_MESSAGES = (
    (re.compile(r"unrecognized arguments: (.*)"),
     "неизвестные аргументы: {0}"),
    (re.compile(r"argument (\S+): expected one argument"),
     "параметр {0}: не указано значение"),
)


class ConfigError(Exception):
    """Ошибка в параметрах командной строки.

    Поле errors содержит список сообщений — по одному на каждую
    найденную ошибку.
    """

    def __init__(self, errors):
        """Создать ошибку со списком сообщений errors."""
        super().__init__("\n".join(errors))
        self.errors = list(errors)


@dataclass
class Config:
    """Проверенные параметры, заданные пользователем."""

    package: str
    repo: str
    mode: str
    version: str
    output: str
    filter: str

    def items(self):
        """Вернуть пары (ключ, значение) в порядке вывода."""
        return [
            ("package", self.package),
            ("repo", self.repo),
            ("mode", self.mode),
            ("version", self.version),
            ("output", self.output),
            ("filter", self.filter),
        ]


class RussianArgumentParser(argparse.ArgumentParser):
    """ArgumentParser, который сообщает об ошибках исключением."""

    def error(self, message):
        """Превратить ошибку разбора в ConfigError на русском языке."""
        raise ConfigError([translate_argparse_message(message)])


def translate_argparse_message(message):
    """Перевести типичное сообщение argparse на русский язык."""
    for pattern, template in ARGPARSE_MESSAGES:
        match = pattern.fullmatch(message)
        if match:
            return template.format(*match.groups())
    return message


def build_parser():
    """Создать парсер опций командной строки."""
    parser = RussianArgumentParser(
        prog="depviz",
        description="Визуализация графа зависимостей пакетов Cargo",
        allow_abbrev=False,
    )
    parser.add_argument("--package", help="имя анализируемого пакета")
    parser.add_argument(
        "--repo",
        help="URL-адрес репозитория или путь к файлу тестового "
             "репозитория (в режиме test)")
    parser.add_argument(
        "--mode", default=MODE_REMOTE,
        help="режим работы: " + MODE_REMOTE + " — реальный репозиторий "
             "по URL, " + MODE_TEST + " — файл тестового репозитория "
             "(по умолчанию " + MODE_REMOTE + ")")
    parser.add_argument(
        "--version", default=LATEST_VERSION,
        help="версия пакета X.Y.Z или " + LATEST_VERSION
             + " (по умолчанию " + LATEST_VERSION + ")")
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT,
        help="имя файла с изображением графа (по умолчанию "
             + DEFAULT_OUTPUT + ")")
    parser.add_argument(
        "--filter", default=None,
        help="не учитывать пакеты, имя которых содержит эту подстроку")
    return parser


def collect_errors(args):
    """Проверить все параметры и вернуть список сообщений об ошибках.

    Имя пакета и адрес репозитория проверяются по правилам выбранного
    режима, поэтому при неверном режиме проверяется только то, что
    они заданы.
    """
    errors = []
    for name, option in REQUIRED_OPTIONS:
        if getattr(args, name) is None:
            errors.append(option + ": обязательный параметр не задан")
    mode_error = validate_mode(args.mode)
    checks = [("--mode", mode_error)]
    if not mode_error:
        if args.package is not None:
            checks.append(("--package",
                           validate_package(args.package, args.mode)))
        if args.repo is not None:
            checks.append(("--repo", validate_repo(args.repo, args.mode)))
    checks.append(("--version", validate_version(args.version)))
    checks.append(("--output", validate_output(args.output)))
    checks.append(("--filter", validate_filter(args.filter)))
    errors.extend(option + ": " + text for option, text in checks if text)
    return errors


def load_config(argv):
    """Разобрать и проверить опции командной строки argv.

    Возвращает Config или возбуждает ConfigError со всеми ошибками.
    """
    args = build_parser().parse_args(argv)
    errors = collect_errors(args)
    if errors:
        raise ConfigError(errors)
    return Config(args.package, args.repo, args.mode, args.version,
                  args.output, args.filter or "")
