@echo off
echo Генератор прописей по методике В. Илюхиной
echo ===============================================

IF "%1"=="dev" (
    echo Запуск в режиме разработки...
    cd %~dp0
    
    echo Установка зависимостей бэкенда...
    cd backend
    call install_dependencies.bat
    if %ERRORLEVEL% NEQ 0 (
        echo Ошибка установки зависимостей бэкенда! 
        echo Проверьте версию Python (рекомендуется 3.10+) и повторите попытку.
        pause
        exit /b 1
    )
    cd ..
    
    echo Запуск серверов...
    start cmd /k "cd backend && python run.py"
    start cmd /k "cd frontend && npm install && npm start"
    
    echo Приложение запущено в режиме разработки!
    echo Бэкенд: http://localhost:8000
    echo Фронтенд: http://localhost:3000
) ELSE IF "%1"=="docker" (
    echo Запуск через Docker...
    docker-compose up
) ELSE (
    echo Запуск приложения...
    cd %~dp0
    
    echo Установка зависимостей...
    npm install
    if %ERRORLEVEL% NEQ 0 (
        echo Ошибка установки зависимостей через npm!
        echo Убедитесь, что Node.js и npm установлены правильно.
        pause
        exit /b 1
    )
    
    echo Установка зависимостей бэкенда...
    cd backend
    call install_dependencies.bat
    if %ERRORLEVEL% NEQ 0 (
        echo Ошибка установки зависимостей бэкенда! 
        echo Проверьте версию Python (рекомендуется 3.10+) и повторите попытку.
        pause
        exit /b 1
    )
    cd ..
    
    echo Запуск приложения...
    npm start
    echo Приложение запущено!
    echo Адрес: http://localhost:3000
)

echo =============================================== 