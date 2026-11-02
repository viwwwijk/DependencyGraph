@echo off
chcp 65001 >nul
rem Этап 5: сравнение графа depviz с выводом cargo tree (нужен Cargo).
cd /d "%~dp0.."
set URL=https://index.crates.io
set G=examples\graphs
set PYTHONPATH=src
if not exist out mkdir out
call :run serde_json 1.0.120 out
call :run url 2.5.2 out
call :run regex 1.10.5 out
call :run tokio 1.38.0 out
exit /b 0

:run
echo $ compare_with_cargo_tree.py %*
python scripts\compare_with_cargo_tree.py %*
echo.
exit /b 0
