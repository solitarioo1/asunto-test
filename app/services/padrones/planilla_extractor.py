import datetime
import io
import re
from dataclasses import dataclass, field

import openpyxl

PATRON_NOMBRE = re.compile(
    r"^([A-Z]+-\d+)[\s_]+Planilla[\s_]+\d+[\s_]+(.+?)[\s_]+\d{4}-\d{4}\.xlsx$",
    re.IGNORECASE,
)

MAX_FILAS_BUSQUEDA_ENCABEZADO = 15
PATRON_BENEFICIARIOS = re.compile(r"(\d+)\s*BENEFICIARIO", re.IGNORECASE)


@dataclass
class GrupoProvincia:
    provincia: str
    n_beneficiarios: int = 0
    monto: float = 0.0


@dataclass
class ResultadoPlanilla:
    nombre_archivo: str
    codigo_planilla: str | None = None
    departamento: str | None = None
    grupos_provincia: dict = field(default_factory=dict)  # provincia -> GrupoProvincia
    fechas: set = field(default_factory=set)
    total_declarado_personas: float | None = None
    total_declarado_monto: float | None = None
    error: str | None = None
    alerta_descuadre: str | None = None

    @property
    def total_calculado_personas(self) -> int:
        return sum(g.n_beneficiarios for g in self.grupos_provincia.values())

    @property
    def total_calculado_monto(self) -> float:
        return sum(g.monto for g in self.grupos_provincia.values())


def parse_nombre_archivo(nombre: str) -> tuple[str, str] | None:
    m = PATRON_NOMBRE.match(nombre.strip())
    if not m:
        return None
    return m.group(1).upper(), m.group(2)


def _encontrar_columna(encabezados: list[str], *fragmentos: str) -> int | None:
    """Devuelve el índice (0-based) del primer encabezado que contenga alguno
    de los fragmentos dados (comparación insensible a mayúsculas)."""
    for idx, texto in enumerate(encabezados):
        texto_norm = texto.upper()
        if any(frag in texto_norm for frag in fragmentos):
            return idx
    return None


def _encontrar_fila_encabezado(filas: list[tuple]) -> int | None:
    """Busca, entre las primeras filas, la fila de encabezados reconociendo la
    columna 'PROVINCIA' (presente tanto en planillas detalladas como en
    resúmenes/tablas dinámicas por departamento)."""
    limite = min(len(filas), MAX_FILAS_BUSQUEDA_ENCABEZADO)
    for idx in range(limite):
        celdas = [str(v).strip().upper() if v is not None else "" for v in filas[idx]]
        if "PROVINCIA" in celdas:
            return idx
    return None


def _primera_fecha(filas: list[tuple]) -> object | None:
    for fila in filas:
        for valor in fila:
            if isinstance(valor, (datetime.date, datetime.datetime)):
                return valor
    return None


def _fila_total_declarado(filas: list[tuple]) -> tuple[float | None, float | None]:
    """Busca una fila con la etiqueta 'TOTAL' y extrae de ahí la cantidad de
    beneficiarios declarada (ej. '6 BENEFICIARIOS') y el monto total (la
    última celda numérica de esa fila)."""
    for fila in filas:
        celdas = list(fila)
        if not any(str(v).strip().upper() == "TOTAL" for v in celdas if v is not None):
            continue

        personas = None
        monto = None
        for valor in celdas:
            m = PATRON_BENEFICIARIOS.search(str(valor)) if valor is not None else None
            if m:
                personas = float(m.group(1))
            if isinstance(valor, (int, float)):
                monto = float(valor)
        return personas, monto
    return None, None


def leer_planilla(nombre: str, datos: bytes) -> ResultadoPlanilla:
    resultado = ResultadoPlanilla(nombre_archivo=nombre)

    parseo = parse_nombre_archivo(nombre)
    if not parseo:
        resultado.error = (
            "el nombre de archivo no calza con el patrón "
            "{COD}-{NUM}_Planilla_{ID}_{DEPARTAMENTO}_2025-2026.xlsx"
        )
        return resultado
    resultado.codigo_planilla, resultado.departamento = parseo

    try:
        wb = openpyxl.load_workbook(io.BytesIO(datos), data_only=True, read_only=True)
        ws = wb.active
        filas = list(ws.iter_rows(values_only=True))
    except Exception as e:
        resultado.error = f"no se pudo abrir el Excel: {e}"
        return resultado

    idx_encabezado = _encontrar_fila_encabezado(filas)
    if idx_encabezado is None:
        resultado.error = "no se encontró la columna 'PROVINCIA' en el Excel"
        return resultado

    encabezados = [str(v).strip().upper() if v is not None else "" for v in filas[idx_encabezado]]
    col_provincia = _encontrar_columna(encabezados, "PROVINCIA")
    col_monto = _encontrar_columna(encabezados, "MONTO")
    col_fecha = _encontrar_columna(encabezados, "FECHA")
    col_cuenta = _encontrar_columna(encabezados, "CUENTA DE")

    # Detalle (una fila = una persona, ej. Puno) vs. resumen/tabla dinámica
    # (una fila = un grupo ya agregado con conteo y suma, ej. Huancavelica).
    es_detalle = any(
        "NOMBRES" in enc or "DNI" in enc or "CÓDIGO DE AVISO" in enc or "CODIGO DE AVISO" in enc
        for enc in encabezados
    )

    filas_previas = filas[:idx_encabezado]
    fecha_fallback = None if col_fecha is not None else _primera_fecha(filas_previas)
    resultado.total_declarado_personas, resultado.total_declarado_monto = _fila_total_declarado(filas_previas)

    for fila in filas[idx_encabezado + 1:]:
        provincia = fila[col_provincia] if col_provincia is not None and col_provincia < len(fila) else None
        if provincia in (None, ""):
            continue
        provincia = str(provincia).strip()

        monto = _num(fila[col_monto]) if col_monto is not None and col_monto < len(fila) else None

        if es_detalle:
            n_beneficiarios = 1
        else:
            crudo = fila[col_cuenta] if col_cuenta is not None and col_cuenta < len(fila) else None
            n_beneficiarios = int(_num(crudo) or 1)

        if col_fecha is not None and col_fecha < len(fila):
            fecha = fila[col_fecha]
        else:
            fecha = fecha_fallback

        grupo = resultado.grupos_provincia.setdefault(provincia, GrupoProvincia(provincia))
        grupo.n_beneficiarios += n_beneficiarios
        grupo.monto += monto or 0.0

        if fecha not in (None, ""):
            resultado.fechas.add(fecha)

    if (
        resultado.total_declarado_personas is not None
        and resultado.total_calculado_personas != resultado.total_declarado_personas
    ) or (
        resultado.total_declarado_monto is not None
        and round(resultado.total_calculado_monto, 2) != round(resultado.total_declarado_monto, 2)
    ):
        declarado_personas = resultado.total_declarado_personas
        if declarado_personas is not None and declarado_personas == int(declarado_personas):
            declarado_personas = int(declarado_personas)
        resultado.alerta_descuadre = (
            f"calculado: {resultado.total_calculado_personas} personas / "
            f"S/ {resultado.total_calculado_monto:,.2f} — "
            f"declarado en TOTAL: {declarado_personas} personas / "
            f"S/ {(resultado.total_declarado_monto or 0):,.2f}"
        )

    return resultado


def _num(valor) -> float | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        return float(str(valor).replace(",", "").replace("S/", "").strip())
    except ValueError:
        return None
