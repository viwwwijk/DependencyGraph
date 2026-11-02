"""Сравнение графа depviz со штатным инструментом Cargo — cargo tree.

Использование:
    PYTHONPATH=src python3 scripts/compare_with_cargo_tree.py \\
        ПАКЕТ ВЕРСИЯ [КАТАЛОГ_ДЛЯ_SVG]

Создаётся пустой проект Cargo, зависящий от пакета crates.io точной
версии, и для пакета выполняется cargo tree (для всех платформ,
обычные и build-зависимости — как в depviz). Скрипт выводит дерево
cargo tree, затем сравнивает пакеты и связи с графом depviz. Если
указан каталог, в него сохраняются два изображения для сравнения:
ПАКЕТ-depviz.svg и ПАКЕТ-cargo-tree.svg (оба рисуются Graphviz).
Нужен установленный Cargo (https://rustup.rs) и доступ к crates.io.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from depviz.dot import to_dot
from depviz.graph import Graph, Package, build_graph
from depviz.render import render_svg
from depviz.sources import RemoteSource

INDEX = "https://index.crates.io"
TREE_OPTIONS = ["--target", "all", "-e", "normal,build"]
LINE = re.compile(r"(\d+)(\S+) v(\S+)")
MANIFEST = """[package]
name = "depviz_probe"
version = "0.1.0"
edition = "2021"

[dependencies]
{0} = "={1}"
"""


def cargo_tree(name, version, prefix):
    """Выполнить cargo tree для пакета в пустом проекте-пробнике."""
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        (folder / "src").mkdir()
        (folder / "src" / "lib.rs").write_text("")
        (folder / "Cargo.toml").write_text(MANIFEST.format(name, version))
        command = (["cargo", "tree", "-p", name + "@" + version]
                   + TREE_OPTIONS + ["--prefix", prefix])
        if prefix == "depth":
            command += ["--format", "{p}"]
        done = subprocess.run(command, cwd=folder, capture_output=True,
                              encoding="utf-8")
    if done.returncode:
        sys.exit("ошибка cargo tree: " + done.stderr.strip())
    return done.stdout


def parse_tree(text):
    """Граф из вывода cargo tree --prefix depth --format {p}.

    Число в начале строки — глубина пакета в дереве; родитель пакета —
    последний пакет на глубину меньше. Пометка (*) означает, что
    зависимости пакета уже показаны выше.
    """
    graph = None
    path = []
    for line in text.splitlines():
        match = LINE.match(line)
        if not match:
            continue
        package = Package(match.group(2), match.group(3))
        del path[int(match.group(1)):]
        if graph is None:
            graph = Graph(package)
        if package not in graph.edges:
            graph.nodes.append(package)
            graph.edges[package] = []
        if path and package not in graph.edges[path[-1]]:
            graph.edges[path[-1]].append(package)
        path.append(package)
    return graph


def edge_set(graph):
    """Связи графа строками «пакет -> зависимость»."""
    return {str(package) + " -> " + str(child)
            for package, children in graph.edges.items()
            for child in children}


def print_difference(title, items):
    """Вывести элементы, которые есть только в одном графе."""
    if not items:
        print(title + ": нет")
        return
    print(title + " (" + str(len(items)) + "):")
    for item in sorted(items):
        print("    " + item)


def compare(ours, theirs):
    """Сравнить пакеты и связи графов depviz и cargo tree."""
    our_nodes = {str(package) for package in ours.nodes}
    their_nodes = {str(package) for package in theirs.nodes}
    print("Пакетов: depviz", len(our_nodes), "| cargo tree",
          len(their_nodes))
    print("Связей:  depviz", ours.edge_count(), "| cargo tree",
          theirs.edge_count())
    print_difference("Пакеты только в depviz", our_nodes - their_nodes)
    print_difference("Пакеты только в cargo tree", their_nodes - our_nodes)
    print_difference("Связи только в depviz", edge_set(ours)
                     - edge_set(theirs))
    print_difference("Связи только в cargo tree", edge_set(theirs)
                     - edge_set(ours))
    same = edge_set(ours) == edge_set(theirs) and our_nodes == their_nodes
    print("Итог:", "графы совпадают" if same else "графы различаются")


def save_images(folder, name, ours, theirs):
    """Сохранить изображения обоих графов для сравнения."""
    for suffix, graph in (("depviz", ours), ("cargo-tree", theirs)):
        path = os.path.join(folder, name + "-" + suffix + ".svg")
        title = suffix.replace("-", " ") + ": зависимости пакета"
        render_svg(to_dot(graph, "Построено: " + suffix, title=title), path)
        print("Изображение:", path)


def main(argv):
    """Разобрать аргументы и выполнить сравнение."""
    name, version, *folder = argv
    print("== cargo tree", name + "@" + version, " ".join(TREE_OPTIONS))
    print(cargo_tree(name, version, "indent"), end="")
    theirs = parse_tree(cargo_tree(name, version, "depth"))
    ours = build_graph(RemoteSource(INDEX), name, version)
    print("== Сравнение с depviz")
    compare(ours, theirs)
    if folder:
        os.makedirs(folder[0], exist_ok=True)
        save_images(folder[0], name, ours, theirs)


if __name__ == "__main__":
    main(sys.argv[1:])
