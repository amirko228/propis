#!/bin/bash

echo "Генератор прописей по методике В. Илюхиной"
echo "==============================================="

install_backend_deps() {
    echo "Установка зависимостей бэкенда..."
    cd backend || exit 1
    chmod +x install_dependencies.sh
    ./install_dependencies.sh
    local result=$?
    if [ $result -ne 0 ]; then
        echo "Ошибка установки зависимостей бэкенда!"
        echo "Проверьте версию Python (рекомендуется 3.10+) и повторите попытку."
        cd ..
        return 1
    fi
    cd ..
    return 0
}

if [ "$1" = "dev" ]; then
    echo "Запуск в режиме разработки..."
    cd "$(dirname "$0")"
    
    # Устанавливаем зависимости бэкенда
    install_backend_deps
    if [ $? -ne 0 ]; then
        read -p "Нажмите Enter для выхода..."
        exit 1
    fi
    
    echo "Запуск серверов..."
    # Пытаемся запустить терминалы для разных сред
    gnome-terminal -- bash -c "cd backend && python run.py; bash" || \
    xterm -e "cd backend && python run.py; bash" || \
    open -a Terminal.app "$(pwd)/backend" -e "python run.py" || \
    konsole --workdir "$(pwd)/backend" -e "python run.py" || \
    terminator -e "cd $(pwd)/backend && python run.py" || \
    echo "Не удалось запустить терминал для бэкенда. Запустите вручную: cd backend && python run.py"
    
    gnome-terminal -- bash -c "cd frontend && npm install && npm start; bash" || \
    xterm -e "cd frontend && npm install && npm start; bash" || \
    open -a Terminal.app "$(pwd)/frontend" -e "npm install && npm start" || \
    konsole --workdir "$(pwd)/frontend" -e "npm install && npm start" || \
    terminator -e "cd $(pwd)/frontend && npm install && npm start" || \
    echo "Не удалось запустить терминал для фронтенда. Запустите вручную: cd frontend && npm install && npm start"
    
    echo "Приложение запущено в режиме разработки!"
    echo "Бэкенд: http://localhost:8000"
    echo "Фронтенд: http://localhost:3000"
elif [ "$1" = "docker" ]; then
    echo "Запуск через Docker..."
    docker-compose up
else
    echo "Запуск приложения..."
    cd "$(dirname "$0")"
    
    echo "Установка зависимостей npm..."
    npm install
    if [ $? -ne 0 ]; then
        echo "Ошибка установки зависимостей через npm!"
        echo "Убедитесь, что Node.js и npm установлены правильно."
        read -p "Нажмите Enter для выхода..."
        exit 1
    fi
    
    # Устанавливаем зависимости бэкенда
    install_backend_deps
    if [ $? -ne 0 ]; then
        read -p "Нажмите Enter для выхода..."
        exit 1
    fi
    
    echo "Запуск приложения..."
    npm start
    echo "Приложение запущено!"
    echo "Адрес: http://localhost:3000"
fi

echo "===============================================" 