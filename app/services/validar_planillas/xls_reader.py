import csv
import io
from html.parser import HTMLParser

import xlrd


class _HojaSimulada:
    """Envoltorio con la misma interfaz mínima que usa el resto del código
    sobre una hoja de xlrd (nrows / row_values), para tablas que en realidad
    llegaron como HTML o CSV disfrazados de .xls."""

    def __init__(self, filas: list[list[str]]):
        self._filas = filas

    @property
    def nrows(self) -> int:
        return len(self._filas)

    def row_values(self, idx: int) -> list[str]:
        return self._filas[idx]


class _LibroSimulado:
    def __init__(self, filas: list[list[str]], nombre_hoja: str = "Hoja1"):
        self._hojas = {nombre_hoja: _HojaSimulada(filas)}

    def sheet_names(self) -> list[str]:
        return list(self._hojas.keys())

    def sheet_by_name(self, nombre: str):
        try:
            return self._hojas[nombre]
        except KeyError:
            raise xlrd.XLRDError(f"no existe la hoja '{nombre}'")


class _ParserTablaHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.filas: list[list[str]] = []
        self._fila: list[str] | None = None
        self._celda: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._fila = []
        elif tag in ("td", "th") and self._fila is not None:
            self._celda = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._celda is not None:
            self._fila.append("".join(self._celda).strip())
            self._celda = None
        elif tag == "tr" and self._fila is not None:
            self.filas.append(self._fila)
            self._fila = None

    def handle_data(self, data):
        if self._celda is not None:
            self._celda.append(data)


def _parece_html(datos: bytes) -> bool:
    inicio = datos[:1024].lstrip().lower()
    return inicio.startswith(b"<html") or inicio.startswith(b"<!doctype") or b"<table" in inicio


def _parece_texto(datos: bytes) -> bool:
    muestra = datos[:2048]
    if b"\x00" in muestra or not muestra:
        return False
    no_imprimibles = sum(1 for b in muestra if b < 9 or 13 < b < 32)
    return no_imprimibles / len(muestra) < 0.05


def _abrir_como_html(datos: bytes) -> _LibroSimulado:
    parser = _ParserTablaHTML()
    parser.feed(datos.decode("utf-8", errors="replace"))
    filas = [f for f in parser.filas if any(c.strip() for c in f)]
    if not filas:
        raise ValueError("no se encontró ninguna tabla HTML con filas")
    return _LibroSimulado(filas)


def _abrir_como_csv(datos: bytes) -> _LibroSimulado:
    texto = datos.decode("utf-8-sig", errors="replace")
    dialecto = csv.Sniffer().sniff(texto[:2048], delimiters=",;\t")
    filas = [f for f in csv.reader(io.StringIO(texto), dialect=dialecto) if any(c.strip() for c in f)]
    if not filas:
        raise ValueError("no se encontró contenido tabular")
    return _LibroSimulado(filas)


def abrir_libro(datos: bytes):
    """Abre un .xls real (xlrd). Si no lo es, intenta reconocer los formatos
    con los que suelen exportar 'Excel' los sistemas de seguros/gobierno:
    una tabla HTML o un CSV/TSV, ambos guardados con extensión .xls."""
    try:
        return xlrd.open_workbook(file_contents=datos)
    except Exception as error_xls:
        if _parece_html(datos):
            try:
                return _abrir_como_html(datos)
            except Exception:
                pass
        if _parece_texto(datos):
            try:
                return _abrir_como_csv(datos)
            except Exception:
                pass
        raise error_xls


def hoja_por_nombre(libro, nombre: str):
    try:
        return libro.sheet_by_name(nombre)
    except xlrd.XLRDError:
        pass
    nombres = libro.sheet_names()
    for nombre_hoja in nombres:
        if nombre_hoja.strip().lower() == nombre.strip().lower():
            return libro.sheet_by_name(nombre_hoja)
    if len(nombres) == 1:
        # HTML/CSV disfrazado de .xls: una sola hoja, con nombre distinto al esperado.
        return libro.sheet_by_name(nombres[0])
    raise xlrd.XLRDError(f"no se encontró la hoja '{nombre}' (hojas disponibles: {nombres})")
