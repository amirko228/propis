from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, Response, JSONResponse, HTMLResponse
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

# Настройка CORS - максимально открытая для тестирования
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://propis.vercel.app", "http://localhost:3000", "http://localhost:8000"],  # Разрешаем все источники и конкретные домены
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Указываем конкретные методы
    allow_headers=["*", "Content-Type", "Authorization"],  # Разрешаем все заголовки и конкретные
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

# Настройка для статических файлов - разместите их в папке static в корне проекта
# Создаем папку, если её нет
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
os.makedirs(static_dir, exist_ok=True)

# Монтируем статические файлы через маршрут /static
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Маршрут для отдачи главной страницы из статических файлов
@app.get("/")
async def serve_static_index():
    """
    Маршрут для отдачи главной страницы из статических файлов
    """
    # Формируем путь к файлу index.html в папке static
    index_path = os.path.join(static_dir, "index.html")
    
    # Проверяем, существует ли файл
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        # Если файла нет, возвращаем простую страницу
        return HTMLResponse("""
        <html>
            <head>
                <title>Генератор прописей</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 40px;
                        line-height: 1.6;
                    }
                    h1 {
                        color: #333;
                    }
                </style>
            </head>
            <body>
                <h1>Генератор прописей</h1>
                <p>API сервера работает. Разместите файлы интерфейса в папке static.</p>
                <h2>Доступные API:</h2>
                <ul>
                    <li><a href="/api/test">/api/test</a> - Тестовый API для проверки работы</li>
                    <li>/api/preview - API для генерации предпросмотра</li>
                    <li>/api/generate-pdf - API для генерации PDF с прописями</li>
                </ul>
            </body>
        </html>
        """)

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

async def root():
    return {"message": "API работает"}

@app.get("/api")
async def api_root():
    return {"message": "API работает"}

@app.get("/api/test")
async def test_api():
    """
    Тестовый API маршрут для проверки соединения
    """
    return {"status": "success", "message": "API работает корректно!"}

@app.post("/api/simple-preview")
async def simple_preview():
    """
    Максимально упрощенный маршрут для предпросмотра
    """
    return {"status": "success", "message": "Предпросмотр успешно создан!"}

@app.post("/api/simple-generate")
async def simple_generate():
    """
    Максимально упрощенный маршрут для генерации
    """
    return {"status": "success", "message": "Пропись успешно сгенерирована!"}

