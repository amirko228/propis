@echo off
echo Установка зависимостей для генератора прописей...

python -m pip install --upgrade pip

echo Установка Pillow из готовых сборок (wheel)...
pip install --only-binary=pillow pillow

echo Установка остальных зависимостей...
pip install -r requirements.txt --no-deps

echo.
echo Установка завершена!
echo. 