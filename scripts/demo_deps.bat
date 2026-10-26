@echo off
chcp 65001 >nul
rem Этап 2: вывод прямых зависимостей пакета заданной версии.
cd /d "%~dp0.."
set URL=https://index.crates.io
echo ## Последняя версия пакета
call :run --package serde --repo %URL%
echo ## Заданная версия: виды зависимостей, платформы, необязательные
call :run --package tokio --repo %URL% --version 1.38.0
echo ## Переименованная зависимость (поле package в индексе)
call :run --package wasm-bindgen --repo %URL% --version 0.2.129
echo ## Короткие имена пакетов (каталоги 2/ и 3/ в индексе)
call :run --package cc --repo %URL% --version 1.0.83
call :run --package log --repo %URL% --version 0.4.22
echo ## Версия без зависимостей
call :run --package fnv --repo %URL% --version 1.0.7
echo ## Тестовый репозиторий
call :run --package A --repo examples\test_repo.txt --mode test
call :run --package D --repo examples\test_repo.txt --mode test
exit /b 0

:run
echo $ run.bat %*
call run.bat %*
echo [код завершения: %errorlevel%]
echo.
exit /b 0