@app.post("/api/preview")
async def generate_preview(request: Request):
    """
    API для создания предпросмотра прописи
    """
    try:
        # Получаем данные из запроса
        data = await request.json()
        
        # Получаем параметры или используем значения по умолчанию
        task = data.get("task", "practice")
        fill_type = data.get("fill_type", "first_letter")
        text = data.get("text", "")
        page_layout = data.get("page_layout", "lines")
        font_type = data.get("font_type", "gray")
        page_orientation = data.get("page_orientation", "portrait")
        student_name = data.get("student_name", "")
        
        # Создаем буфер в памяти вместо файла на диске
        buffer = io.BytesIO()
        
        # Определяем размер страницы
        if page_orientation == "landscape":
            pagesize = landscape(A4)
        else:
            pagesize = A4
        
        # Создаем PDF в буфере
        c = canvas.Canvas(buffer, pagesize=pagesize)
        width, height = pagesize
        
        # Настраиваем основной шрифт
        c.setFont(DEFAULT_FONT, 12)
        
        # Добавляем метку предпросмотра
        c.setFont(DEFAULT_FONT, 10)
        c.setFillColor(red)
        c.drawString(width - 150, height - 20, "ПРЕДПРОСМОТР")
        c.setFillColor(black)
        
        # Добавляем заголовок
        c.setFont(DEFAULT_FONT, 14)
        title = "Пропись для практики письма"
        c.drawString(30, height - 40, title)
        
        # Определяем отступы
        margin_left = 30
        margin_top = 80
        content_width = width - 2 * margin_left
        content_height = height - margin_top - 30
        
        # Рисуем разметку на странице в зависимости от выбранного типа
        # Для предпросмотра рисуем только первую часть страницы
        preview_height = min(300, content_height)  # Ограничиваем высоту для предпросмотра
        
        if page_layout == "cells":
            # Рисуем клетки
            cell_size = 15  # размер клетки в пунктах
            rows = int(preview_height / cell_size)
            cols = int(content_width / cell_size)
            draw_school_grid(c, margin_left, height - margin_top, cell_size, rows, cols)
        elif page_layout == "lines_oblique":
            # Рисуем линии с наклонными линиями
            line_height = 12  # высота строки
            draw_propisi_lines(c, margin_left, height - margin_top, content_width, line_height, 10, True)
        else:  # "lines"
            # Рисуем обычные линии
            line_height = 12  # высота строки
            draw_propisi_lines(c, margin_left, height - margin_top, content_width, line_height, 10, False)
        
        # Добавляем текст прописи, если он есть
        if text:
            # Разбиваем текст на строки
            lines = text.split('\n')
            
            # Ограничиваем количество строк для предпросмотра
            preview_lines = lines[:5]  # Только первые 5 строк для предпросмотра
            
            # Определяем параметры для текста
            c.setFont(DEFAULT_FONT, 12)
            y_position = height - margin_top - line_height
            
            # Стиль шрифта в зависимости от выбранного типа
            if font_type == "punktir":
                c.setFillColor(Color(0.7, 0.7, 0.7))  # Светло-серый для пунктира
            elif font_type == "gray":
                c.setFillColor(Color(0.5, 0.5, 0.5))  # Серый
            else:  # "black"
                c.setFillColor(black)
            
            # Выводим текст в зависимости от способа заполнения
            for i, line in enumerate(preview_lines):
                if not line.strip():  # Пропускаем пустые строки
                    continue
                    
                current_y = y_position - i * line_height * 2
                
                if fill_type == "first_letter":
                    # Размножаем первую букву в каждой строке
                    if line:
                        first_char = line[0]
                        c.drawString(margin_left + 5, current_y, first_char * len(line))
                elif fill_type == "one_line":
                    # Размножаем первую строку на всю страницу
                    if i == 0 and line:
                        for j in range(5):  # Только первые 5 строк для предпросмотра
                            repeat_y = y_position - j * line_height * 2
                            c.drawString(margin_left + 5, repeat_y, line)
                        break  # Выводим только первую строку
                else:  # "all"
                    # Выводим текст как есть
                    c.drawString(margin_left + 5, current_y, line)
        
        # Сохраняем PDF в буфер
        c.save()
        
        # Перемещаем указатель в начало буфера
        buffer.seek(0)
        
        # В Vercel окружении возвращаем PDF напрямую
        if os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV') or os.path.exists('/.vercel/'):
            return Response(
                content=buffer.getvalue(),
                media_type="application/pdf",
                headers={"Content-Disposition": f"inline; filename=preview.pdf"}
            )
        else:
            # В локальном окружении сохраняем в файл
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"preview_{timestamp}.pdf"
            filepath = os.path.join(temp_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(buffer.getvalue())
            
            # Формируем URL для просмотра
            preview_url = f"/preview/{filename}"
            return {"status": "success", "message": "Предпросмотр создан успешно", "preview_url": preview_url}
            
    except Exception as e:
        print(f"Ошибка в /api/preview: {str(e)}")
        error_message = f"Произошла ошибка: {str(e)}"
        print(error_message)
        
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": error_message, "error_details": str(e)}
        )

