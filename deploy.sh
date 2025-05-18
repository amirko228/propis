#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}===== Проверка и деплой приложения на Vercel =====${NC}"

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Ошибка: Python 3 не установлен. Пожалуйста, установите Python 3.9+${NC}"
    exit 1
fi

# Проверяем наличие Vercel CLI
if ! command -v vercel &> /dev/null; then
    echo -e "${YELLOW}Предупреждение: Vercel CLI не установлен.${NC}"
    echo "Установка Vercel CLI..."
    npm install -g vercel
    if [ $? -ne 0 ]; then
        echo -e "${RED}Ошибка: Не удалось установить Vercel CLI. Пожалуйста, установите его вручную: npm install -g vercel${NC}"
        exit 1
    fi
fi

# Делаем скрипт проверки исполняемым
chmod +x deploy_check.py

# Запускаем скрипт проверки готовности к деплою
echo "Проверка готовности проекта к деплою..."
python3 deploy_check.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Проверка не пройдена. Исправьте ошибки перед деплоем.${NC}"
    exit 1
fi

# Спрашиваем пользователя о продолжении
echo
echo -e "${YELLOW}Проект готов к деплою. Хотите продолжить? (y/n)${NC}"
read -r continue

if [[ ! $continue =~ ^[Yy]$ ]]; then
    echo "Деплой отменен."
    exit 0
fi

# Выполняем деплой
echo
echo "Выполняется деплой на Vercel..."
vercel --prod

if [ $? -ne 0 ]; then
    echo -e "${RED}Произошла ошибка при деплое.${NC}"
    exit 1
else
    echo -e "${GREEN}Приложение успешно задеплоено на Vercel!${NC}"
fi

echo
echo -e "${GREEN}Готово!${NC}" 