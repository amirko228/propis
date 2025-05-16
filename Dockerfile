FROM node:20 AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.10-slim

WORKDIR /app

# Копируем и устанавливаем зависимости бэкенда
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --only-binary=pillow pillow && \
    pip install --no-cache-dir -r requirements.txt --no-deps

# Копируем шрифты перед остальными файлами
COPY backend/fonts/ ./fonts/

# Копируем остальные файлы бэкенда
COPY backend/ .

# Копируем собранный фронтенд
COPY --from=frontend-builder /app/frontend/build ./static

# Создаем директорию для временных файлов
RUN mkdir -p temp

# Настройка FastAPI для обслуживания статического контента
RUN sed -i 's/app = FastAPI/app = FastAPI()\napp.mount\("\/static", StaticFiles(directory="static"), name="static"\)/g' main.py

# Проверяем, что шрифты на месте
RUN ls -la fonts/

# Экспонируем порт
EXPOSE 8000

# Запускаем приложение
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 