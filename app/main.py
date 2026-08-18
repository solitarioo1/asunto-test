from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers.memorandos import router as memorandos_router
from app.routers.padrones import router as padrones_router
from app.routers.validar_planillas import router as validar_planillas_router

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Utilidades - Correos")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
async def raiz():
    return RedirectResponse("/memorandos")


app.include_router(memorandos_router, prefix="/memorandos")
app.include_router(padrones_router, prefix="/padrones")
app.include_router(validar_planillas_router, prefix="/validar_planillas")
