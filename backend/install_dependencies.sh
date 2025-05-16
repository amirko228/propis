#!/bin/bash

echo "Установка зависимостей для генератора прописей..."

python3 -m pip install --upgrade pip

echo "Установка Pillow из готовых сборок (wheel)..."
pip install --only-binary=pillow pillow

echo "Установка остальных зависимостей..."
pip install -r requirements.txt --no-deps

echo ""
echo "Установка завершена!"
echo "" 