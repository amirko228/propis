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
    Обходное решение - возвращаем HTML вместо PDF для Vercel.
    """
    try:
        # Создаем простой HTML-шаблон для отображения текста
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Генератор прописей - {task}</title>
            <meta charset="utf-8">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 30px; 
                    line-height: 1.6;
                }}
                .container {{ 
                    border: 1px solid #ddd; 
                    padding: 20px; 
                    margin-bottom: 20px; 
                    background-color: #f9f9f9;
                }}
                .title {{ 
                    font-size: 24px; 
                    margin-bottom: 20px; 
                    color: #333;
                }}
                .text {{ 
                    white-space: pre-line; 
                    font-size: 16px; 
                    margin-bottom: 30px;
                }}
                .info {{ 
                    font-size: 12px; 
                    color: #777; 
                    margin-top: 30px;
                }}
                .red-line {{
                    border-right: 2px solid red;
                    padding-right: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container red-line">
                <h1 class="title">{task}</h1>
                <div class="text">{text}</div>
                <div class="info">
                    <p>Тип заполнения: {fill_type}</p>
                    <p>Тип разметки: {page_layout}</p>
                    <p>Тип шрифта: {font_type}</p>
                    <p>Ориентация: {page_orientation}</p>
                    {f"<p>Имя ученика: {student_name}</p>" if student_name else ""}
                </div>
            </div>
        </body>
        </html>
        """
        
        # Возвращаем HTML-страницу
        return Response(content=html_content, media_type="text/html")
    
    except Exception as e:
        # Максимально подробно логируем ошибку
        import traceback
        error_trace = traceback.format_exc()
        print(f"ОШИБКА В GENERATE_PDF: {str(e)}")
        print(error_trace)
        
        # Возвращаем ошибку в формате HTML
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ошибка генерации</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 30px; }}
                .error {{ color: red; font-weight: bold; }}
                .details {{ margin-top: 20px; padding: 10px; background-color: #f8f8f8; border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <h1 class="error">Произошла ошибка при генерации страницы</h1>
            <p>Пожалуйста, попробуйте снова или обратитесь к администратору</p>
            <div class="details">
                <h3>Детали ошибки (для разработчика):</h3>
                <p>{str(e)}</p>
            </div>
        </body>
        </html>
        """
        return Response(content=error_html, media_type="text/html", status_code=500)

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
    Обходное решение - возвращаем HTML вместо PDF для предпросмотра на Vercel.
    """
    try:
        # Ограничиваем текст только первыми тремя строками
        preview_lines = text.split('\n')[:3]
        preview_text = '\n'.join(preview_lines)
        
        # Создаем простой HTML-шаблон для предпросмотра
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Предпросмотр - {task}</title>
            <meta charset="utf-8">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 30px; 
                    line-height: 1.6;
                }}
                .container {{ 
                    border: 1px solid #ddd; 
                    padding: 20px; 
                    margin-bottom: 20px; 
                    background-color: #f9f9f9;
                }}
                .title {{ 
                    font-size: 24px; 
                    margin-bottom: 20px; 
                    color: #333;
                }}
                .text {{ 
                    white-space: pre-line; 
                    font-size: 16px; 
                    margin-bottom: 30px;
                }}
                .info {{ 
                    font-size: 12px; 
                    color: #777; 
                    margin-top: 30px;
                }}
                .preview-notice {{
                    background-color: #fff3cd;
                    padding: 10px;
                    border: 1px solid #ffeeba;
                    color: #856404;
                    margin-top: 20px;
                }}
                .red-line {{
                    border-right: 2px solid red;
                    padding-right: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container red-line">
                <h1 class="title">Предпросмотр: {task}</h1>
                <div class="text">{preview_text}</div>
                <div class="preview-notice">
                    Это только предварительный просмотр. Полный документ может отличаться.
                </div>
                <div class="info">
                    <p>Тип заполнения: {fill_type}</p>
                    <p>Тип разметки: {page_layout}</p>
                    <p>Тип шрифта: {font_type}</p>
                    <p>Ориентация: {page_orientation}</p>
                    {f"<p>Имя ученика: {student_name}</p>" if student_name else ""}
                </div>
            </div>
        </body>
        </html>
        """
        
        # Возвращаем HTML-страницу вместо PDF
        return Response(content=html_content, media_type="text/html")
    
    except Exception as e:
        # Максимально подробно логируем ошибку
        import traceback
        error_trace = traceback.format_exc()
        print(f"ОШИБКА В PREVIEW: {str(e)}")
        print(error_trace)
        
        # Возвращаем ошибку в формате HTML
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ошибка предпросмотра</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 30px; }}
                .error {{ color: red; font-weight: bold; }}
                .details {{ margin-top: 20px; padding: 10px; background-color: #f8f8f8; border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <h1 class="error">Произошла ошибка при создании предпросмотра</h1>
            <p>Пожалуйста, попробуйте снова или обратитесь к администратору</p>
            <div class="details">
                <h3>Детали ошибки (для разработчика):</h3>
                <p>{str(e)}</p>
            </div>
        </body>
        </html>
        """
        return Response(content=error_html, media_type="text/html", status_code=500)

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