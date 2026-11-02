#!/bin/sh
# Этап 4: порядок загрузки зависимостей на разных случаях.
cd "$(dirname "$0")/.."
run() {
    printf '$ ./run.sh'
    for arg in "$@"; do
        case "$arg" in
            ""|*[!A-Za-z0-9._/:=-]*) printf " '%s'" "$arg" ;;
            *) printf ' %s' "$arg" ;;
        esac
    done
    printf '
'
    sh run.sh "$@"
    echo "[код завершения: $?]"
    echo
}
URL=https://index.crates.io
G=examples/graphs
echo "## Слои: сначала пакеты без зависимостей, корень последним"
run --mode test --repo $G/layers.txt --package A --load-order
echo "## Ромб: общая зависимость загружается один раз"
run --mode test --repo $G/diamond.txt --package A --load-order
echo "## Несколько уровней, недостижимый пакет X не загружается"
run --mode test --repo $G/bfs_order.txt --package A --load-order
echo "## Фильтр: исключённые пакеты не загружаются"
run --mode test --repo $G/filter.txt --package APP --load-order
run --mode test --repo $G/filter.txt --package APP --load-order --filter TEST
echo "## Частичный цикл: загружается всё, что не зависит от цикла"
run --mode test --repo $G/partial_cycle.txt --package A --load-order
echo "## Фильтр, исключивший пакет цикла, делает загрузку возможной"
run --mode test --repo $G/partial_cycle.txt --package A --load-order --filter E
echo "## Всё упирается в циклы: загрузить нельзя ничего"
run --mode test --repo $G/cycles.txt --package A --load-order
echo "## Реальные пакеты crates.io"
run --package serde_json --repo "$URL" --version 1.0.120 --load-order
run --package url --repo "$URL" --version 2.5.2 --load-order
