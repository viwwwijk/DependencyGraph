#!/bin/sh
# Этап 1: успешные запуски с выводом параметров в формате ключ=значение.
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
run --package serde --repo https://index.crates.io
run --package tokio --repo https://index.crates.io --version 1.38.0 \
    --output tokio.svg --filter test
run --package A --repo examples/test_repo.txt --mode test --filter E
