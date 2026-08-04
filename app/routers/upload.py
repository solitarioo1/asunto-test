from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pypdf import PdfReader
import io
from pathlib import Path

from app.config import TURNSTILE_SITE_KEY
from app.services.file_intake import recolectar_pdfs
from app.services.pdf_extractor import CAMPOS_OBLIGATORIOS, armar_bloque_html, extraer_campos
from app.services.turnstile import verificar_turnstile

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"turnstile_site_key": TURNSTILE_SITE_KEY}
    )


@router.post("/procesar", response_class=HTMLResponse)
async def procesar(
    request: Request,
    archivos: list[UploadFile] = File(...),
    cf_turnstile_response: str = Form(default="", alias="cf-turnstile-response"),
):
    ip_cliente = request.client.host if request.client else None
    if not await verificar_turnstile(cf_turnstile_response, ip_cliente):
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "turnstile_site_key": TURNSTILE_SITE_KEY,
                "error": "Verificación anti-bot fallida. Vuelve a intentarlo.",
            },
        )

    pares = [(a.filename or "sin_nombre", await a.read()) for a in archivos]
    recolectados = recolectar_pdfs(pares)

    bloques = []
    n_revisar = 0
    n_error = 0
    n_descartado = 0

    for archivo in recolectados:
        if not archivo.valido:
            n_descartado += 1
            bloques.append(f"<p class='alerta'>[DESCARTADO {archivo.nombre}: {archivo.motivo}]</p>")
            continue

        try:
            reader = PdfReader(io.BytesIO(archivo.datos))
            if len(reader.pages) == 0:
                n_error += 1
                bloques.append(f"<p class='alerta'>[ERROR {archivo.nombre}: 0 páginas]</p>")
                continue

            texto = reader.pages[0].extract_text()
            campos = extraer_campos(texto)
            faltantes = [k for k in CAMPOS_OBLIGATORIOS if not campos.get(k)]

            if faltantes:
                n_revisar += 1
                bloques.append(
                    f"<p class='alerta'>[REVISAR {archivo.nombre}: faltan {faltantes}]</p>"
                )
                continue

            bloques.append(armar_bloque_html(campos))
        except Exception as e:
            n_error += 1
            bloques.append(f"<p class='alerta'>[ERROR {archivo.nombre}: {e}]</p>")

    total = len(recolectados)
    ok = total - n_revisar - n_error - n_descartado

    return templates.TemplateResponse(
        request,
        "resultado.html",
        {
            "turnstile_site_key": TURNSTILE_SITE_KEY,
            "total": total,
            "n_revisar": n_revisar,
            "n_error": n_error,
            "n_descartado": n_descartado,
            "ok": ok,
            "bloques": bloques,
        },
    )
