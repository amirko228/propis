from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging
import uuid
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import traceback
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import gray, black

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pdf-generator")

app = FastAPI(title="PDF Generator API")

# Добавляем CORS middleware для обработки запросов с фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любых доменов (в продакшене лучше указать конкретные домены)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Определяем базовый путь
BASE_DIR = Path(__file__).resolve().parent

# Монтируем статические файлы
try:
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    logger.info(f"Статические файлы подключены из директории: {BASE_DIR / 'static'}")
except Exception as e:
    logger.error(f"Ошибка при монтировании статических файлов: {e}")

# Папка для временных файлов
# На Vercel функции ограничены доступом на запись, создадим директорию в /tmp
if os.environ.get("VERCEL"):
    TEMP_DIR = Path("/tmp") / "pdf_generator"
else:
    TEMP_DIR = Path(tempfile.gettempdir()) / "pdf_generator"

if not TEMP_DIR.exists():
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Создана временная директория: {TEMP_DIR}")

def cleanup_temp_files(filepath: Path):
    """Удаляет временные файлы после отправки ответа клиенту"""
    if filepath.exists():
        try:
            filepath.unlink()
            logger.info(f"Временный файл удален: {filepath}")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла {filepath}: {e}")

def generate_pdf_file(data: Dict[Any, Any], output_path: Path) -> bool:
    """Генерирует PDF файл на основе данных запроса
    
    Args:
        data: Данные для генерации PDF
        output_path: Путь для сохранения файла
        
    Returns:
        bool: True если генерация прошла успешно
    """
    try:
        # Получаем параметры из запроса
        fill_type = data.get("fill_type", "first_letter")
        text = data.get("text", "")
        page_layout = data.get("page_layout", "lines")
        font_type = data.get("font_type", "black")
        page_orientation = data.get("page_orientation", "portrait")
        student_name = data.get("student_name", "")
        
        # Выбираем ориентацию страницы
        pagesize = landscape(A4) if page_orientation == "landscape" else A4
        width, height = pagesize
        
        # Создаем PDF с использованием reportlab
        pdf = canvas.Canvas(str(output_path), pagesize=pagesize)
        
        # Устанавливаем шрифт (используем стандартный)
        pdf.setFont("Helvetica", 16)
        
        # Добавляем заголовок
        pdf.drawString(50, height - 50, "Пропись для практики письма")
        
        # Если есть имя ученика, добавляем его
        if student_name:
            pdf.setFont("Helvetica", 12)
            pdf.drawString(50, height - 80, f"Ученик: {student_name}")
        
        # Добавляем текст в зависимости от типа заполнения
        lines = text.split('\n')
        line_height = 30
        start_y = height - 120
        
        # Устанавливаем цвет в зависимости от выбранного типа
        if font_type == "gray":
            pdf.setFillColor(gray)
        else:
            pdf.setFillColor(black)
            
        # Ограничиваем количество строк
        max_lines = 20
        
        # Подготавливаем текст в зависимости от варианта заполнения
        if fill_type == "one_line" and lines and lines[0].strip():
            # Размножаем первую строку
            first_line = lines[0].strip()
            for i in range(max_lines):
                y_pos = start_y - i * line_height
                if y_pos > 50:  # Оставляем отступ снизу
                    pdf.drawString(50, y_pos, first_line)
        elif fill_type == "first_letter":
            # Размножаем первую букву каждой строки
            for i, line in enumerate(lines[:max_lines]):
                if not line.strip():
                    continue
                    
                first_char = line[0] if line else ""
                if first_char:
                    y_pos = start_y - i * line_height
                    if y_pos > 50:
                        # Повторяем первую букву несколько раз
                        repeated_text = first_char * 30
                        pdf.drawString(50, y_pos, repeated_text)
        else:
            # Выводим текст как есть
            for i, line in enumerate(lines[:max_lines]):
                if not line.strip():
                    continue
                    
                y_pos = start_y - i * line_height
                if y_pos > 50:
                    pdf.drawString(50, y_pos, line)
        
        # Сохраняем PDF
        pdf.save()
        logger.info(f"PDF успешно сгенерирован: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}")
        logger.error(traceback.format_exc())
        return False

@app.get("/")
async def read_root():
    """Корневой эндпоинт, перенаправляет на статическую страницу"""
    return FileResponse(BASE_DIR / "static" / "pdf-generator.html")

@app.post("/generate-pdf")
async def generate_pdf(request: Request, background_tasks: BackgroundTasks):
    """Эндпоинт для генерации PDF файла
    
    Принимает данные о прописях и возвращает PDF файл.
    """
    try:
        # Создаем уникальное имя файла
        filename = f"propisi_{uuid.uuid4()}.pdf"
        output_path = TEMP_DIR / filename
        
        # Получаем данные из запроса
        try:
            data = await request.json()
            logger.info(f"Получен запрос на генерацию PDF: {data}")
        except Exception as e:
            logger.error(f"Ошибка при чтении данных запроса: {e}")
            return JSONResponse(
                status_code=400,
                content={"error": "Некорректный формат данных"}
            )
        
        # Генерируем PDF
        success = generate_pdf_file(data, output_path)
        
        if not success:
            return JSONResponse(
                status_code=500,
                content={"error": "Ошибка при генерации PDF"}
            )
        
        # Проверяем, что файл был создан
        if not output_path.exists():
            logger.error(f"Файл не был создан: {output_path}")
            return JSONResponse(
                status_code=500, 
                content={"error": "Файл PDF не был создан"}
            )
        
        # Планируем удаление временного файла после отправки ответа
        background_tasks.add_task(cleanup_temp_files, output_path)
        
        # Отправляем файл клиенту
        return FileResponse(
            path=str(output_path),
            media_type="application/pdf",
            filename="propisi.pdf"
        )
        
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Внутренняя ошибка сервера: {str(e)}"}
        )

@app.get("/health")
def health_check():
    """Эндпоинт для проверки работоспособности API"""
    return {"status": "OK"}

# Для локального запуска
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 