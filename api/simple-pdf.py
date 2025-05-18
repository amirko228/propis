from http.server import BaseHTTPRequestHandler
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Создаем буфер в памяти для PDF
            buffer = io.BytesIO()
            
            # Создаем PDF
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            
            # Добавляем простой текст
            c.setFont("Helvetica", 24)
            c.drawString(100, height - 100, "Тестовый PDF")
            
            c.setFont("Helvetica", 16)
            c.drawString(100, height - 150, "Этот файл был создан на Vercel")
            c.drawString(100, height - 180, "Если вы видите этот текст, значит генерация PDF работает!")
            
            # Сохраняем PDF
            c.save()
            
            # Получаем содержимое буфера
            buffer.seek(0)
            pdf_content = buffer.read()
            
            # Отправляем PDF в ответе
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', 'inline; filename="test.pdf"')
            self.send_header('Content-Length', str(len(pdf_content)))
            self.end_headers()
            self.wfile.write(pdf_content)
            
        except Exception as e:
            # В случае ошибки возвращаем текстовую ошибку
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            error_message = f"Ошибка при создании PDF: {str(e)} | Тип: {type(e).__name__}"
            self.wfile.write(error_message.encode('utf-8')) 