"""Порядок загрузки зависимостей (этап 4).

Пакет можно загрузить только после всех его зависимостей, поэтому
порядок загрузки — это топологическая сортировка графа, в которой
зависимости идут раньше зависящих от них пакетов. Сортировка
выполняется алгоритмом Кана без рекурсии:

1. для каждого пакета считается число его ещё не загруженных
   зависимостей;
2. пакеты, у которых это число равно нулю, готовы к загрузке;
3. из готовых загружается пакет с наибольшим числом пакетов, которые
   от него зависят (прямо или транзитивно), при равенстве — первый
   по алфавиту; так же выбирает следующую задачу Cargo, чтобы раньше
   освободить длинные цепочки;
4. у пакетов, зависящих от загруженного, счётчик уменьшается, и
   шаги 2–4 повторяются.

Пакеты, входящие в цикл, никогда не становятся готовыми: их
зависимости ждут друг друга. Такие пакеты и пакеты, зависящие от них,
загрузить нельзя; они возвращаются отдельно.
"""
import heapq
from collections import deque
from dataclasses import dataclass, field


@dataclass
class LoadOrder:
    """Результат: порядок загрузки и пакеты, которые загрузить нельзя."""

    order: list = field(default_factory=list)
    blocked: list = field(default_factory=list)


def dependents_of(edges):
    """Обратные рёбра: для каждого пакета — пакеты, зависящие от него."""
    dependents = {package: [] for package in edges}
    for package, children in edges.items():
        for child in children:
            dependents.setdefault(child, []).append(package)
    return dependents


def dependent_counts(edges, dependents):
    """Число пакетов, транзитивно зависящих от каждого пакета.

    Для каждого пакета выполняется обход в ширину по обратным рёбрам
    (без рекурсии); циклы не мешают благодаря множеству seen.
    """
    counts = {}
    for package in edges:
        seen = {package}
        queue = deque([package])
        while queue:
            for parent in dependents.get(queue.popleft(), []):
                if parent not in seen:
                    seen.add(parent)
                    queue.append(parent)
        counts[package] = len(seen) - 1
    return counts


def load_order(graph):
    """Порядок загрузки пакетов графа (алгоритм Кана)."""
    edges = graph.edges
    dependents = dependents_of(edges)
    counts = dependent_counts(edges, dependents)
    waiting = {package: len(set(children))
               for package, children in edges.items()}
    ready = [(-counts[package], str(package), package)
             for package, number in waiting.items() if not number]
    heapq.heapify(ready)
    result = LoadOrder()
    while ready:
        package = heapq.heappop(ready)[2]
        result.order.append(package)
        for parent in set(dependents.get(package, [])):
            waiting[parent] -= 1
            if not waiting[parent]:
                heapq.heappush(ready, (-counts[parent], str(parent), parent))
    loaded = set(result.order)
    result.blocked = [package for package in graph.nodes
                      if package not in loaded]
    return result
