from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
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

# Регистрируем шрифты
FONT_LOADED = False
try:
    # Получаем абсолютный путь к текущему файлу
    current_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(current_dir, "fonts")
    
    # В режиме Vercel проверяем специальный путь для шрифтов
    if os.environ.get('VERCEL', False) and not os.path.exists(fonts_dir):
        # Пробуем найти шрифты в другой директории на Vercel
        vercel_dir = os.path.dirname(os.path.dirname(current_dir))
        fonts_dir = os.path.join(vercel_dir, "backend", "fonts")
    
    print(f"Директория со шрифтами: {fonts_dir}")
    
    # Проверяем содержимое директории шрифтов
    if os.path.exists(fonts_dir):
        print("Содержимое директории шрифтов:")
        for f in os.listdir(fonts_dir):
            print(f"  - {f}")
    else:
        print(f"Директория {fonts_dir} не найдена!")
    
    # Пробуем сначала ilyukhina.ttf
    ilyukhina_path = os.path.join(fonts_dir, "ilyukhina.ttf")
    if os.path.exists(ilyukhina_path) and os.path.getsize(ilyukhina_path) > 0:
        print("Регистрируем шрифт ilyukhina.ttf")
        pdfmetrics.registerFont(TTFont('Propisi', ilyukhina_path))
        FONT_LOADED = True
        print("Шрифт ilyukhina.ttf успешно загружен")
    else:
        # Если нет, пробуем propisi.ttf
        propisi_path = os.path.join(fonts_dir, "propisi.ttf")
        if os.path.exists(propisi_path) and os.path.getsize(propisi_path) > 0:
            print("Регистрируем шрифт propisi.ttf")
            pdfmetrics.registerFont(TTFont('Propisi', propisi_path))
            FONT_LOADED = True
            print("Шрифт propisi.ttf успешно загружен")
        else:
            print("Ни один из шрифтов не найден или файлы повреждены!")
            FONT_LOADED = False
except Exception as e:
    print(f"Ошибка при загрузке шрифта: {e}")
    import traceback
    traceback.print_exc()
    FONT_LOADED = False

