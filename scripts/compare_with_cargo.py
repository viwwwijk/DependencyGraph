"""Сравнение порядка загрузки depviz с реальным менеджером пакетов Cargo.

Использование:
    PYTHONPATH=src python3 scripts/compare_with_cargo.py test ФАЙЛ ПАКЕТ
    PYTHONPATH=src python3 scripts/compare_with_cargo.py remote ПАКЕТ ВЕРСИЯ

В режиме test по графу из файла тестового репозитория создаются
настоящие локальные пакеты Cargo (pkg_a, pkg_b, ...) с зависимостями
через path, в режиме remote — пустой проект, зависящий от пакета
crates.io заданной версии. Затем выполняется cargo build -j1 (сборка в
один поток, чтобы порядок был последовательным), и из JSON-сообщений
Cargo (compiler-artifact) берётся порядок, в котором собирались
библиотеки пакетов. Этот порядок сравнивается с выводом depviz.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from depviz.graph import build_graph
from depviz.loadorder import load_order
from depviz.sources import FileSource, RemoteSource
from depviz.testing_repo import load_test_repo

INDEX = "https://index.crates.io"
PROBE = "depviz_probe"
PREFIX = "pkg_"
BUILD_SCRIPT = "custom-build"
MANIFEST = """[package]
name = "{name}"
version = "0.1.0"
edition = "2021"

[dependencies]
{dependencies}
"""


def crate_name(package):
    """Имя пакета Cargo для пакета тестового репозитория."""
    return PREFIX + package.lower()


def write_crate(root, name, dependencies):
    """Создать каталог пакета Cargo с Cargo.toml и пустой библиотекой."""
    folder = root / name
    (folder / "src").mkdir(parents=True)
    (folder / "src" / "lib.rs").write_text("")
    (folder / "Cargo.toml").write_text(MANIFEST.format(
        name=name, dependencies="\n".join(dependencies)))
    return folder


def make_test_workspace(root, path, package):
    """Создать пакеты Cargo по файлу тестового репозитория."""
    for name, children in load_test_repo(path).items():
        lines = ['{0} = {{ path = "../{0}" }}'.format(crate_name(child))
                 for child in children]
        folder = write_crate(root, crate_name(name), lines)
        if name == package:
            target = folder
    return target


def make_remote_project(root, package, version):
    """Создать проект, зависящий от пакета crates.io точной версии."""
    line = '{0} = "={1}"'.format(package, version)
    return write_crate(root, PROBE, [line])


def cargo_order(folder, offline):
    """Собрать проект Cargo и вернуть порядок сборки или ошибку.

    Возвращает пару (список «имя версия», текст ошибки или "").
    """
    command = ["cargo", "build", "-j1", "--message-format=json"]
    if offline:
        command.append("--offline")
    done = subprocess.run(command, cwd=folder, capture_output=True,
                          text=True)
    if done.returncode:
        return [], first_error(done.stderr)
    order = []
    for line in done.stdout.splitlines():
        message = json.loads(line)
        if message.get("reason") != "compiler-artifact":
            continue
        if BUILD_SCRIPT in message["target"]["kind"]:
            continue
        order.append(artifact_label(message, offline))
    return order, ""


def first_error(stderr):
    """Первое сообщение об ошибке Cargo вместе со строками продолжения."""
    lines = stderr.splitlines()
    starts = [index for index, line in enumerate(lines)
              if line.startswith("error")]
    if not starts:
        return stderr.strip()
    block = [lines[starts[0]]]
    for line in lines[starts[0] + 1:]:
        if not line.strip() or line.startswith("error"):
            break
        block.append(line.strip())
    return " ".join(block)


def artifact_label(message, offline):
    """Имя пакета (и версия для crates.io) из сообщения Cargo.

    package_id имеет вид «источник#имя@версия»; у локального пакета
    имя опускается, если совпадает с именем каталога.
    """
    tail = message["package_id"].split("#")[-1]
    if "@" in tail:
        name, version = tail.split("@")
    else:
        name, version = Path(message["manifest_path"]).parent.name, tail
    if offline:
        return name[len(PREFIX):].upper()
    return name + " " + version


def depviz_order(mode, first, second):
    """Граф и порядок загрузки по данным depviz."""
    if mode == "test":
        graph = build_graph(FileSource(first), second, "latest")
    else:
        graph = build_graph(RemoteSource(INDEX), first, second)
    return graph, load_order(graph)


def violations(order, graph):
    """Рёбра графа, для которых зависимость загружена позже пакета."""
    position = {label: index for index, label in enumerate(order)}
    bad = []
    for package, children in graph.edges.items():
        for child in children:
            first, second = str(child), str(package)
            if first in position and second in position \
                    and position[first] > position[second]:
                bad.append(second + " раньше " + first)
    return bad


def print_report(graph, result, cargo, error):
    """Вывести оба порядка рядом и итог сравнения."""
    ours = [str(item) for item in result.order]
    print("depviz:", " -> ".join(ours) or "(пусто)")
    if result.blocked:
        print("depviz, нельзя загрузить (циклы):",
              ", ".join(str(item) for item in result.blocked))
    if error:
        print("cargo: ошибка:", error)
        return
    print("cargo: ", " -> ".join(cargo))
    if ours == cargo:
        print("Итог: порядки совпадают полностью")
        return
    print_differences(graph, ours, cargo)


def print_differences(graph, ours, cargo):
    """Вывести, чем различаются порядки depviz и Cargo."""
    only_ours = sorted(set(ours) - set(cargo))
    only_cargo = sorted(set(cargo) - set(ours))
    print("Итог: порядки различаются")
    print("  только в depviz:", ", ".join(only_ours) or "нет")
    print("  только в cargo: ", ", ".join(only_cargo) or "нет")
    bad = violations(cargo, graph)
    print("  порядок cargo нарушает рёбра графа depviz:",
          ", ".join(bad) or "нет")


def main(argv):
    """Разобрать аргументы и выполнить сравнение."""
    mode, first, second = argv
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        if mode == "test":
            folder = make_test_workspace(root, first, second)
        else:
            folder = make_remote_project(root, first, second)
        cargo, error = cargo_order(folder, offline=mode == "test")
    probe = PROBE + " "
    cargo = [item for item in cargo if not item.startswith(probe)]
    graph, result = depviz_order(mode, first, second)
    print_report(graph, result, cargo, error)


if __name__ == "__main__":
    main(sys.argv[1:])
