import io
import re
import zipfile
from dataclasses import dataclass

from app.services.validar_planillas.xls_reader import abrir_libro

FIRMA_ZIP = b"PK\x03\x04"


def es_zip_real(datos: bytes) -> bool:
    return datos[:4] == FIRMA_ZIP


def es_xls_real(datos: bytes) -> bool:
    try:
        abrir_libro(datos)
        return True
    except Exception:
        return False


@dataclass
class ArchivoRecolectado:
    nombre: str
    datos: bytes | None
    valido: bool
    motivo: str | None = None


def _procesar_zip(datos_zip: bytes) -> list[ArchivoRecolectado]:
    resultado = []
    with zipfile.ZipFile(io.BytesIO(datos_zip)) as zf:
        nombres = sorted(
            n for n in zf.namelist()
            if not n.endswith("/") and not n.startswith("__MACOSX/")
        )
        for nombre in nombres:
            datos = zf.read(nombre)
            if es_xls_real(datos):
                resultado.append(ArchivoRecolectado(nombre, datos, True))
            else:
                resultado.append(ArchivoRecolectado(
                    nombre, None, False,
                    "no es un .xls válido (el contenido no se pudo abrir con xlrd)",
                ))
    return resultado


def recolectar_xls(archivos: list[tuple[str, bytes]]) -> list[ArchivoRecolectado]:
    """Recibe pares (nombre, bytes) tal como llegan del formulario (sueltos, de una
    carpeta, o de un ZIP) y devuelve la lista de .xls válidos, descartando por
    contenido real cualquier archivo cuya extensión no coincida con sus bytes."""
    resultado = []
    for nombre, datos in archivos:
        if not datos:
            resultado.append(ArchivoRecolectado(nombre, None, False, "archivo vacío"))
        elif es_xls_real(datos):
            resultado.append(ArchivoRecolectado(nombre, datos, True))
        elif es_zip_real(datos):
            try:
                resultado.extend(_procesar_zip(datos))
            except zipfile.BadZipFile:
                resultado.append(ArchivoRecolectado(nombre, None, False, "ZIP corrupto o inválido"))
        else:
            resultado.append(ArchivoRecolectado(
                nombre, None, False,
                "no es un .xls ni un ZIP válido (la extensión no coincide con el contenido real)",
            ))
    return resultado


PATRON_MEMO = re.compile(r"memo", re.IGNORECASE)
PATRON_SINIESTRO = re.compile(r"siniestro", re.IGNORECASE)
PATRON_ORDEN_PAGO = re.compile(r"^\d+$")


def clasificar(nombre: str) -> str:
    """Devuelve 'memo', 'orden_pago' o 'desconocido' según el nombre de archivo."""
    stem = nombre.rsplit(".", 1)[0].strip()
    if PATRON_MEMO.search(stem) and PATRON_SINIESTRO.search(stem):
        return "memo"
    if PATRON_ORDEN_PAGO.match(stem):
        return "orden_pago"
    return "desconocido"
