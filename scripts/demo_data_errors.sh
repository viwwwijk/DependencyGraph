#!/bin/sh
# Этап 2: ошибки получения данных о зависимостях (код завершения 1).
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
echo "## Пакета нет в репозитории"
run --package nosuchcrate-xyz-123 --repo "$URL"
echo "## Версии нет у пакета"
run --package serde --repo "$URL" --version 0.0.1
echo "## По URL нет индекса Cargo"
run --package serde --repo https://crates.io
echo "## Сервер недоступен"
run --package serde --repo https://localhost:9
echo "## Пакет не описан в тестовом репозитории"
run --package Z --repo examples/test_repo.txt --mode test
echo "## Ошибка в файле тестового репозитория"
run --package A --repo examples/broken_test_repo.txt --mode test
echo "## Предупреждение: версия в тестовом режиме не используется"
run --package A --repo examples/test_repo.txt --mode test --version 1.0.0
