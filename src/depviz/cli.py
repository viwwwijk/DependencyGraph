"""Запуск приложения из командной строки.

На этапе 3 приложение строит граф зависимостей заданного пакета с
учётом транзитивности (обход в ширину), исключает пакеты по
подстроке фильтра, находит циклы и выводит граф на экран. На этапе 4
добавлен режим --load-order: вместо графа выводится порядок загрузки
зависимостей. Ошибки
параметров завершают программу с кодом 2, ошибки получения данных —
с кодом 1.
"""
import sys

from depviz.config import ConfigError, load_config
from depviz.graph import build_graph, format_cycle
from depviz.loadorder import load_order
from depviz.registry import DataError
from depviz.sources import FileSource, RemoteSource
from depviz.validators import LATEST_VERSION, MODE_TEST

EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2
INDENT = "  "
NO_DEPENDENCIES = "нет зависимостей"


def describe_scope(config):
    """Описание того, какие зависимости учитываются в графе."""
    if config.mode == MODE_TEST:
        return "Тестовый репозиторий: " + config.repo
    return ("Репозиторий: " + config.repo + "\nУчитываются обычные и "
            "build-зависимости, кроме необязательных (optional)")


def format_graph(graph, config):
    """Отформатировать граф: список смежности в порядке обхода и итоги."""
    lines = ["Граф зависимостей: " + str(graph.root), describe_scope(config),
             "Пакетов: " + str(len(graph.nodes)) + ", связей: "
             + str(graph.edge_count()) + " (обход в ширину)"]
    for package in graph.nodes:
        children = graph.edges[package]
        listed = ", ".join(str(child) for child in children) or NO_DEPENDENCIES
        lines.append(INDENT + str(package) + " -> " + listed)
    if config.filter:
        excluded = ", ".join(graph.excluded) or "нет"
        lines.append("Исключены фильтром «" + config.filter + "»: " + excluded)
    lines.append(format_cycles(graph.cycles))
    lines.extend(format_problems(graph.problems))
    return "\n".join(lines)


def format_cycles(cycles):
    """Строки о найденных циклических зависимостях."""
    if not cycles:
        return "Циклические зависимости: нет"
    lines = ["Циклические зависимости (" + str(len(cycles)) + "):"]
    lines.extend(INDENT + format_cycle(cycle) for cycle in cycles)
    return "\n".join(lines)


def format_load_order(graph, config):
    """Отформатировать порядок загрузки зависимостей (этап 4)."""
    result = load_order(graph)
    lines = ["Порядок загрузки: " + str(graph.root), describe_scope(config),
             "Пакетов: " + str(len(graph.nodes)) + " (каждый пакет "
             "загружается после всех своих зависимостей)"]
    for number, package in enumerate(result.order, 1):
        lines.append(INDENT + str(number) + ". " + str(package))
    if not result.order:
        lines.append(INDENT + "нет пакетов, которые можно загрузить")
    if config.filter:
        excluded = ", ".join(graph.excluded) or "нет"
        lines.append("Исключены фильтром «" + config.filter + "»: " + excluded)
    if result.blocked:
        lines.append("Нельзя загрузить из-за циклических зависимостей ("
                     + str(len(result.blocked)) + "): "
                     + ", ".join(str(item) for item in result.blocked))
    lines.append(format_cycles(graph.cycles))
    lines.extend(format_problems(graph.problems))
    return "\n".join(lines)


def format_problems(problems):
    """Строки о зависимостях, для которых не удалось выбрать версию."""
    if not problems:
        return []
    return (["Не удалось выбрать версию (" + str(len(problems)) + "):"]
            + [INDENT + problem for problem in problems])


def build_report(config, stderr):
    """Построить граф в выбранном режиме и вернуть отчёт."""
    if config.mode == MODE_TEST:
        if config.version != LATEST_VERSION:
            print("предупреждение: --version не используется в тестовом "
                  "режиме", file=stderr)
        source = FileSource(config.repo)
    else:
        source = RemoteSource(config.repo)
    graph = build_graph(source, config.package, config.version,
                        config.filter)
    if config.load_order:
        return format_load_order(graph, config)
    return format_graph(graph, config)


def main(argv=None, stdout=None, stderr=None):
    """Разобрать параметры, вывести граф или порядок загрузки.

    Возвращает код завершения.
    """
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
