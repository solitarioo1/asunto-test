from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import SESSION_SECRET_KEY
from app.routers.memorandos import router as memorandos_router
from app.routers.padrones import router as padrones_router
from app.routers.validar_planillas import router as validar_planillas_router
from app.routers.verificar import router as verificar_router

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Utilidades - Correos")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.middleware("http")
async def exigir_verificacion(request: Request, call_next):
    if request.url.path.startswith("/static") or request.url.path.startswith("/verificar"):
        return await call_next(request)
    if not request.session.get("verificado_humano"):
        return RedirectResponse(f"/verificar?next={request.url.path}")
    return await call_next(request)


# Se agrega después del middleware de arriba: Starlette apila los middlewares en
# orden inverso, así SessionMiddleware queda "afuera" y llena request.session
# antes de que exigir_verificacion lo lea.
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie="sesion_verificacion",
    max_age=60 * 60 * 12,
)


@app.get("/")
async def raiz():
    return RedirectResponse("/memorandos")


app.include_router(verificar_router, prefix="/verificar")
app.include_router(memorandos_router, prefix="/memorandos")
app.include_router(padrones_router, prefix="/padrones")
app.include_router(validar_planillas_router, prefix="/validar_planillas")
