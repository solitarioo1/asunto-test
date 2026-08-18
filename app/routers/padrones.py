from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.padrones.correo_builder import armar_correos
from app.services.padrones.excel_intake import recolectar_excels
from app.services.padrones.planilla_extractor import leer_planilla

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "padrones/index.html", {"activo": "padrones"})


@router.post("/procesar", response_class=HTMLResponse)
async def procesar(request: Request, archivos: list[UploadFile] = File(...)):
    pares = [(a.filename or "sin_nombre", await a.read()) for a in archivos]
    recolectados = recolectar_excels(pares)

    alertas_archivo = []
    planillas = []

    for archivo in recolectados:
        if not archivo.valido:
            alertas_archivo.append(f"[{archivo.nombre}] descartado: {archivo.motivo}")
            continue
        planillas.append(leer_planilla(archivo.nombre, archivo.datos))

    resultado = armar_correos(planillas)
    resultado["alertas_archivo"] = alertas_archivo + resultado["alertas_archivo"]

    return templates.TemplateResponse(
        request,
        "padrones/resultado.html",
        {
            "activo": "padrones",
            "correos_listos": resultado["correos_listos"],
            "grupos_con_alerta": resultado["grupos_con_alerta"],
            "alertas_archivo": resultado["alertas_archivo"],
        },
    )
