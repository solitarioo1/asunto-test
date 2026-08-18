import re

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
