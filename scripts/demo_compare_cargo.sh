#!/bin/sh
# Этап 4: сравнение порядка загрузки depviz с реальным Cargo.
# Нужен установленный Cargo (https://rustup.rs) и доступ к crates.io.
cd "$(dirname "$0")/.."
compare() {
    echo "\$ compare_with_cargo.py $*"
    PYTHONPATH=src python3 scripts/compare_with_cargo.py "$@"
    echo
}
G=examples/graphs
echo "## Тестовые репозитории: локальные пакеты Cargo по графу"
compare test $G/layers.txt A
compare test $G/diamond.txt A
compare test $G/bfs_order.txt A
compare test $G/filter.txt APP
compare test $G/partial_cycle.txt A
compare test $G/cycles.txt A
echo "## Пакеты crates.io"
compare remote serde 1.0.229
compare remote serde_json 1.0.120
compare remote url 2.5.2
compare remote tokio 1.38.0
compare remote regex 1.10.5
