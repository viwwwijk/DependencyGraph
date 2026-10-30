#!/bin/sh
# Этап 3: граф зависимостей на различных случаях тестового репозитория.
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
G=examples/graphs
echo "## Порядок обхода в ширину, недостижимый пакет X не попадает в граф"
run --mode test --repo $G/bfs_order.txt --package A
echo "## Ромб: общая зависимость обрабатывается один раз"
run --mode test --repo $G/diamond.txt --package A
echo "## Циклические зависимости и петля"
run --mode test --repo $G/cycles.txt --package A
run --mode test --repo $G/cycles.txt --package D
run --mode test --repo $G/cycles.txt --package F
echo "## Фильтр по подстроке"
run --mode test --repo $G/filter.txt --package APP
run --mode test --repo $G/filter.txt --package APP --filter TEST
echo "## Фильтр разрывает цикл A -> B -> C -> A"
run --mode test --repo $G/cycles.txt --package A --filter C
echo "## Неописанная зависимость: ошибка, если её не исключил фильтр"
run --mode test --repo $G/missing.txt --package A
run --mode test --repo $G/missing.txt --package A --filter C
echo "## Фильтр исключает сам анализируемый пакет"
run --mode test --repo $G/filter.txt --package APP --filter AP
