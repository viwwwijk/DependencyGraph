@echo off
chcp 65001 >nul
rem Этап 2: ошибки получения данных о зависимостях (код завершения 1).
cd /d "%~dp0.."
set URL=https://index.crates.io
echo ## Пакета нет в репозитории
call :run --package nosuchcrate-xyz-123 --repo %URL%
echo ## Версии нет у пакета
call :run --package serde --repo %URL% --version 0.0.1
echo ## По URL нет индекса Cargo
call :run --package serde --repo https://crates.io
echo ## Сервер недоступен
call :run --package serde --repo https://localhost:9
echo ## Пакет не описан в тестовом репозитории
call :run --package Z --repo examples\test_repo.txt --mode test
echo ## Ошибка в файле тестового репозитория
call :run --package A --repo examples\broken_test_repo.txt --mode test
echo ## Предупреждение: версия в тестовом режиме не используется
call :run --package A --repo examples\test_repo.txt --mode test --version 1.0.0
exit /b 0

:run
echo $ run.bat %*
call run.bat %*
echo [код завершения: %errorlevel%]
echo.
exit /b 0
