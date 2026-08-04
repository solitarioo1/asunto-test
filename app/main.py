from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers.upload import router as upload_router

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Generador de Asunto + Cuerpo de correo")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(upload_router)
