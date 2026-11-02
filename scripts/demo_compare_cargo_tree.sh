#!/bin/sh
# Этап 5: сравнение графа depviz с выводом штатного инструмента cargo tree.
# Нужен установленный Cargo (https://rustup.rs) и доступ к crates.io.
cd "$(dirname "$0")/.."
compare() {
    echo "\$ compare_with_cargo_tree.py $*"
    PYTHONPATH=src python3 scripts/compare_with_cargo_tree.py "$@"
    echo
}
mkdir -p out
compare serde_json 1.0.120 out
compare url 2.5.2 out
compare regex 1.10.5 out
compare tokio 1.38.0 out
