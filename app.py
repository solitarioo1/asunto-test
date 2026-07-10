import io
import re
import zipfile

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from pypdf import PdfReader

app = FastAPI()

PATRONES = {
    'siniestro':    r'Siniestro:\s*(\d+)',
    'personas':     r'N[uú]mero de personas:\s*(\d+)',
    'monto':        r'Monto de la indemnizaci[oó]n de esta planilla:\s*S/\s*([\d,]+\.\d{2})',
    'cultivos':     r'Cultivos indemnizados:\s*(.+?)\.',
    'departamento': r'Departamento:\s*(.+?)\.',
    'provincia':    r'Provincia:\s*(.+?)\.',
    'poliza':       r'P[oó]liza:\s*(\d+)',
    'campania':     r'Catastr[oó]fico\s+(\d{4}-\d{4})',
    'mem':          r'MEMOR[AÁ]NDUM\s+Seg\.Rurales-(\d+-\d{4})',
    'planilla':     r'Planilla\s+(\d+)\s+del\s+Siniestro',
}

CAMPOS_OBLIGATORIOS = ['siniestro', 'departamento', 'campania', 'personas', 'monto']
CAMPOS_NOTA = ['mem', 'planilla']

COLOR_NOTA_GRIS = "#BFBFBF"

PAGINA_BASE = """<!doctype html>
<html><head><meta charset="utf-8">
<title>Generador de correos - memorandums</title>
<style>
:root{{
  --naranja:#EE7B3D;
  --naranja-suave:#FBEADD;
  --cyan:#3EC6C6;
  --cyan-suave:#DEF6F5;
  --negro:#222222;
  --gris:#8B8B8B;
  --gris-oscuro:#4A4A4A;
  --borde:#ECECEC;
  --fondo:#F3F2F0;
  --blanco:#FFFFFF;
}}
*{{box-sizing:border-box}}
body{{font-family:-apple-system,Segoe UI,Calibri,Arial,sans-serif;font-size:14px;
color:var(--negro);margin:0;padding:32px 16px;line-height:1.5;background:var(--fondo)}}
.tarjeta{{max-width:720px;margin:0 auto;background:var(--blanco);border-radius:16px;
box-shadow:0 1px 3px rgba(0,0,0,.06);padding:28px 32px}}
.encabezado{{display:flex;align-items:center;justify-content:space-between;
border-bottom:1px solid var(--borde);padding-bottom:16px;margin-bottom:24px}}
h2{{font-weight:700;font-size:17px;margin:0}}
label.etiqueta{{display:block;font-size:11px;font-weight:700;letter-spacing:.5px;
color:var(--gris);text-transform:uppercase;margin-bottom:8px}}
.campo-archivo{{border:1px solid var(--borde);border-radius:10px;padding:10px 14px;
background:var(--fondo);display:flex;align-items:center;gap:10px}}
input[type=file]{{flex:1;border:none;background:transparent;font-size:13px}}
form{{display:flex;flex-direction:column;gap:8px;margin-bottom:8px}}
.pie-form{{display:flex;align-items:center;justify-content:space-between;
margin-top:18px;padding-top:16px;border-top:1px solid var(--borde)}}
.nota-pie{{color:var(--gris);font-size:12px}}
button{{background:var(--naranja);color:var(--blanco);border:none;border-radius:8px;
padding:11px 22px;font-weight:700;font-size:13px;cursor:pointer}}
button:hover{{opacity:.92}}
.btn-secundario{{display:inline-block;background:var(--blanco);color:var(--gris-oscuro);
border:1px solid var(--borde);border-radius:8px;padding:9px 16px;text-decoration:none;
font-weight:700;font-size:13px;margin-top:20px}}
.btn-secundario:hover{{background:var(--naranja-suave);border-color:var(--naranja)}}
.resumen{{color:var(--gris-oscuro);margin-bottom:20px;background:var(--cyan-suave);
border:1px solid var(--cyan);border-radius:10px;padding:12px 16px;font-size:13px}}
.bloque{{padding:16px 20px;margin-bottom:16px;border:1px solid var(--borde);
border-radius:10px;background:var(--blanco)}}
.bloque p{{margin:0 0 10px 0}}
.bloque b{{color:var(--negro)}}
.alerta{{color:var(--negro);background:var(--naranja-suave);border:1px solid var(--naranja);
border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:13px}}
.aviso{{color:var(--gris);font-size:12px;margin:-8px 0 24px}}
</style></head><body>
<div class="tarjeta">
<div class="encabezado"><h2>Generador de Asunto + Cuerpo</h2></div>
<form method="post" action="/procesar" enctype="multipart/form-data">
  <label class="etiqueta">Archivo ZIP con los PDF</label>
  <div class="campo-archivo">
    <input type="file" name="archivo_zip" accept=".zip" required>
  </div>
  <div class="pie-form">
    <span class="nota-pie">Los PDF no se almacenan: se procesan en memoria y se descartan.</span>
    <button type="submit">Generar</button>
  </div>
</form>
{contenido}
</div>
</body></html>"""


