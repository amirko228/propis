from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Union, Annotated
import os
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, gray, red, Color, lightgrey, white
import tempfile
import shutil
import math
from reportlab.graphics.shapes import Path, String, Group
from reportlab.graphics import renderPDF
from reportlab.lib.units import mm
from reportlab.pdfbase._fontdata import standardFonts
from reportlab.pdfbase import _fontdata
import datetime

app = FastAPI(title="Генератор прописей")

# Настройка CORS - подробная конфигурация
origins = ["*"]  # В продакшене лучше указать конкретные домены
if "VERCEL_URL" in os.environ:
    origins.append(f"https://{os.environ['VERCEL_URL']}")
    origins.append(f"https://*.{os.environ['VERCEL_URL']}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    expose_headers=["Content-Disposition", "Content-Type"],
)

# Модель данных для запроса
class PropisiRequest(BaseModel):
    task: str
    fill_type: str  # "all", "first_letter", "one_line"
    text: str
    page_layout: str  # "cells", "lines", "lines_oblique"
    font_type: str  # "punktir", "gray", "black"
    page_orientation: str  # "portrait", "landscape"
    student_name: Optional[str] = None

# Создаем папку для временных файлов
# На Vercel используем /tmp директорию, которая доступна для serverless функций
if os.environ.get('VERCEL', False):
    temp_dir = "/tmp"
else:
    temp_dir = "temp"
os.makedirs(temp_dir, exist_ok=True)

# Регистрируем шрифты - отключаем пользовательские шрифты
FONT_LOADED = False
try:
    # Отключаем загрузку пользовательских шрифтов, используем только стандартные
    print("Используем только стандартные шрифты ReportLab")
    # Заглушка для совместимости
    FONT_LOADED = False
except Exception as e:
    print(f"Используем только стандартные шрифты: {e}")
    FONT_LOADED = False

# Определяем шрифт, который будет использоваться
print(f"Статус загрузки шрифта: {FONT_LOADED}")
# Отключаем загрузку пользовательских шрифтов, используем только стандартный Helvetica
FONT_LOADED = False
DEFAULT_FONT = "Helvetica"
print(f"Будет использован шрифт: {DEFAULT_FONT}")

# Функция для рисования школьной клетки с наклонными линиями
def draw_school_grid(c, x, y, cell_size, rows, cols):
    # Устанавливаем тонкие линии для сетки
    c.setLineWidth(0.3)
    c.setStrokeColor(Color(0.7, 0.7, 0.7))  # Светло-серый цвет для сетки
    c.setDash([])  # Сплошная линия для клеток
    
    # Рисуем горизонтальные линии
    for i in range(rows + 1):
        c.line(x, y - i * cell_size, x + cols * cell_size, y - i * cell_size)
    
    # Рисуем вертикальные линии
    for i in range(cols + 1):
        c.line(x + i * cell_size, y, x + i * cell_size, y - rows * cell_size)
    
    # Не рисуем диагональные линии для соответствия образцу
    # Диагональные линии только создают визуальный шум

# Функция для рисования линейки для прописей
def draw_propisi_lines(c, x, y, width, line_height, count, oblique=False):
    # Настройка для рисования линий
    c.setLineWidth(0.3)
    
    # Разные оттенки серого для линий прописи
    light_gray = Color(0.85, 0.85, 0.85)  # Верхняя и нижняя линии
    dark_gray = Color(0.6, 0.6, 0.6)      # Основная (средняя) линия
    slope_gray = Color(0.8, 0.8, 0.8)     # Наклонные линии
    
    # Размер промежутков между группами линий (убираем)
    line_gap = 0  # Полностью убираем отступы между группами линий
    group_height = line_height * 2  # Общая высота группы из трех линий
    
    # Рассчитываем общее количество групп линий для заполнения всего листа
    # Даже если count меньше, мы все равно будем заполнять весь лист
    page_height = y
    total_groups = int(page_height / (group_height + line_gap)) + 2  # +2 для запаса
    
    # Проходим по всем возможным строкам для заполнения всей страницы
    for i in range(total_groups):
        # Позиция для текущей группы линий (базовая линия в середине)
        base_y = y - i * (group_height + line_gap)
        
        # Пропускаем, если строка уже за пределами страницы
        if base_y - line_height < 0:
            continue
            
        # Рисуем основную (среднюю) линию - более темную
        c.setStrokeColor(dark_gray)
        c.line(x, base_y, x + width, base_y)
        
        # Рисуем верхнюю линию - более светлую
        c.setStrokeColor(light_gray)
        c.line(x, base_y + line_height, x + width, base_y + line_height)
        
        # Рисуем нижнюю линию - тоже светлую
        c.line(x, base_y - line_height, x + width, base_y - line_height)
    
    # Если выбрана косая линия
    if oblique:
        # Настройка для косых линий
        c.setStrokeColor(slope_gray)
        c.setLineWidth(0.25)

        # Используем другой подход для рисования косых линий
        # Угол наклона (фиксированный)
        angle = math.radians(-58)  # направление вправо-вниз
        
        # Шаг между линиями (меньше для более частых линий)
        step = 10  # пунктов
        
        # Подход: рисуем линии с равномерным шагом сверху и справа,
        # убедившись, что они достаточно длинные, чтобы пройти всю страницу
        
        # 1. Линии начинаются сверху страницы и идут вниз вправо
        # Используем увеличенную частоту и диапазон для гарантии покрытия всей страницы
        extra_distance = 500  # дополнительное расстояние для гарантии пересечения всей страницы
        
        # Рисуем линии начиная от левой стороны до правой вверху страницы
        for offset in range(-1000, int(width) + 1000, step):
            # Начальная точка (с отрицательным смещением для гарантии)
            start_x = offset
            start_y = y + extra_distance  # Начинаем выше верха страницы
            
            # Рассчитываем конечную точку, достаточно далеко, чтобы пересечь страницу
            end_y = -extra_distance  # Ниже низа страницы
            # Используем тригонометрию для расчета смещения по X
            delta_y = start_y - end_y
            delta_x = delta_y * math.tan(-angle)  # Отрицательный угол для наклона вправо
            end_x = start_x + delta_x
            
            # Рисуем линию
            if offset % 2 == 0:  # Рисуем через одну линию для оптимизации
                c.line(start_x, start_y, end_x, end_y)

