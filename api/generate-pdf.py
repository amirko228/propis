from http.server import BaseHTTPRequestHandler
import json
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import Color
import base64
import datetime

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Получаем данные запроса
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Получаем параметры из запроса
            fill_type = data.get("fill_type", "first_letter")
            text = data.get("text", "")
            page_layout = data.get("page_layout", "lines")
            font_type = data.get("font_type", "black")
            page_orientation = data.get("page_orientation", "portrait")
            student_name = data.get("student_name", "")
            
            # Создаем буфер в памяти для PDF
            buffer = io.BytesIO()
            
            # Определяем размер страницы
            if page_orientation == "landscape":
                pagesize = landscape(A4)
            else:
                pagesize = A4
            
            # Создаем PDF
            c = canvas.Canvas(buffer, pagesize=pagesize)
            width, height = pagesize
            
            # Настраиваем шрифт
            c.setFont("Helvetica", 12)
            
            # Добавляем заголовок
            c.setFont("Helvetica", 14)
            c.drawString(30, height - 40, "Пропись для практики письма")
            
            # Добавляем дату
            c.setFont("Helvetica", 10)
            today = datetime.datetime.now().strftime("%d.%m.%Y")
            c.drawRightString(width - 20, height - 20, f"Дата: {today}")
            
            # Если указано имя ученика, добавляем его
            if student_name:
                c.setFont("Helvetica", 12)
                c.drawString(30, height - 60, f"Ученик: {student_name}")
            
            # Определяем отступы
            margin_left = 30
            margin_top = 80
            
            # Рисуем базовую разметку (упрощенную)
            c.setLineWidth(0.3)
            c.setStrokeColor(Color(0.7, 0.7, 0.7))
            
            # Рисуем горизонтальные линии на всю страницу
            line_height = 20
            current_y = height - margin_top
            while current_y > 30:
                c.line(margin_left, current_y, width - margin_left, current_y)
                current_y -= line_height
            
            # Определяем стиль шрифта для текста
            if font_type == "punktir":
                c.setFillColor(Color(0.7, 0.7, 0.7))  # Светло-серый для пунктира
            elif font_type == "gray":
                c.setFillColor(Color(0.5, 0.5, 0.5))  # Серый
            else:  # "black"
                c.setFillColor(Color(0, 0, 0))  # Черный
            
            # Добавляем текст на страницу
            if text:
                lines = text.split('\n')
                y_position = height - margin_top + 5  # Немного выше линии
                
                # Выводим текст в зависимости от способа заполнения
                if fill_type == "first_letter":
                    # Размножаем первую букву в каждой строке
                    for i, line in enumerate(lines):
                        if line.strip():
                            first_char = line[0]
                            current_y = y_position - i * line_height
                            if current_y > 30:
                                c.drawString(margin_left + 10, current_y, first_char * 30)
                
                elif fill_type == "one_line":
                    # Размножаем первую строку на всю страницу
                    if lines and lines[0].strip():
                        first_line = lines[0].strip()
                        for i in range(20):  # Максимум 20 строк
                            current_y = y_position - i * line_height
                            if current_y > 30:
                                c.drawString(margin_left + 10, current_y, first_line)
                
                else:  # "all"
                    # Выводим текст как есть
                    for i, line in enumerate(lines):
                        if line.strip():
                            current_y = y_position - i * line_height
                            if current_y > 30:
                                c.drawString(margin_left + 10, current_y, line)
            
            # Сохраняем PDF
            c.save()
            
            # Получаем содержимое буфера
            buffer.seek(0)
            pdf_content = buffer.read()
            
            # Отправляем PDF в ответе
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            filename = f"propisi_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(len(pdf_content)))
            self.end_headers()
            self.wfile.write(pdf_content)
            
        except Exception as e:
            # В случае ошибки возвращаем простой текстовый PDF
            try:
                # Создаем простой PDF с сообщением об ошибке
                error_buffer = io.BytesIO()
                c = canvas.Canvas(error_buffer, pagesize=A4)
                width, height = A4
                
                c.setFont("Helvetica", 14)
                c.drawString(30, height - 40, "Ошибка при создании PDF")
                
                c.setFont("Helvetica", 12)
                c.drawString(30, height - 80, f"Тип ошибки: {type(e).__name__}")
                c.drawString(30, height - 100, f"Сообщение: {str(e)}")
                
                c.save()
                
                error_buffer.seek(0)
                error_pdf = error_buffer.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.send_header('Content-Disposition', 'attachment; filename="error_report.pdf"')
                self.send_header('Content-Length', str(len(error_pdf)))
                self.end_headers()
                self.wfile.write(error_pdf)
                
            except:
                # Если даже создание PDF с ошибкой не сработало, возвращаем текстовую ошибку
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": str(e),
                    "type": type(e).__name__
                }).encode('utf-8')) 