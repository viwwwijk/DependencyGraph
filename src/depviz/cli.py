"""Запуск приложения из командной строки.

На этапе 2 приложение проверяет параметры, получает прямые
зависимости заданной версии пакета и выводит их на экран. Ошибки
параметров завершают программу с кодом 2, ошибки получения данных —
с кодом 1.
"""
import sys

from depviz.config import ConfigError, load_config
from depviz.registry import DataError, remote_dependencies
from depviz.testing_repo import file_dependencies
from depviz.validators import LATEST_VERSION, MODE_TEST

EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2
INDENT = "  "


def describe_dependency(dependency):
    """Вернуть строку о зависимости: имя, требование к версии, пометки."""
    text = INDENT + dependency.name
    if dependency.req:
        text += " " + dependency.req
    notes = []
    if dependency.crate() != dependency.name:
        notes.append("пакет " + dependency.package)
    if dependency.kind != "normal":
        notes.append(dependency.kind)
    if dependency.optional:
        notes.append("необязательная")
    if dependency.target:
        notes.append("платформа " + dependency.target)
    if notes:
        text += " (" + ", ".join(notes) + ")"
    return text


def format_dependencies(title, dependencies):
    """Отформатировать заголовок и список прямых зависимостей."""
    if not dependencies:
        return title + "\nПрямые зависимости: нет"
    lines = [title, "Прямые зависимости (" + str(len(dependencies)) + "):"]
    lines.extend(describe_dependency(item) for item in dependencies)
    return "\n".join(lines)


def remote_report(config):
    """Получить зависимости из репозитория по URL и вернуть отчёт."""
    entry, dependencies = remote_dependencies(config.repo, config.package,
                                              config.version)
    title = "Пакет: " + config.package + " " + entry["vers"]
    if config.version == LATEST_VERSION:
        title += " (последняя версия)"
    if entry.get("yanked"):
        title += " (версия отозвана — yanked)"
    title += "\nРепозиторий: " + config.repo
    return format_dependencies(title, dependencies)


def test_mode_report(config):
    """Получить зависимости из файла тестового репозитория."""
    dependencies = file_dependencies(config.repo, config.package)
    title = ("Пакет: " + config.package + "\nТестовый репозиторий: "
             + config.repo)
    return format_dependencies(title, dependencies)


def build_report(config, stderr):
    """Получить зависимости в выбранном режиме и вернуть отчёт."""
    if config.mode != MODE_TEST:
        return remote_report(config)
    if config.version != LATEST_VERSION:
        print("предупреждение: --version не используется в тестовом "
              "режиме", file=stderr)
    return test_mode_report(config)


def main(argv=None, stdout=None, stderr=None):
    """Разобрать параметры, вывести прямые зависимости, вернуть код."""
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    try:
        config = load_config(sys.argv[1:] if argv is None else argv)
    except ConfigError as error:
        for message in error.errors:
            print("ошибка: " + message, file=stderr)
        return EXIT_CONFIG_ERROR
    try:
        report = build_report(config, stderr)
    except DataError as error:
        print("ошибка: " + str(error), file=stderr)
        return EXIT_DATA_ERROR
    print(report, file=stdout)
    return EXIT_OK
