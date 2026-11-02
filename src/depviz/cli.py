"""Запуск приложения из командной строки.

Приложение строит граф зависимостей заданного пакета с учётом
транзитивности (этап 3: обход в ширину, фильтр, циклы) и
визуализирует его (этап 5): выводит текстовое представление графа на
языке диаграмм Graphviz (DOT) в стандартный поток вывода и сохраняет
изображение графа в файл SVG (--output). Сообщение о сохранённом файле
и предупреждения выводятся в стандартный поток ошибок, поэтому вывод
можно перенаправить в файл .dot.

Коды завершения: 0 — успех, 1 — ошибка получения данных, 2 — ошибка
параметров, 3 — не удалось сохранить изображение.
"""
import sys

from depviz.config import ConfigError, load_config
from depviz.dot import to_dot
from depviz.graph import build_graph
from depviz.registry import DataError
from depviz.render import RenderError, render_svg
from depviz.sources import FileSource, RemoteSource
from depviz.validators import LATEST_VERSION, MODE_TEST

EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_RENDER_ERROR = 3


def describe_scope(config):
    """Описание того, какие зависимости учитываются в графе."""
    if config.mode == MODE_TEST:
        return "Тестовый репозиторий: " + config.repo
    return ("Репозиторий: " + config.repo + "\nУчитываются обычные и "
            "build-зависимости, кроме необязательных (optional)")


def make_source(config, stderr):
    """Источник данных для выбранного режима."""
    if config.mode == MODE_TEST:
        if config.version != LATEST_VERSION:
            print("предупреждение: --version не используется в тестовом "
                  "режиме", file=stderr)
        return FileSource(config.repo)
    return RemoteSource(config.repo)


def build_dot(config, stderr):
    """Построить граф и вернуть пару (граф, текст на языке DOT)."""
    graph = build_graph(make_source(config, stderr), config.package,
                        config.version, config.filter)
    return graph, to_dot(graph, describe_scope(config), config.filter)


def saved_message(graph, output):
    """Сообщение о сохранённом изображении."""
    return ("Изображение графа сохранено в файл " + output + " (пакетов: "
            + str(len(graph.nodes)) + ", связей: "
            + str(graph.edge_count()) + ", циклов: "
            + str(len(graph.cycles)) + ")")


def main(argv=None, stdout=None, stderr=None):
    """Разобрать параметры, вывести граф на языке DOT и сохранить SVG.

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
        graph, dot_text = build_dot(config, stderr)
    except DataError as error:
        print("ошибка: " + str(error), file=stderr)
        return EXIT_DATA_ERROR
    stdout.write(dot_text)
    try:
        render_svg(dot_text, config.output)
    except RenderError as error:
        print("ошибка: " + str(error), file=stderr)
        return EXIT_RENDER_ERROR
    print(saved_message(graph, config.output), file=stderr)
    return EXIT_OK