# Добавляем маршрут для просмотра предпросмотра
@app.get("/preview/{filename}")
async def view_preview(filename: str):
    """
    Маршрут для просмотра предпросмотра
    """
    try:
        file_path = os.path.join(temp_dir, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Файл не найден")
            
        # Проверяем доступность файла для чтения
        if not os.access(file_path, os.R_OK):
            raise HTTPException(status_code=500, detail="Файл недоступен для чтения")
            
        return FileResponse(
            path=file_path, 
            filename=filename,
            media_type="application/pdf"
        )
    except Exception as e:
        print(f"Ошибка при просмотре файла {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при доступе к файлу: {str(e)}")

# Добавляем маршрут для скачивания файлов
@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Маршрут для скачивания сгенерированных файлов
    """
    try:
        file_path = os.path.join(temp_dir, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Файл не найден")
            
        # Проверяем доступность файла для чтения
        if not os.access(file_path, os.R_OK):
            raise HTTPException(status_code=500, detail="Файл недоступен для чтения")
            
        return FileResponse(
            path=file_path, 
            filename=filename,
            media_type="application/pdf"
        )
    except Exception as e:
        print(f"Ошибка при скачивании файла {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при доступе к файлу: {str(e)}")

@app.post("/api/generate-pdf")
async def generate_pdf(request: Request):
    """
    API для генерации PDF с прописями
    """
    try:
        # Получаем данные из запроса
        data = await request.json()
        
        # Получаем параметры или используем значения по умолчанию
        task = data.get("task", "practice")
        fill_type = data.get("fill_type", "first_letter")
        text = data.get("text", "")
        page_layout = data.get("page_layout", "lines")
        font_type = data.get("font_type", "gray")
        page_orientation = data.get("page_orientation", "portrait")
        student_name = data.get("student_name", "")
        
        # Создаем буфер в памяти вместо файла на диске
        buffer = io.BytesIO()
        
        # Определяем размер страницы
        if page_orientation == "landscape":
            pagesize = landscape(A4)
        else:
            pagesize = A4
        
        # Создаем PDF в буфере
        c = canvas.Canvas(buffer, pagesize=pagesize)
        width, height = pagesize
        
        # Настраиваем основной шрифт
        c.setFont(DEFAULT_FONT, 12)
        
        # Добавляем дату в углу
        c.setFont(DEFAULT_FONT, 8)
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        c.drawRightString(width - 20, height - 20, f"Дата: {today}")
        
        # Добавляем заголовок
        c.setFont(DEFAULT_FONT, 14)
        title = "Пропись для практики письма"
        c.drawString(30, height - 40, title)
        
        # Если указано имя ученика, добавляем его
        if student_name:
            c.setFont(DEFAULT_FONT, 12)
            c.drawString(30, height - 60, f"Ученик: {student_name}")
        
        # Определяем отступы
        margin_left = 30
        margin_top = 80
        content_width = width - 2 * margin_left
        content_height = height - margin_top - 30
        
        # Рисуем разметку на странице в зависимости от выбранного типа
        if page_layout == "cells":
            # Рисуем клетки
            cell_size = 15  # размер клетки в пунктах
            rows = int(content_height / cell_size)
            cols = int(content_width / cell_size)
            draw_school_grid(c, margin_left, height - margin_top, cell_size, rows, cols)
        elif page_layout == "lines_oblique":
            # Рисуем линии с наклонными линиями
            line_height = 12  # высота строки
            draw_propisi_lines(c, margin_left, height - margin_top, content_width, line_height, 20, True)
        else:  # "lines"
            # Рисуем обычные линии
            line_height = 12  # высота строки
            draw_propisi_lines(c, margin_left, height - margin_top, content_width, line_height, 20, False)
        
        # Добавляем текст прописи, если он есть
        if text:
            # Разбиваем текст на строки
            lines = text.split('\n')
            
            # Определяем параметры для текста
            c.setFont(DEFAULT_FONT, 12)
            y_position = height - margin_top - line_height
            
            # Стиль шрифта в зависимости от выбранного типа
            if font_type == "punktir":
                c.setFillColor(Color(0.7, 0.7, 0.7))  # Светло-серый для пунктира
            elif font_type == "gray":
                c.setFillColor(Color(0.5, 0.5, 0.5))  # Серый
            else:  # "black"
                c.setFillColor(black)
            
            # Выводим текст в зависимости от способа заполнения
            for i, line in enumerate(lines):
                if not line.strip():  # Пропускаем пустые строки
                    continue
                    
                current_y = y_position - i * line_height * 2
                
                # Прерываем, если вышли за пределы страницы
                if current_y < 30:
                    break
                
                if fill_type == "first_letter":
                    # Размножаем первую букву в каждой строке
                    if line:
                        first_char = line[0]
                        c.drawString(margin_left + 5, current_y, first_char * len(line))
                elif fill_type == "one_line":
                    # Размножаем первую строку на всю страницу
                    if i == 0 and line:
                        for j in range(20):  # Максимум 20 строк
                            repeat_y = y_position - j * line_height * 2
                            if repeat_y < 30:
                                break
                            c.drawString(margin_left + 5, repeat_y, line)
                        break  # Выводим только первую строку
                else:  # "all"
                    # Выводим текст как есть
                    c.drawString(margin_left + 5, current_y, line)
        
        # Сохраняем PDF в буфер
        c.save()
        
        # Перемещаем указатель в начало буфера
        buffer.seek(0)
        
        # В Vercel окружении возвращаем PDF напрямую
        if os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV') or os.path.exists('/.vercel/'):
            return Response(
                content=buffer.getvalue(),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=propisi.pdf"}
            )
        else:
            # В локальном окружении сохраняем в файл
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"propisi_{timestamp}.pdf"
            filepath = os.path.join(temp_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(buffer.getvalue())
            
            # Формируем URL для скачивания
            file_url = f"/download/{filename}"
            return {"status": "success", "message": "Пропись успешно сгенерирована", "file_url": file_url}
            
    except Exception as e:
        print(f"Ошибка в /api/generate-pdf: {str(e)}")
        error_type = type(e).__name__
        error_message = f"Произошла ошибка типа {error_type}: {str(e)}"
        print(error_message)
        
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": error_message, "error_details": str(e), "error_type": error_type}
        )

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