def extraer_campos(texto: str) -> dict:
    campos = {}
    for nombre, patron in PATRONES.items():
        m = re.search(patron, texto)
        campos[nombre] = m.group(1).strip() if m else None
    return campos


def armar_asunto(campos: dict) -> str:
    return (f"SINIESTRO {campos['siniestro']} - "
            f"{campos['departamento'].upper()} {campos['campania']} / "
            f"{campos['personas']} p")


def armar_bloque_html(campos: dict) -> str:
    asunto = armar_asunto(campos)
    nota_html = ""
    if all(campos.get(k) for k in CAMPOS_NOTA):
        nota_html = (f"<br><br><i style='color:{COLOR_NOTA_GRIS}'>Nota interna: "
                     f"MEM ({campos['mem']}) - Planilla {campos['planilla']}</i>")
    return (
        f"<div class='bloque'>"
        f"<p><b>{asunto}</b></p>"
        f"<p>Estimada Catherine buen día,<br><br>"
        f"Envío adjunto el archivo para que por favor generen la planilla respectiva.<br><br>"
        f"El monto es de S/ <b>{campos['monto']}</b>{nota_html}</p>"
        f"</div>"
    )


@app.get("/", response_class=HTMLResponse)
async def index():
    return PAGINA_BASE.format(contenido="")


@app.post("/procesar", response_class=HTMLResponse)
async def procesar(archivo_zip: UploadFile = File(...)):
    contenido_zip = await archivo_zip.read()

    with zipfile.ZipFile(io.BytesIO(contenido_zip)) as zf:
        nombres_pdf = sorted(
            n for n in zf.namelist()
            if n.lower().endswith(".pdf") and not n.startswith("__MACOSX/")
        )

        bloques = []
        n_revisar = 0
        n_error = 0

        for nombre in nombres_pdf:
            try:
                datos_pdf = zf.read(nombre)
                reader = PdfReader(io.BytesIO(datos_pdf))
                if len(reader.pages) == 0:
                    n_error += 1
                    bloques.append(f"<p class='alerta'>[ERROR {nombre}: 0 páginas]</p>")
                    continue

                texto = reader.pages[0].extract_text()
                campos = extraer_campos(texto)
                faltantes = [k for k in CAMPOS_OBLIGATORIOS if not campos.get(k)]

                if faltantes:
                    n_revisar += 1
                    bloques.append(
                        f"<p class='alerta'>[REVISAR {nombre}: faltan {faltantes}]</p>"
                    )
                    continue

                bloques.append(armar_bloque_html(campos))
            except Exception as e:
                n_error += 1
                bloques.append(f"<p class='alerta'>[ERROR {nombre}: {e}]</p>")

    resumen = (
        f"<p class='resumen'>PDFs procesados: {len(nombres_pdf)} | "
        f"Con campos faltantes: {n_revisar} | Con error: {n_error} | "
        f"OK: {len(nombres_pdf) - n_revisar - n_error}</p>"
    )
    boton_refrescar = '<a class="btn-secundario" href="/">&larr; Subir otro zip</a>'
    contenido = resumen + "\n".join(bloques) + boton_refrescar
    return PAGINA_BASE.format(contenido=contenido)
