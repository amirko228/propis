from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import io
import traceback
from fpdf import FPDF
import json

app = FastAPI()

@app.post("/generate-pdf")
async def generate_pdf(request: Request):
    try:
        # Получаем и логируем данные запроса
        data = await request.json()
        print(f"Received data: {json.dumps(data, indent=2)}")
        
        # Создаем PDF с помощью fpdf2
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        
        # Устанавливаем ориентацию страницы
        orientation = data.get('page_orientation', 'portrait')
        if orientation == 'landscape':
            pdf = FPDF(orientation='L', unit='mm', format='A4')
        
        pdf.add_page()
        pdf.set_font('helvetica', size=16)
        
        # Добавляем заголовок
        pdf.cell(0, 10, 'Пропись для практики письма', ln=True, align='C')
        
        # Добавляем имя ученика, если есть
        student_name = data.get('student_name', '')
        if student_name:
            pdf.set_font('helvetica', size=12)
            pdf.cell(0, 10, f'Ученик: {student_name}', ln=True)
        
        # Обрабатываем текст
        pdf.set_font('helvetica', size=12)
        
        # Определяем цвет текста
        text_color = (0, 0, 0)  # черный по умолчанию
        font_type = data.get('font_type', 'black')
        if font_type == 'gray':
            text_color = (128, 128, 128)
        elif font_type == 'punktir':
            text_color = (180, 180, 180)
        
        pdf.set_text_color(*text_color)
        
        # Добавляем текст
        text = data.get('text', '')
        fill_type = data.get('fill_type', 'all')
        
        lines = text.split('\n')
        text_content = []
        
        # Обрабатываем текст согласно типу заполнения
        if fill_type == 'one_line' and lines and lines[0].strip():
            # Размножаем первую строку
            first_line = lines[0].strip()
            for i in range(20):
                text_content.append(first_line)
        elif fill_type == 'first_letter':
            # Размножаем первую букву каждой строки
            for line in lines:
                if not line.strip():
                    continue
                first_char = line[0] if line else ''
                if first_char:
                    text_content.append(first_char * 30)
        else:
            # Используем текст как есть
            text_content = [line for line in lines if line.strip()]
        
        # Добавляем строки в PDF
        pdf.ln(10)
        for line in text_content:
            pdf.cell(0, 10, line, ln=True)
            pdf.ln(5)  # Дополнительный отступ между строками
        
        # Получаем байты PDF
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        
        # Возвращаем PDF как поток байтов
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=propisi_{data.get('student_name', 'practice')}.pdf"}
        )
    except Exception as e:
        # Детальное логирование ошибки
        error_details = traceback.format_exc()
        print(f"Error generating PDF: {str(e)}\n{error_details}")
        
        # Возвращаем информативную ошибку
        return JSONResponse(
            status_code=500,
            content={
                "status": "error", 
                "message": str(e), 
                "details": error_details
            }
        )

# Временное решение для отладки - отдельный эндпоинт
@app.post("/generate-pdf-debug")
async def generate_pdf_debug(request: Request):
    try:
        data = await request.json()
        print(f"Received data in debug endpoint: {json.dumps(data, indent=2)}")
        return {"status": "success", "message": "Endpoint works, but PDF generation disabled for testing"}
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in debug endpoint: {str(e)}\n{error_details}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e), "details": error_details}
        ) 