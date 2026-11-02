#!/bin/sh
# Этап 5: визуализация графа (текст на языке Graphviz и файл SVG).
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
mkdir -p out
echo "## Три пакета crates.io: изображения в каталоге out/"
run --package serde_json --repo "$URL" --version 1.0.120 --output out/serde_json.svg
run --package url --repo "$URL" --version 2.5.2 --output out/url.svg
run --package regex --repo "$URL" --version 1.10.5 --output out/regex.svg
echo "## Зависимости для отдельных платформ и фильтр"
run --package tokio --repo "$URL" --version 1.38.0 --output out/tokio.svg
run --package tokio --repo "$URL" --version 1.38.0 --filter backtrace --output out/tokio_filter.svg
echo "## Тестовый репозиторий: ромб, циклы (красные рёбра), фильтр"
run --mode test --repo $G/diamond.txt --package A --output out/diamond.svg
run --mode test --repo $G/cycles.txt --package A --output out/cycles.svg
run --mode test --repo $G/partial_cycle.txt --package A --output out/partial_cycle.svg
run --mode test --repo $G/filter.txt --package APP --filter TEST --output out/filter.svg
