import io
import zipfile
from dataclasses import dataclass

import openpyxl

FIRMA_ZIP = b"PK\x03\x04"


def es_zip_real(datos: bytes) -> bool:
    return datos[:4] == FIRMA_ZIP


def es_xlsx_real(datos: bytes) -> bool:
    if not es_zip_real(datos):
        return False
    try:
        openpyxl.load_workbook(io.BytesIO(datos), data_only=True, read_only=True)
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
            if es_xlsx_real(datos):
                resultado.append(ArchivoRecolectado(nombre, datos, True))
            else:
                resultado.append(ArchivoRecolectado(
                    nombre, None, False,
                    "no es un Excel válido (el contenido no se pudo abrir como .xlsx)",
                ))
    return resultado


def recolectar_excels(archivos: list[tuple[str, bytes]]) -> list[ArchivoRecolectado]:
    """Recibe pares (nombre, bytes) tal como llegan del formulario (sueltos, de una
    carpeta, o de un ZIP) y devuelve la lista de Excels válidos, descartando por
    contenido real cualquier archivo cuya extensión no coincida con sus bytes."""
    resultado = []
    for nombre, datos in archivos:
        if not datos:
            resultado.append(ArchivoRecolectado(nombre, None, False, "archivo vacío"))
        elif es_xlsx_real(datos):
            # .xlsx es en sí un contenedor ZIP: se prueba primero como workbook.
            resultado.append(ArchivoRecolectado(nombre, datos, True))
        elif es_zip_real(datos):
            try:
                resultado.extend(_procesar_zip(datos))
            except zipfile.BadZipFile:
                resultado.append(ArchivoRecolectado(nombre, None, False, "ZIP corrupto o inválido"))
        else:
            resultado.append(ArchivoRecolectado(
                nombre, None, False,
                "no es un Excel ni un ZIP válido (la extensión no coincide con el contenido real)",
            ))
    return resultado
