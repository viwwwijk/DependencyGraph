@echo off
chcp 65001 >nul
rem Этап 1: успешные запуски с выводом параметров в формате ключ=значение.
cd /d "%~dp0.."
set URL=https://index.crates.io
call :run --package serde --repo https://index.crates.io
call :run --package tokio --repo https://index.crates.io --version 1.38.0 --output tokio.svg --filter test
call :run --package A --repo examples\test_repo.txt --mode test --filter E
exit /b 0

:run
echo $ run.bat %*
call run.bat %*
echo [код завершения: %errorlevel%]
echo.
exit /b 0
