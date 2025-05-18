@echo off
echo ===== Проверка и деплой приложения на Vercel =====

REM Проверяем наличие Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [31mОшибка: Python не установлен. Пожалуйста, установите Python 3.9+[0m
    exit /b 1
)

REM Проверяем наличие Vercel CLI
vercel --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [33mПредупреждение: Vercel CLI не установлен.[0m
    echo Установка Vercel CLI...
    npm install -g vercel
    if %ERRORLEVEL% neq 0 (
        echo [31mОшибка: Не удалось установить Vercel CLI. Пожалуйста, установите его вручную: npm install -g vercel[0m
        exit /b 1
    )
)

REM Запускаем скрипт проверки готовности к деплою
echo Проверка готовности проекта к деплою...
python deploy_check.py
if %ERRORLEVEL% neq 0 (
    echo [31mПроверка не пройдена. Исправьте ошибки перед деплоем.[0m
    exit /b 1
)

REM Спрашиваем пользователя о продолжении
echo.
echo [33mПроект готов к деплою. Хотите продолжить? (y/n)[0m
set /p continue=

if /i "%continue%" neq "y" (
    echo Деплой отменен.
    exit /b 0
)

REM Выполняем деплой
echo.
echo Выполняется деплой на Vercel...
vercel --prod

if %ERRORLEVEL% neq 0 (
    echo [31mПроизошла ошибка при деплое.[0m
    exit /b 1
) else (
    echo [32mПриложение успешно задеплоено на Vercel![0m
)

echo.
echo [32mГотово![0m 