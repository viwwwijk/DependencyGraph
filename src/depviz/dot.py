"""Текстовое представление графа на языке диаграмм Graphviz (этап 5).

Граф зависимостей записывается на языке DOT: каждый пакет — вершина,
каждая прямая зависимость — ориентированное ребро «пакет ->
зависимость». Анализируемый пакет выделяется цветом, рёбра,
входящие в циклические зависимости, — красным цветом. В начале текста
комментариями (``//``) записываются итоги анализа: источник данных,
число пакетов и связей, исключённые фильтром пакеты, циклы и
зависимости, для которых не удалось выбрать версию.
"""
from depviz.graph import format_cycle

INDENT = "    "
FONT = "Helvetica"
GRAPH_ATTRIBUTES = ("rankdir=TB", "labelloc=t", "fontsize=16",
                    "fontname=" + '"' + FONT + '"')
NODE_ATTRIBUTES = ("shape=box", 'style="rounded,filled"',
                   'fillcolor="#f2f2f2"', 'color="#666666"',
                   'fontname="' + FONT + '"')
EDGE_ATTRIBUTES = ('color="#555555"', "arrowsize=0.7")
ROOT_ATTRIBUTES = ('fillcolor="#cfe2ff"', 'color="#1f4e9c"', "penwidth=2")
CYCLE_ATTRIBUTES = ('color="#d62728"', "penwidth=2")
TITLE = "Зависимости пакета"


def escape(text):
    """Экранировать обратную косую черту и кавычки для строки DOT."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def quote(text):
    """Строка DOT в кавычках."""
    return '"' + escape(text) + '"'


def attributes(items):
    """Список атрибутов DOT в квадратных скобках."""
    return "[" + ", ".join(items) + "]"


def node_label(package):
    """Подпись вершины: имя пакета и (если есть) версия на новой строке."""
    label = escape(package.name)
    if package.version:
        label += "\\n" + escape(package.version)
    return '"' + label + '"'


def cycle_edges(cycles):
    """Множество рёбер (пакет, зависимость), входящих в циклы."""
    edges = set()
    for cycle in cycles:
        edges.update(zip(cycle, cycle[1:]))
    return edges


def summary_comments(graph, scope, substring):
    """Комментарии DOT с итогами анализа графа."""
    lines = ["Граф зависимостей: " + str(graph.root)]
    lines.extend(scope.splitlines())
    lines.append("Пакетов: " + str(len(graph.nodes)) + ", связей: "
                 + str(graph.edge_count()))
    if substring:
        lines.append("Исключены фильтром «" + substring + "»: "
                     + (", ".join(graph.excluded) or "нет"))
    if graph.cycles:
        lines.append("Циклические зависимости (" + str(len(graph.cycles))
                     + "):")
        lines.extend(INDENT + format_cycle(cycle) for cycle in graph.cycles)
    else:
        lines.append("Циклические зависимости: нет")
    if graph.problems:
        lines.append("Не удалось выбрать версию:")
        lines.extend(INDENT + problem for problem in graph.problems)
    return ["// " + line for line in lines]


def graph_label(graph, substring, title=TITLE):
    """Заголовок изображения: корневой пакет и исключённые фильтром."""
    label = escape(title + " " + str(graph.root))
    if substring and graph.excluded:
        label += "\\nисключены фильтром «" + escape(substring) + "»: "
        label += escape(", ".join(graph.excluded))
    return '"' + label + '"'


def to_dot(graph, scope="", substring="", title=TITLE):
    """Записать граф на языке DOT.

    scope — описание источника данных (попадает в комментарии),
    substring — подстрока фильтра, если она задана, title — начало
    заголовка изображения.
    """
    lines = summary_comments(graph, scope, substring)
    lines.append("digraph dependencies {")
    lines.append(INDENT + "graph " + attributes(GRAPH_ATTRIBUTES))
    lines.append(INDENT + "label=" + graph_label(graph, substring, title))
    lines.append(INDENT + "node " + attributes(NODE_ATTRIBUTES))
    lines.append(INDENT + "edge " + attributes(EDGE_ATTRIBUTES))
    for package in graph.nodes:
        items = ("label=" + node_label(package),)
        if package == graph.root:
            items += ROOT_ATTRIBUTES
        lines.append(INDENT + quote(str(package)) + " " + attributes(items))
    in_cycle = cycle_edges(graph.cycles)
    for package in graph.nodes:
        for child in graph.edges[package]:
            line = quote(str(package)) + " -> " + quote(str(child))
            if (package, child) in in_cycle:
                line += " " + attributes(CYCLE_ATTRIBUTES)
            lines.append(INDENT + line)
    lines.append("}")
    return "\n".join(lines) + "\n"
