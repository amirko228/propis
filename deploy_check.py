#!/usr/bin/env python3
"""
Скрипт для проверки готовности проекта к деплою на Vercel

Проверяет:
1. Наличие необходимых файлов
2. Корректность форматов переноса строк
3. Валидацию JSON-файлов
4. Структуру проекта
"""

import os
import sys
import json
import re
from pathlib import Path

# Цвета для вывода в консоль
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Директории, которые нужно игнорировать при проверке
IGNORED_DIRS = ['.git', '__pycache__', 'venv', 'env', 'node_modules', '.venv', 'dist', 'build']

def print_status(message, status, details=None):
    """Выводит статус проверки с цветом и форматированием"""
    status_str = f"{GREEN}OK{RESET}" if status else f"{RED}ОШИБКА{RESET}"
    print(f"  {status_str} | {message}")
    
    if details and not status:
        if isinstance(details, list):
            for detail in details:
                print(f"       - {detail}")
        else:
            print(f"       - {details}")
    
    return status

def check_file_exists(filepath):
    """Проверяет наличие файла"""
    path = Path(filepath)
    return path.exists()

def validate_json(filepath):
    """Проверяет валидность JSON-файла"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        return True, None
    except json.JSONDecodeError as e:
        return False, f"Невалидный JSON: {e}"
    except Exception as e:
        return False, f"Ошибка при чтении файла: {e}"

def check_line_endings(filepath):
    """Проверяет окончания строк в файле"""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Подсчитываем количество разных окончаний строк
        crlf_count = content.count(b'\r\n')
        lf_count = content.count(b'\n') - crlf_count
        cr_count = content.count(b'\r') - crlf_count
        
        # Если файл имеет смешанные окончания строк, это проблема
        if sum(1 for count in [crlf_count, lf_count, cr_count] if count > 0) > 1:
            return False, f"Смешанные окончания строк: CRLF={crlf_count}, LF={lf_count}, CR={cr_count}"
        
        # В Unix-подобных системах предпочтительнее LF
        if os.name != 'nt' and crlf_count > 0:
            return True, "Файл использует CRLF (Windows) окончания строк"
            
        return True, None
    except Exception as e:
        return False, f"Ошибка при проверке окончаний строк: {e}"

def should_ignore_path(path):
    """Проверяет, нужно ли игнорировать данный путь"""
    path_parts = Path(path).parts
    return any(ignored_dir in path_parts for ignored_dir in IGNORED_DIRS)

def check_required_files():
    """Проверяет наличие всех необходимых файлов для деплоя на Vercel"""
    required_files = [
        "main.py",            # Основной файл FastAPI
        "requirements.txt",   # Зависимости Python
        "vercel.json",        # Конфигурация Vercel
        ".gitattributes",     # Настройки Git для окончаний строк
        "static/pdf-generator.html", # Основной HTML файл
    ]
    
    print(f"\n{BLUE}Проверка наличия необходимых файлов:{RESET}")
    
    all_files_present = True
    missing_files = []
    
    for filepath in required_files:
        exists = check_file_exists(filepath)
        if not exists:
            all_files_present = False
            missing_files.append(filepath)
    
    print_status("Все необходимые файлы присутствуют", all_files_present, missing_files)
    
    return all_files_present

def check_json_files():
    """Проверяет валидность JSON файлов"""
    json_files = [
        "vercel.json",
    ]
    
    print(f"\n{BLUE}Проверка валидности JSON файлов:{RESET}")
    
    all_valid = True
    invalid_files = []
    
    for filepath in json_files:
        if check_file_exists(filepath):
            valid, error = validate_json(filepath)
            if not valid:
                all_valid = False
                invalid_files.append(f"{filepath}: {error}")
        else:
            all_valid = False
            invalid_files.append(f"{filepath}: файл не найден")
    
    print_status("Все JSON файлы валидны", all_valid, invalid_files)
    
    return all_valid

def check_line_ending_consistency():
    """Проверяет согласованность окончаний строк в файлах"""
    extensions = ['.py', '.html', '.json', '.md', '.txt']
    
    print(f"\n{BLUE}Проверка согласованности окончаний строк:{RESET}")
    
    all_consistent = True
    inconsistent_files = []
    
    # Проходимся по всем файлам проекта
    for root, _, files in os.walk('.'):
        if should_ignore_path(root):
            continue
            
        for filename in files:
            if any(filename.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, filename)
                
                # Пропускаем файлы в игнорируемых директориях
                if should_ignore_path(filepath):
                    continue
                    
                consistent, error = check_line_endings(filepath)
                if not consistent:
                    all_consistent = False
                    inconsistent_files.append(f"{filepath}: {error}")
    
    print_status("Все файлы имеют согласованные окончания строк", all_consistent, inconsistent_files)
    
    return all_consistent

def check_structure():
    """Проверяет структуру проекта"""
    print(f"\n{BLUE}Проверка структуры проекта:{RESET}")
    
    # Проверяем наличие директории static
    static_exists = os.path.isdir("static")
    print_status("Директория static существует", static_exists)
    
    # Проверяем, что main.py корректно импортирует FastAPI
    import_ok = False
    if check_file_exists("main.py"):
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
            import_ok = "from fastapi import" in content
    
    print_status("main.py корректно импортирует FastAPI", import_ok)
    
    # Проверяем конфигурацию vercel.json
    vercel_config_ok = False
    if check_file_exists("vercel.json"):
        valid, _ = validate_json("vercel.json")
        if valid:
            with open("vercel.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                vercel_config_ok = "builds" in config and "routes" in config
    
    print_status("vercel.json содержит корректные настройки builds и routes", vercel_config_ok)
    
    return static_exists and import_ok and vercel_config_ok

def main():
    """Основная функция проверки"""
    print(f"{YELLOW}=== Проверка готовности к деплою на Vercel ==={RESET}")
    
    files_ok = check_required_files()
    json_ok = check_json_files()
    line_endings_ok = check_line_ending_consistency()
    structure_ok = check_structure()
    
    print(f"\n{YELLOW}=== Результаты проверки ==={RESET}")
    all_ok = files_ok and json_ok and line_endings_ok and structure_ok
    
    if all_ok:
        print(f"\n{GREEN}✓ Проект готов к деплою на Vercel!{RESET}")
        print(f"{BLUE}Для деплоя выполните:{RESET} vercel")
        return 0
    else:
        print(f"\n{RED}✗ Обнаружены проблемы, которые могут помешать успешному деплою.{RESET}")
        print(f"{BLUE}Пожалуйста, исправьте указанные выше ошибки и запустите проверку снова.{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 