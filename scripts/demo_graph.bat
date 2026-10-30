@echo off
chcp 65001 >nul
rem Этап 3: граф зависимостей пакетов crates.io (обход в ширину).
cd /d "%~dp0.."
set URL=https://index.crates.io
set G=examples\graphs
echo ## Последняя версия: зависимость cfg(any()) не учитывается
call :run --package serde --repo %URL%
echo ## Транзитивные зависимости
call :run --package serde_json --repo %URL% --version 1.0.120
echo ## Общая зависимость (ромб): percent-encoding нужен url и form_urlencoded
call :run --package url --repo %URL% --version 2.5.2
echo ## Зависимости для отдельных платформ
call :run --package tokio --repo %URL% --version 1.38.0
echo ## Фильтр: backtrace и всё, что нужно только ему, не учитываются
call :run --package tokio --repo %URL% --version 1.38.0 --filter backtrace
exit /b 0

:run
echo $ run.bat %*
call run.bat %*
echo [код завершения: %errorlevel%]
echo.
exit /b 0
