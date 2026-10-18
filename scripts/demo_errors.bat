@echo off
chcp 65001 >nul
rem Этап 1: обработка ошибок для каждого параметра командной строки.
cd /d "%~dp0.."
set URL=https://index.crates.io
echo ## Обязательные параметры и ошибки разбора
call :run
call :run --package serde
call :run --package --repo %URL%
call :run --package serde --repo %URL% --unknown 1
echo ## --package
call :run --package "" --repo %URL%
call :run --package 1serde --repo %URL%
call :run --package "serde json" --repo %URL%
call :run --package serde --repo examples\test_repo.txt --mode test
echo ## --repo
call :run --package serde --repo ""
call :run --package serde --repo ftp://index.crates.io
call :run --package serde --repo https://
call :run --package A --repo examples\missing.txt --mode test
call :run --package A --repo examples --mode test
echo ## --mode
call :run --package serde --repo %URL% --mode local
echo ## --version
call :run --package serde --repo %URL% --version 1.0
call :run --package serde --repo %URL% --version v1.0.0
echo ## --output
call :run --package serde --repo %URL% --output graph.png
call :run --package serde --repo %URL% --output missing\graph.svg
echo ## --filter
call :run --package serde --repo %URL% --filter ""
call :run --package serde --repo %URL% --filter "a b"
echo ## Несколько ошибок сразу
call :run --package 1bad --repo ftp://x --version 1.0 --output g.png --filter "*"
exit /b 0

:run
echo $ run.bat %*
call run.bat %*
echo [код завершения: %errorlevel%]
echo.
exit /b 0
