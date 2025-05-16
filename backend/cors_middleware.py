from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

def setup_cors(app: FastAPI):
    """
    Настройка CORS для приложения FastAPI
    """
    # Получаем список разрешенных доменов из переменной окружения или используем значение по умолчанию
    origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://propis.vercel.app")
    origins = origins_env.split(',')
    
    # Добавляем промежуточное ПО CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    print(f"CORS настроен для доменов: {origins}") 