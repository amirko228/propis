@echo off
echo Проверка наличия Chocolatey...
where choco >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Chocolatey не установлен. Пожалуйста, установите Chocolatey с сайта https://chocolatey.org/install
    echo Или следуйте инструкциям в файле poppler_install_instructions.md
    goto :eof
)

echo Установка poppler через Chocolatey...
choco install poppler -y

echo.
echo Проверяем установку poppler...
where pdftoppm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Не удалось найти pdftoppm в PATH
    echo Пожалуйста, следуйте ручной инструкции в файле poppler_install_instructions.md
) else (
    echo Poppler успешно установлен!
    echo Путь к исполняемым файлам poppler:
    where pdftoppm
)

echo.
echo Установка зависимостей Python...
pip install -r requirements.txt

echo.
echo Установка завершена. Теперь можно запустить сервер с помощью: python run.py
echo. 