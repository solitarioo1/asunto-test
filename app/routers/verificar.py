from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import TURNSTILE_SITE_KEY
from app.services.turnstile import verificar_turnstile

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")

RUTA_DEFECTO = "/memorandos"


def _next_seguro(next_: str | None) -> str:
    if not next_ or not next_.startswith("/") or next_.startswith("//") or "://" in next_:
        return RUTA_DEFECTO
    return next_


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, next: str | None = None):
    return templates.TemplateResponse(
        request,
        "verificar/index.html",
        {"turnstile_site_key": TURNSTILE_SITE_KEY, "next": _next_seguro(next)},
    )


@router.post("/procesar", response_class=HTMLResponse)
async def procesar(
    request: Request,
    cf_turnstile_response: str = Form(default="", alias="cf-turnstile-response"),
    next: str = Form(default=RUTA_DEFECTO),
):
    destino = _next_seguro(next)
    ip_cliente = request.client.host if request.client else None

    if not await verificar_turnstile(cf_turnstile_response, ip_cliente):
        return templates.TemplateResponse(
            request,
            "verificar/index.html",
            {
                "turnstile_site_key": TURNSTILE_SITE_KEY,
                "next": destino,
                "error": "Verificación anti-bot fallida. Vuelve a intentarlo.",
            },
        )

    request.session["verificado_humano"] = True
    return RedirectResponse(destino, status_code=303)
