#!/bin/sh
# Этап 3: граф зависимостей пакетов crates.io (обход в ширину).
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
echo "## Последняя версия: зависимость cfg(any()) не учитывается"
run --package serde --repo "$URL"
echo "## Транзитивные зависимости"
run --package serde_json --repo "$URL" --version 1.0.120
echo "## Общая зависимость (ромб): percent-encoding нужен url и form_urlencoded"
run --package url --repo "$URL" --version 2.5.2
echo "## Зависимости для отдельных платформ"
run --package tokio --repo "$URL" --version 1.38.0
echo "## Фильтр: backtrace и всё, что нужно только ему, не учитываются"
run --package tokio --repo "$URL" --version 1.38.0 --filter backtrace
