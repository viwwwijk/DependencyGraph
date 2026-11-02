@echo off
chcp 65001 >nul
rem Этап 4: порядок загрузки зависимостей на разных случаях.
cd /d "%~dp0.."
set URL=https://index.crates.io
set G=examples\graphs
set PYTHONPATH=src
echo ## Слои: сначала пакеты без зависимостей, корень последним
call :run --mode test --repo %G%\layers.txt --package A --load-order
echo ## Ромб: общая зависимость загружается один раз
call :run --mode test --repo %G%\diamond.txt --package A --load-order
echo ## Несколько уровней, недостижимый пакет X не загружается
call :run --mode test --repo %G%\bfs_order.txt --package A --load-order
echo ## Фильтр: исключённые пакеты не загружаются
call :run --mode test --repo %G%\filter.txt --package APP --load-order
call :run --mode test --repo %G%\filter.txt --package APP --load-order --filter TEST
echo ## Частичный цикл: загружается всё, что не зависит от цикла
call :run --mode test --repo %G%\partial_cycle.txt --package A --load-order
echo ## Фильтр, исключивший пакет цикла, делает загрузку возможной
call :run --mode test --repo %G%\partial_cycle.txt --package A --load-order --filter E
echo ## Всё упирается в циклы: загрузить нельзя ничего
call :run --mode test --repo %G%\cycles.txt --package A --load-order
echo ## Реальные пакеты crates.io
call :run --package serde_json --repo %URL% --version 1.0.120 --load-order
call :run --package url --repo %URL% --version 2.5.2 --load-order
exit /b 0

:run
echo $ run.bat %*
call run.bat %*
echo [код завершения: %errorlevel%]
echo.
exit /b 0
