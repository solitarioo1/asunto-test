from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.validar_planillas.comparador import comparar
from app.services.validar_planillas.intake import clasificar, recolectar_xls
from app.services.validar_planillas.memo_extractor import leer_memo
from app.services.validar_planillas.orden_pago_extractor import leer_orden_pago

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "validar_planillas/index.html", {"activo": "validar_planillas"})


@router.post("/procesar", response_class=HTMLResponse)
async def procesar(request: Request, archivos: list[UploadFile] = File(...)):
    pares = [(a.filename or "sin_nombre", await a.read()) for a in archivos]
    recolectados = recolectar_xls(pares)

    alertas_archivo = []
    memos = []
    ordenes = []

    for archivo in recolectados:
        if not archivo.valido:
            alertas_archivo.append(f"[{archivo.nombre}] descartado: {archivo.motivo}")
            continue

        tipo = clasificar(archivo.nombre)
        if tipo == "memo":
            memos.append(archivo)
        elif tipo == "orden_pago":
            ordenes.append(archivo)
        else:
            alertas_archivo.append(
                f"[{archivo.nombre}] no se pudo clasificar como Memo ni como Orden de Pago"
            )

    n_pares = min(len(memos), len(ordenes))
    for sobrante in memos[n_pares:]:
        alertas_archivo.append(f"[{sobrante.nombre}] Memo sin Orden de Pago para emparejar")
    for sobrante in ordenes[n_pares:]:
        alertas_archivo.append(f"[{sobrante.nombre}] Orden de Pago sin Memo para emparejar")

    reportes = []
    for archivo_memo, archivo_orden in zip(memos, ordenes):
        resultado_memo = leer_memo(archivo_memo.nombre, archivo_memo.datos)
        resultado_orden = leer_orden_pago(archivo_orden.nombre, archivo_orden.datos)

        if resultado_memo.error:
            alertas_archivo.append(f"[{archivo_memo.nombre}] {resultado_memo.error}")
            continue
        if resultado_orden.error:
            alertas_archivo.append(f"[{archivo_orden.nombre}] {resultado_orden.error}")
            continue

        reportes.append(comparar(resultado_memo, resultado_orden))

    return templates.TemplateResponse(
        request,
        "validar_planillas/resultado.html",
        {
            "activo": "validar_planillas",
            "reportes": reportes,
            "alertas_archivo": alertas_archivo,
        },
    )