@app.post("/api/generate-pdf")
async def generate_pdf(
    task: Annotated[str, Form()],
    fill_type: Annotated[str, Form()],
    text: Annotated[str, Form()],
    page_layout: Annotated[str, Form()],
    font_type: Annotated[str, Form()],
    page_orientation: Annotated[str, Form()],
    student_name: Annotated[Union[str, None], Form()] = None
):
    """
    Крайне упрощенная версия API для диагностики
    """
    try:
        # Создаем объект с данными, которые мы получили
        response_data = {
            "message": "Запрос успешно обработан",
            "task": task,
            "fill_type": fill_type,
            "text_sample": text[:50] + "..." if len(text) > 50 else text,
            "page_layout": page_layout,
            "font_type": font_type,
            "page_orientation": page_orientation,
            "student_name": student_name,
            "timestamp": str(datetime.datetime.now())
        }
        
        # Возвращаем простой JSON без попыток создания PDF
        return JSONResponse(content=response_data)
    except Exception as e:
        # Подробное логирование ошибки
        import traceback
        error_trace = traceback.format_exc()
        print(f"ОШИБКА В GENERATE_PDF: {str(e)}")
        print(error_trace)
        
        # Возвращаем ошибку в формате JSON
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "error_type": type(e).__name__,
                "message": "Произошла ошибка при обработке запроса"
            }
        )

@app.post("/api/preview")
async def generate_preview(
    task: Annotated[str, Form()],
    fill_type: Annotated[str, Form()],
    text: Annotated[str, Form()], 
    page_layout: Annotated[str, Form()],
    font_type: Annotated[str, Form()],
    page_orientation: Annotated[str, Form()],
    student_name: Annotated[Union[str, None], Form()] = None
):
    """
    Крайне упрощенная версия API для предпросмотра для диагностики
    """
    try:
        # Создаем объект с данными, которые мы получили
        response_data = {
            "message": "Запрос предпросмотра успешно обработан",
            "task": task,
            "fill_type": fill_type,
            "text_sample": text[:30] + "..." if len(text) > 30 else text,
            "page_layout": page_layout,
            "font_type": font_type,
            "page_orientation": page_orientation,
            "student_name": student_name,
            "timestamp": str(datetime.datetime.now())
        }
        
        # Возвращаем простой JSON без попыток создания PDF
        return JSONResponse(content=response_data)
    except Exception as e:
        # Подробное логирование ошибки
        import traceback
        error_trace = traceback.format_exc()
        print(f"ОШИБКА В PREVIEW: {str(e)}")
        print(error_trace)
        
        # Возвращаем ошибку в формате JSON
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "error_type": type(e).__name__,
                "message": "Произошла ошибка при обработке запроса предпросмотра"
            }
        )

@app.get("/api")
async def root():
    return {"message": "Генератор прописей API работает!"}

# Удаление временных файлов при выключении сервера
@app.on_event("shutdown")
def shutdown_event():
    # Не удаляем системную /tmp директорию
    if temp_dir != "/tmp":
        shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        # Удаляем только наши файлы в /tmp
        import glob
        for f in glob.glob(os.path.join(temp_dir, "propisi_*.pdf")):
            try:
                os.remove(f)
            except:
                pass
        for f in glob.glob(os.path.join(temp_dir, "preview_*.pdf")):
            try:
                os.remove(f)
            except:
                pass
        for f in glob.glob(os.path.join(temp_dir, "preview_*.png")):
            try:
                os.remove(f)
            except:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 