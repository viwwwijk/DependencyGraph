"""Построение графа зависимостей обходом в ширину (этап 3).

Граф строится алгоритмом BFS без рекурсии: пакеты обрабатываются из
очереди collections.deque в порядке удаления от корня. Каждый пакет
попадает в очередь не больше одного раза (множество seen), поэтому
циклические зависимости не приводят к бесконечному обходу: ребро к
уже встреченному пакету записывается, но пакет повторно не
обрабатывается. Циклы затем находятся отдельно и выводятся.

Источник данных (source) должен предоставлять три метода:

- ``root(name, version)`` — корневой пакет;
- ``dependencies(package)`` — пары (имя, требование к версии) прямых
  зависимостей пакета;
- ``resolve(name, requirement)`` — пакет-зависимость или None, если
  подходящую версию найти не удалось (причина — в source.problems).
"""
from collections import deque
from dataclasses import dataclass, field

from depviz.registry import DataError

WHITE, GRAY, BLACK = range(3)


@dataclass(frozen=True)
class Package:
    """Вершина графа: имя пакета и выбранная версия (в тестовом режиме
    версии нет)."""

    name: str
    version: str = ""

    def __str__(self):
        """Имя и версия через пробел, например ``serde 1.0.229``."""
        return (self.name + " " + self.version).strip()


@dataclass
class Graph:
    """Граф зависимостей.

    nodes — пакеты в порядке обхода в ширину, edges — прямые
    зависимости каждого пакета, excluded — имена пакетов, исключённых
    фильтром, cycles — найденные циклы, problems — зависимости, для
    которых не удалось выбрать версию.
    """

    root: Package
    nodes: list = field(default_factory=list)
    edges: dict = field(default_factory=dict)
    excluded: list = field(default_factory=list)
    cycles: list = field(default_factory=list)
    problems: list = field(default_factory=list)

    def edge_count(self):
        """Число рёбер графа."""
        return sum(len(children) for children in self.edges.values())


def is_excluded(name, substring):
    """Проверить, что имя пакета содержит подстроку фильтра."""
    return bool(substring) and substring in name


def build_graph(source, name, version, substring=""):
    """Построить граф зависимостей пакета обходом в ширину.

    Пакеты, имя которых содержит substring, не учитываются: они не
    попадают в граф, их зависимости не загружаются. Если фильтр
    исключает сам корневой пакет, возбуждается DataError.
    """
    if is_excluded(name, substring):
        raise DataError("пакет " + name + " исключён фильтром «"
                        + substring + "», анализировать нечего")
    graph = Graph(source.root(name, version))
    queue = deque([graph.root])
    seen = {graph.root}
    while queue:
        package = queue.popleft()
        graph.nodes.append(package)
        graph.edges[package] = expand(source, package, substring, graph)
        for child in graph.edges[package]:
            if child not in seen:
                seen.add(child)
                queue.append(child)
    graph.problems = list(source.problems)
    graph.cycles = find_cycles(graph)
    return graph


def expand(source, package, substring, graph):
    """Вернуть прямые зависимости пакета, учитывая фильтр.

    Исключённые фильтром имена запоминаются в graph.excluded.
    Повторяющиеся зависимости (например, обычная и build) дают одно
    ребро.
    """
    children = []
    for name, requirement in source.dependencies(package):
        if is_excluded(name, substring):
            if name not in graph.excluded:
                graph.excluded.append(name)
            continue
        child = source.resolve(name, requirement)
        if child is not None and child not in children:
            children.append(child)
    return children


def find_cycles(graph):
    """Найти циклы графа поиском в глубину без рекурсии.

    Используется явный стек и раскраска вершин: ребро в «серую»
    вершину (она ещё в стеке) замыкает цикл. Каждый цикл возвращается
    списком пакетов, первый пакет повторяется в конце; одинаковые циклы,
    найденные с разных вершин, выводятся один раз.
    """
    color = {package: WHITE for package in graph.nodes}
    cycles = []
    for start in graph.nodes:
        if color[start] == WHITE:
            walk_from(start, graph.edges, color, cycles)
    return cycles


def walk_from(start, edges, color, cycles):
    """Обойти в глубину вершины, достижимые из start, собирая циклы."""
    path = [start]
    stack = [iter(edges.get(start, []))]
    color[start] = GRAY
    while stack:
        child = next(stack[-1], None)
        if child is None:
            color[path.pop()] = BLACK
            stack.pop()
        elif color.get(child, BLACK) == GRAY:
            add_cycle(path[path.index(child):] + [child], cycles)
        elif color.get(child) == WHITE:
            color[child] = GRAY
            path.append(child)
            stack.append(iter(edges.get(child, [])))


def add_cycle(cycle, cycles):
    """Добавить цикл, если такого же (с точностью до сдвига) ещё нет."""
    body = cycle[:-1]
    rotations = [body[index:] + body[:index] for index in range(len(body))]
    if not any(existing[:-1] in rotations for existing in cycles):
        cycles.append(cycle)


def format_cycle(cycle):
    """Цикл в виде ``A -> B -> A``."""
    return " -> ".join(str(package) for package in cycle)
