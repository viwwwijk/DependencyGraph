#!/bin/sh
# Этап 1: обработка ошибок для каждого параметра командной строки.
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
echo "## Обязательные параметры и ошибки разбора"
run
run --package serde
run --package --repo "$URL"
run --package serde --repo "$URL" --unknown 1
echo "## --package"
run --package "" --repo "$URL"
run --package 1serde --repo "$URL"
run --package "serde json" --repo "$URL"
run --package serde --repo examples/test_repo.txt --mode test
echo "## --repo"
run --package serde --repo ""
run --package serde --repo ftp://index.crates.io
run --package serde --repo https://
run --package A --repo examples/missing.txt --mode test
run --package A --repo examples --mode test
echo "## --mode"
run --package serde --repo "$URL" --mode local
echo "## --version"
run --package serde --repo "$URL" --version 1.0
run --package serde --repo "$URL" --version v1.0.0
echo "## --output"
run --package serde --repo "$URL" --output graph.png
run --package serde --repo "$URL" --output missing/graph.svg
echo "## --filter"
run --package serde --repo "$URL" --filter ""
run --package serde --repo "$URL" --filter "a b"
echo "## Несколько ошибок сразу"
run --package 1bad --repo ftp://x --version 1.0 --output g.png --filter "*"
