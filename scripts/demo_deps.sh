#!/bin/sh
# Этап 2: вывод прямых зависимостей пакета заданной версии.
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
echo "## Последняя версия пакета"
run --package serde --repo "$URL"
echo "## Заданная версия: виды зависимостей, платформы, необязательные"
run --package tokio --repo "$URL" --version 1.38.0
echo "## Переименованная зависимость (поле package в индексе)"
run --package wasm-bindgen --repo "$URL" --version 0.2.129
echo "## Короткие имена пакетов (каталоги 2/ и 3/ в индексе)"
run --package cc --repo "$URL" --version 1.0.83
run --package log --repo "$URL" --version 0.4.22
echo "## Версия без зависимостей"
run --package fnv --repo "$URL" --version 1.0.7
echo "## Тестовый репозиторий"
run --package A --repo examples/test_repo.txt --mode test
run --package D --repo examples/test_repo.txt --mode test