# Определяем шрифт, который будет использоваться
print(f"Статус загрузки шрифта: {FONT_LOADED}")
DEFAULT_FONT = "Propisi" if FONT_LOADED else "Helvetica-Oblique"
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
        # Используем увеличенную частоту и диапазон для гарантии покрытия
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
    try:
        # Логируем полученные параметры
        print(f"Получены параметры для генерации PDF:")
        print(f"- task: {task}")
        print(f"- fill_type: {fill_type}")
        print(f"- page_layout: {page_layout}")
        print(f"- font_type: {font_type}")
        print(f"- page_orientation: {page_orientation}")
        print(f"- student_name: {student_name}")
        print(f"- text length: {len(text)} символов")
        
        # Создаем PDF сразу в памяти без записи на диск
        # Определяем ориентацию страницы
        page_size = landscape(A4) if page_orientation == "landscape" else A4
        print(f"Размер страницы: {page_size}")
        
        # Создаем PDF в памяти
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=page_size)
    
    # Минимальные отступы страницы 
    margin_left = 2
    margin_right = 2
    margin_top = 2
    margin_bottom = 2
    
    # Заголовок задания делаем невидимым или удаляем
    # c.setFont("Helvetica-Bold", 12)
    # c.drawString(margin_left, page_size[1] - margin_top, task)
    
    # Определяем параметры разметки страницы
    content_width = page_size[0] - margin_left - margin_right
    content_height = page_size[1] - margin_top - margin_bottom
    
    # Рисуем линии или клетки в зависимости от выбранного шаблона
    y_start = page_size[1] - margin_top
    
    # Разбиваем текст на строки
    lines = text.strip().split('\n')
    if not lines:
        lines = [""]
    
    # Обрабатываем варианты заполнения
    processed_lines = []
    
    if fill_type == "all":
        # Все строки без изменений
        processed_lines = lines
    elif fill_type == "first_letter":
        # Размножаем первую букву в каждой строке
        for line in lines:
            if line:
                first_char = line[0]
                processed_lines.append(first_char * 30)  # Размножаем букву на строку
            else:
                processed_lines.append("")
    elif fill_type == "one_line":
        # Размножаем первую строку на весь лист
        if lines[0]:
            first_line = lines[0]
            processed_lines = [first_line] * 10  # 10 строк с одинаковым текстом
        else:
            processed_lines = [""] * 10
    
    # Ограничиваем количество строк для отображения
    max_lines = min(10, len(processed_lines))
    
    # Используем всю доступную ширину для содержимого
    content_start_x = margin_left
    content_usable_width = content_width
    
    # Определяем параметры отрисовки в зависимости от типа разметки
    if page_layout == "cells":
        # Для клеточек
        cell_size = 25  # Размер клетки в пунктах
        
        # Рассчитываем количество строк и столбцов для заполнения всей страницы
        rows = int(content_height / cell_size) + 1  # +1 для гарантии заполнения
        cols = int(content_usable_width / cell_size)
        
        # Рисуем школьные клетки с стандартными настройками на всю страницу
        draw_school_grid(c, content_start_x, y_start, cell_size, rows, cols)
        
        # Расстояние между буквами для клеток - используем размер клетки
        char_width = cell_size
        char_offset_y = cell_size * 0.5  # Точно центрируем символы в клетке по вертикали
        line_height = cell_size
        line_gap = 0
        
        # Размер шрифта для клеток
        cell_font_size = 20  # Размер немного меньше клетки для лучшего визуального восприятия
    else:
        # Для линейки параметры
        line_height = 14  # Высота между линиями
        line_gap = 0  # Полностью убираем отступы
        
        # Рисуем линейки для прописей на всю ширину страницы
        # Сначала горизонтальные линии для всех типов линеек
        c.setDash([])  # Сплошная линия для разметки
        c.setLineWidth(0.3)
        
        # Разные оттенки серого для линий
        light_gray = Color(0.85, 0.85, 0.85)  # Верхняя и нижняя линии
        dark_gray = Color(0.6, 0.6, 0.6)      # Основная (средняя) линия
        
        # Рассчитываем количество групп линий на странице
        group_height = line_height * 2  # Высота группы из трех линий
        total_groups = int(content_height / group_height) + 2  # +2 для запаса
        
        # Рисуем горизонтальные линии
        for i in range(total_groups):
            base_y = y_start - i * group_height
            
            # Пропускаем, если вышли за пределы страницы
            if base_y - line_height < 0:
                continue
                
            # Средняя линия (темнее)
            c.setStrokeColor(dark_gray)
            c.line(content_start_x, base_y, content_start_x + content_usable_width, base_y)
            
            # Верхняя линия (светлее)
            c.setStrokeColor(light_gray)
            c.line(content_start_x, base_y + line_height, 
                  content_start_x + content_usable_width, base_y + line_height)
            
            # Нижняя линия (светлее)
            c.line(content_start_x, base_y - line_height,
                  content_start_x + content_usable_width, base_y - line_height)
        
        # Если нужны косые линии, добавляем их
        if page_layout == "lines_oblique":
            # Настройки для косых линий
            c.setStrokeColor(Color(0.8, 0.8, 0.8))  # Светло-серый цвет
            c.setLineWidth(0.25)  # Тонкие линии
            
            # Угол наклона: положительный угол для наклона влево-вниз (как на первом скрине)
            angle = 58  # градусов
            
            # Шаг между линиями
            step = 18  # пикселей, делаем линии более редкими как на первом скрине
            
            # Вычисляем расстояние, необходимое для пересечения страницы
            page_width = page_size[0]
            page_height = page_size[1]
            
            # Вычисляем дельту X для заданного угла наклона
            delta_x = page_height / math.tan(math.radians(abs(angle)))
            
            # Рисуем линии с отрицательным отступом для гарантии покрытия всей страницы
            start_x = -delta_x
            while start_x < page_width + delta_x:
                # Рисуем линию от верхнего края до нижнего
                if angle < 0:  # Наклон вправо
                    c.line(start_x, page_height, start_x + delta_x, 0)
                else:  # Наклон влево (как на первом скрине)
                    c.line(start_x, page_height, start_x - delta_x, 0)
                
                # Смещаем начало для следующей линии
                start_x += step
        
        # Расстояние между буквами для линейки - адаптируем на основе высоты линий
        char_width = line_height * 1.5  # Адаптивная ширина букв
        char_offset_y = 0  # Для линеек выравниваем по базовой линии
        
        # Размер шрифта для линеек
        line_font_size = 24  # Чуть больше для линеек
    
    # Добавляем текст с учетом типа разметки
    for i in range(max_lines):
        if page_layout == "cells":
            # Позиция для текста в клетках - центрируем по ячейке
            base_y = y_start - i * cell_size - char_offset_y
        else:
            # Позиция для текста в линейке (основная линия)
            group_height = line_height * 2  # Общая высота группы из трех линий
            line_gap = 0  # Полностью убираем отступы
            base_y = y_start - i * (group_height + line_gap)  # Точно по средней линии
        
        # Добавляем текст, если есть
        if i < len(processed_lines) and processed_lines[i]:
            # Используем шрифт прописей, если доступен
            try:
                # Фиксированный размер шрифта для прописей
                font_size = 20 if page_layout == "cells" else 28  # Увеличиваем размер шрифта для линеек
                c.setFont(DEFAULT_FONT, font_size)
            except:
                # Запасной вариант со стандартным шрифтом
                font_size = 14 if page_layout == "cells" else 24
                c.setFont("Helvetica-Italic", font_size)
            
            # Применение стилей для букв
            for j, char in enumerate(processed_lines[i]):
                # Расположение символа с учетом типа разметки
                if page_layout == "cells":
                    # Для клеток - центрируем каждую букву в своей клетке
                    x = content_start_x + j * cell_size + cell_size/2 - font_size/3
                    this_base_y = base_y
                    
                    # Смещения для визуального центрирования в клетке
                    if char.isupper():
                        this_base_y += cell_size * 0.05  # Слегка вверх
                    elif char.islower():
                        this_base_y -= cell_size * 0.05  # Слегка вниз
                else:
                    # Для линеек - размещаем буквы так, чтобы каждая занимала ровно одну секцию
                    # Рассчитываем ширину одной секции между линиями
                    section_width = line_height * 2  # Ширина одной секции (равна высоте между линиями)
                    
                    # Позиционируем каждую букву точно в своей клетке/секции
                    x = content_start_x + j * section_width + section_width * 0.3
                    
                    # Позиционирование по вертикали зависит от типа буквы
                    if char.isupper():  # Заглавные буквы
                        # Заглавные буквы опираются на нижнюю линию и достигают верхней
                        this_base_y = base_y - line_height * 0.1  # Чуть выше средней линии
                    else:  # Строчные буквы
                        # Строчные буквы размещаем между средней и нижней линией
                        this_base_y = base_y - line_height * 0.7  # Ближе к нижней линии
                
                # Проверка на выход за границы страницы
                if x < content_start_x + content_usable_width - (cell_size if page_layout == "cells" else char_width):
                    # Применяем выбранный стиль шрифта
                    if font_type == "punktir":
                        # Для пунктирного шрифта - имитируем пунктирный контур
                        c.saveState()
                        
                        if page_layout == "cells":
                            # Для клеток - используем светло-серую заливку
                            c.setFont(DEFAULT_FONT, font_size)
                            c.setFillColor(Color(0.7, 0.7, 0.7))  # Светло-серый
                            c.drawString(x, this_base_y, char)
                        else:
                            # Для линеек - используем тот же подход
                            c.setFont(DEFAULT_FONT, font_size)
                            # Делаем буквы светло-серыми, чтобы они выглядели как пунктир
                            c.setFillColor(Color(0.7, 0.7, 0.7))  # Светло-серый
                            c.drawString(x, this_base_y, char)
                        
                        c.restoreState()
                    elif font_type == "gray":
                        # Очень светлый серый цвет для букв
                        c.setFillColor(Color(0.6, 0.6, 0.6))
                        c.drawString(x, this_base_y, char)
                    else:  # "black"
                        # Черный цвет для букв
                        c.setFillColor(black)
                        c.drawString(x, this_base_y, char)
    
    # Добавляем красную линию по правой стороне как в тетради
    c.setStrokeColor(red)
    c.setDash([])  # Сплошная линия
    c.setLineWidth(1.0)  # Устанавливаем толщину красной линии
    
    # Позиция красной полосы - точно по правому краю
    red_line_x = page_size[0] - 2  # Близко к правому краю
    red_line_top = page_size[1] - 1  # Почти до верха страницы
    red_line_bottom = 1  # Почти до низа страницы
    c.line(red_line_x, red_line_top, red_line_x, red_line_bottom)
    
    # Убираем подпись внизу страницы
    
    c.save()
    
    # Получаем данные из буфера и возвращаем напрямую
    buffer.seek(0)
    pdf_data = buffer.getvalue()
    
    # Проверяем размер созданного PDF
    file_size = len(pdf_data)
    print(f"Размер PDF файла в памяти: {file_size} байт")
    
    if file_size == 0:
        raise HTTPException(status_code=500, detail="Создан пустой PDF файл")
    
    # Возвращаем PDF напрямую из памяти
    from fastapi.responses import Response
    return Response(
        content=pdf_data, 
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=propisi.pdf"}
    )
    except Exception as e:
        # Логируем ошибку и возвращаем детальную информацию
        import traceback
        error_details = traceback.format_exc()
        print(f"Ошибка при генерации PDF: {e}")
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации PDF: {str(e)}")

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
    Генерирует предварительный просмотр страницы прописи в формате PDF
    """
    try:
        # Логируем полученные параметры
        print(f"Получены параметры для предпросмотра:")
        print(f"- task: {task}")
        print(f"- fill_type: {fill_type}")
        print(f"- page_layout: {page_layout}")
        print(f"- font_type: {font_type}")
        print(f"- page_orientation: {page_orientation}")
        print(f"- student_name: {student_name}")
        print(f"- text length: {len(text)} символов")
        
        # Создаем PDF сразу в памяти
        print("Создаем PDF в памяти для предпросмотра")
    
    # Определяем ориентацию страницы
    page_size = landscape(A4) if page_orientation == "landscape" else A4
    
    # Создаем PDF в памяти
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=page_size)
    
    # Минимальные отступы страницы 
    margin_left = 2
    margin_right = 2
    margin_top = 2
    margin_bottom = 2
    
    # Определяем параметры разметки страницы
    content_width = page_size[0] - margin_left - margin_right
    content_height = page_size[1] - margin_top - margin_bottom
    
    # Рисуем линии или клетки в зависимости от выбранного шаблона
    y_start = page_size[1] - margin_top
    
    # Обрабатываем только первые 2-3 строки для предпросмотра
    lines = text.strip().split('\n')
    if not lines:
        lines = [""]
    
    # Обрезаем текст до первых 3 строк для предпросмотра
    lines = lines[:min(3, len(lines))]
    
    # Обрабатываем варианты заполнения
    processed_lines = []
    
    if fill_type == "all":
        # Все строки без изменений
        processed_lines = lines
    elif fill_type == "first_letter":
        # Размножаем первую букву в каждой строке
        for line in lines:
            if line:
                first_char = line[0]
                processed_lines.append(first_char * 10)  # Меньше букв для предпросмотра
            else:
                processed_lines.append("")
    elif fill_type == "one_line":
        # Размножаем первую строку на весь предпросмотр
        if lines[0]:
            first_line = lines[0]
            processed_lines = [first_line] * min(3, len(lines))
        else:
            processed_lines = [""] * min(3, len(lines))
    
    # Ограничиваем количество строк для отображения
    max_lines = len(processed_lines)
    
    # Используем всю доступную ширину для содержимого
    content_start_x = margin_left
    content_usable_width = content_width
    
    # Определяем параметры отрисовки в зависимости от типа разметки
    if page_layout == "cells":
        # Для клеточек
        cell_size = 25  # Размер клетки в пунктах
        
        # Рассчитываем количество строк и столбцов для заполнения всей страницы
        rows = min(10, int(content_height / cell_size) + 1)  # Ограничиваем для предпросмотра
        cols = int(content_usable_width / cell_size)
        
        # Рисуем школьные клетки с стандартными настройками на всю страницу
        draw_school_grid(c, content_start_x, y_start, cell_size, rows, cols)
        
        # Расстояние между буквами для клеток - используем размер клетки
        char_width = cell_size
        char_offset_y = cell_size * 0.5  # Точно центрируем символы в клетке по вертикали
        line_height = cell_size
        line_gap = 0
        
        # Размер шрифта для клеток
        cell_font_size = 20  # Размер немного меньше клетки для лучшего визуального восприятия
    else:
        # Для линейки параметры
        line_height = 14  # Высота между линиями
        line_gap = 0  # Полностью убираем отступы
        
        # Рисуем линейки для прописей на всю ширину страницы
        # Сначала горизонтальные линии для всех типов линеек
        c.setDash([])  # Сплошная линия для разметки
        c.setLineWidth(0.3)
        
        # Разные оттенки серого для линий
        light_gray = Color(0.85, 0.85, 0.85)  # Верхняя и нижняя линии
        dark_gray = Color(0.6, 0.6, 0.6)      # Основная (средняя) линия
        
        # Рассчитываем количество групп линий на странице (ограничиваем для предпросмотра)
        group_height = line_height * 2  # Высота группы из трех линий
        total_groups = min(6, int(content_height / group_height) + 1)
        
        # Рисуем горизонтальные линии
        for i in range(total_groups):
            base_y = y_start - i * group_height
            
            # Пропускаем, если вышли за пределы страницы
            if base_y - line_height < 0:
                continue
                
            # Средняя линия (темнее)
            c.setStrokeColor(dark_gray)
            c.line(content_start_x, base_y, content_start_x + content_usable_width, base_y)
            
            # Верхняя линия (светлее)
            c.setStrokeColor(light_gray)
            c.line(content_start_x, base_y + line_height, 
                  content_start_x + content_usable_width, base_y + line_height)
            
            # Нижняя линия (светлее)
            c.line(content_start_x, base_y - line_height,
                  content_start_x + content_usable_width, base_y - line_height)
        
        # Если нужны косые линии, добавляем их
        if page_layout == "lines_oblique":
            # Настройки для косых линий
            c.setStrokeColor(Color(0.8, 0.8, 0.8))  # Светло-серый цвет
            c.setLineWidth(0.25)  # Тонкие линии
            
            # Угол наклона: положительный угол для наклона влево-вниз (как на первом скрине)
            angle = 58  # градусов
            
            # Шаг между линиями
            step = 18  # пикселей, делаем линии более редкими 
            
            # Вычисляем расстояние, необходимое для пересечения страницы
            page_width = page_size[0]
            page_height = page_size[1]
            
            # Вычисляем дельту X для заданного угла наклона
            delta_x = page_height / math.tan(math.radians(abs(angle)))
            
            # Рисуем линии с отрицательным отступом для гарантии покрытия всей страницы
            start_x = -delta_x
            while start_x < page_width + delta_x:
                # Рисуем линию от верхнего края до нижнего
                if angle < 0:  # Наклон вправо
                    c.line(start_x, page_height, start_x + delta_x, 0)
                else:  # Наклон влево (как на первом скрине)
                    c.line(start_x, page_height, start_x - delta_x, 0)
                
                # Смещаем начало для следующей линии
                start_x += step
        
        # Расстояние между буквами для линейки - адаптируем на основе высоты линий
        char_width = line_height * 1.5  # Адаптивная ширина букв
        char_offset_y = 0  # Для линеек выравниваем по базовой линии
        
        # Размер шрифта для линеек
        line_font_size = 28  # Увеличиваем размер шрифта для линеек
    
    # Добавляем текст с учетом типа разметки
    for i in range(max_lines):
        if page_layout == "cells":
            # Позиция для текста в клетках - центрируем по ячейке
            base_y = y_start - i * cell_size - char_offset_y
        else:
            # Позиция для текста в линейке (основная линия)
            group_height = line_height * 2  # Общая высота группы из трех линий
            line_gap = 0  # Полностью убираем отступы
            base_y = y_start - i * (group_height + line_gap)  # Точно по средней линии
        
        # Добавляем текст, если есть
        if i < len(processed_lines) and processed_lines[i]:
            # Используем шрифт прописей, если доступен
            try:
                # Фиксированный размер шрифта для прописей
                font_size = 20 if page_layout == "cells" else 28  # Увеличиваем размер шрифта для линеек
                c.setFont(DEFAULT_FONT, font_size)
            except:
                # Запасной вариант со стандартным шрифтом
                font_size = 14 if page_layout == "cells" else 24
                c.setFont("Helvetica-Italic", font_size)
            
            # Применение стилей для букв
            for j, char in enumerate(processed_lines[i]):
                # Расположение символа с учетом типа разметки
                if page_layout == "cells":
                    # Для клеток - центрируем каждую букву в своей клетке
                    x = content_start_x + j * cell_size + cell_size/2 - font_size/3
                    this_base_y = base_y
                    
                    # Смещения для визуального центрирования в клетке
                    if char.isupper():
                        this_base_y += cell_size * 0.05  # Слегка вверх
                    elif char.islower():
                        this_base_y -= cell_size * 0.05  # Слегка вниз
                else:
                    # Для линеек - размещаем буквы так, чтобы каждая занимала ровно одну секцию
                    # Рассчитываем ширину одной секции между линиями
                    section_width = line_height * 2  # Ширина одной секции (равна высоте между линиями)
                    
                    # Позиционируем каждую букву точно в своей клетке/секции
                    x = content_start_x + j * section_width + section_width * 0.3
                    
                    # Позиционирование по вертикали зависит от типа буквы
                    if char.isupper():  # Заглавные буквы
                        # Заглавные буквы опираются на нижнюю линию и достигают верхней
                        this_base_y = base_y - line_height * 0.1  # Чуть выше средней линии
                    else:  # Строчные буквы
                        # Строчные буквы размещаем между средней и нижней линией
                        this_base_y = base_y - line_height * 0.7  # Ближе к нижней линии
                
                # Проверка на выход за границы страницы и ограничение количества символов для предпросмотра
                # Для предпросмотра ограничиваем количество символов по ширине (до 15)
                if j < 15 and x < content_start_x + content_usable_width - (cell_size if page_layout == "cells" else section_width):
                    # Применяем выбранный стиль шрифта
                    if font_type == "punktir":
                        # Для пунктирного шрифта - имитируем пунктирный контур
                        c.saveState()
                        
                        if page_layout == "cells":
                            # Для клеток - используем светло-серую заливку
                            c.setFont(DEFAULT_FONT, font_size)
                            c.setFillColor(Color(0.7, 0.7, 0.7))  # Светло-серый
                            c.drawString(x, this_base_y, char)
                        else:
                            # Для линеек - используем тот же подход
                            c.setFont(DEFAULT_FONT, font_size)
                            # Делаем буквы светло-серыми, чтобы они выглядели как пунктир
                            c.setFillColor(Color(0.7, 0.7, 0.7))  # Светло-серый
                            c.drawString(x, this_base_y, char)
                        
                        c.restoreState()
                    elif font_type == "gray":
                        # Очень светлый серый цвет для букв
                        c.setFillColor(Color(0.6, 0.6, 0.6))
                        c.drawString(x, this_base_y, char)
                    else:  # "black"
                        # Черный цвет для букв
                        c.setFillColor(black)
                        c.drawString(x, this_base_y, char)
    
    # Добавляем красную линию по правой стороне как в тетради
    c.setStrokeColor(red)
    c.setDash([])  # Сплошная линия
    c.setLineWidth(1.0)  # Устанавливаем толщину красной линии
    
    # Позиция красной полосы - точно по правому краю
    red_line_x = page_size[0] - 2  # Близко к правому краю
    red_line_top = page_size[1] - 1  # Почти до верха страницы
    red_line_bottom = 1  # Почти до низа страницы
    c.line(red_line_x, red_line_top, red_line_x, red_line_bottom)
    
    c.save()
    
    # Получаем данные из буфера и сохраняем в файл
    c.save()
    buffer.seek(0)
    pdf_data = buffer.getvalue()
    
    # Проверяем размер PDF
    file_size = len(pdf_data)
    print(f"Размер PDF файла для предпросмотра: {file_size} байт")
    
    if file_size == 0:
        raise HTTPException(status_code=500, detail="Создан пустой PDF файл для предпросмотра")
    
    # Возвращаем PDF напрямую из памяти
    from fastapi.responses import Response
    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=preview.pdf"}
    )
except Exception as e:
        # Логируем ошибку и возвращаем детальную информацию
        import traceback
        error_details = traceback.format_exc()
        print(f"Ошибка при генерации предпросмотра: {e}")
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации предпросмотра: {str(e)}")

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