@echo off
chcp 65001 >nul
rem Этап 4: сравнение порядка загрузки depviz с реальным Cargo (нужен Cargo).
cd /d "%~dp0.."
set URL=https://index.crates.io
set G=examples\graphs
set PYTHONPATH=src
echo ## Тестовые репозитории: локальные пакеты Cargo по графу
call :run test %G%\layers.txt A
call :run test %G%\diamond.txt A
call :run test %G%\bfs_order.txt A
call :run test %G%\filter.txt APP
call :run test %G%\partial_cycle.txt A
call :run test %G%\cycles.txt A
echo ## Пакеты crates.io
call :run remote serde 1.0.229
call :run remote serde_json 1.0.120
call :run remote url 2.5.2
call :run remote tokio 1.38.0
call :run remote regex 1.10.5
exit /b 0

:run
echo $ compare_with_cargo.py %*
python scripts\compare_with_cargo.py %*
echo.
exit /b 0
