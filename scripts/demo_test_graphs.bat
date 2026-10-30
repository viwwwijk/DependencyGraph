@echo off
chcp 65001 >nul
rem Этап 3: граф зависимостей на различных случаях тестового репозитория.
cd /d "%~dp0.."
set URL=https://index.crates.io
set G=examples\graphs
echo ## Порядок обхода в ширину, недостижимый пакет X не попадает в граф
call :run --mode test --repo %G%\bfs_order.txt --package A
echo ## Ромб: общая зависимость обрабатывается один раз
call :run --mode test --repo %G%\diamond.txt --package A
echo ## Циклические зависимости и петля
call :run --mode test --repo %G%\cycles.txt --package A
call :run --mode test --repo %G%\cycles.txt --package D
call :run --mode test --repo %G%\cycles.txt --package F
echo ## Фильтр по подстроке
call :run --mode test --repo %G%\filter.txt --package APP
call :run --mode test --repo %G%\filter.txt --package APP --filter TEST
echo ## Фильтр разрывает цикл A -^> B -^> C -^> A
call :run --mode test --repo %G%\cycles.txt --package A --filter C
echo ## Неописанная зависимость: ошибка, если её не исключил фильтр
call :run --mode test --repo %G%\missing.txt --package A
call :run --mode test --repo %G%\missing.txt --package A --filter C
echo ## Фильтр исключает сам анализируемый пакет
call :run --mode test --repo %G%\filter.txt --package APP --filter AP
exit /b 0

:run
echo $ run.bat %*
call run.bat %*
echo [код завершения: %errorlevel%]
echo.
exit /b 0
