@echo off
chcp 65001 >nul
rem Этап 5: визуализация графа (текст на языке Graphviz и файл SVG).
cd /d "%~dp0.."
set URL=https://index.crates.io
set G=examples\graphs
if not exist out mkdir out
echo ## Три пакета crates.io: изображения в каталоге out/
call :run --package serde_json --repo %URL% --version 1.0.120 --output out\serde_json.svg
call :run --package url --repo %URL% --version 2.5.2 --output out\url.svg
call :run --package regex --repo %URL% --version 1.10.5 --output out\regex.svg
echo ## Зависимости для отдельных платформ и фильтр
call :run --package tokio --repo %URL% --version 1.38.0 --output out\tokio.svg
call :run --package tokio --repo %URL% --version 1.38.0 --filter backtrace --output out\tokio_filter.svg
echo ## Тестовый репозиторий: ромб, циклы (красные рёбра), фильтр
call :run --mode test --repo %G%\diamond.txt --package A --output out\diamond.svg
call :run --mode test --repo %G%\cycles.txt --package A --output out\cycles.svg
call :run --mode test --repo %G%\partial_cycle.txt --package A --output out\partial_cycle.svg
call :run --mode test --repo %G%\filter.txt --package APP --filter TEST --output out\filter.svg
exit /b 0

:run
echo $ run.bat %*
call run.bat %*
echo [код завершения: %errorlevel%]
echo.
exit /b 0
