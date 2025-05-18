from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Подключаем основное приложение
from main import app as main_app

# Указываем Vercel, что мы используем FastAPI
app = main_app

# Для локальной разработки
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 