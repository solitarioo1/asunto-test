from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pypdf import PdfReader
import io
from pathlib import Path

from app.services.memorandos.file_intake import recolectar_pdfs
from app.services.memorandos.pdf_extractor import CAMPOS_OBLIGATORIOS, armar_bloque_html, extraer_campos

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request, "memorandos/index.html", {"activo": "memorandos"}
    )


@router.post("/procesar", response_class=HTMLResponse)
async def procesar(
    request: Request,
    archivos: list[UploadFile] = File(...),
):
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
        "memorandos/resultado.html",
        {
            "total": total,
            "n_revisar": n_revisar,
            "n_error": n_error,
            "n_descartado": n_descartado,
            "ok": ok,
            "bloques": bloques,
            "activo": "memorandos",
        },
    )
