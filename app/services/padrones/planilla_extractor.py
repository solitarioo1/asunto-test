import io
import re
from dataclasses import dataclass, field

import openpyxl

PATRON_NOMBRE = re.compile(
    r"^([A-Z]+-\d+)_Planilla_\d+_([A-Za-z]+)_\d{4}-\d{4}\.xlsx$", re.IGNORECASE
)

FILA_TOTAL = 2
FILA_INICIO_DATOS = 5

COL_CODIGO_AVISO = 2   # [1] 0-based
COL_PROVINCIA = 6      # [5] 0-based
COL_MONTO = 10         # [9] 0-based
COL_FECHA_ABONO = 16   # [15] 0-based

COL_TOTAL_PERSONAS = 8   # aprox H, 0-based [7]
COL_TOTAL_MONTO = 9      # aprox I/J, 0-based [8]/[9]


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
    except Exception as e:
        resultado.error = f"no se pudo abrir el Excel: {e}"
        return resultado

    fila_total = list(ws.iter_rows(min_row=FILA_TOTAL, max_row=FILA_TOTAL))
    if fila_total:
        celdas = fila_total[0]
        resultado.total_declarado_personas = _num(celdas[COL_TOTAL_PERSONAS - 1].value if len(celdas) >= COL_TOTAL_PERSONAS else None)
        resultado.total_declarado_monto = _num(celdas[COL_TOTAL_MONTO - 1].value if len(celdas) >= COL_TOTAL_MONTO else None)

    for fila in ws.iter_rows(min_row=FILA_INICIO_DATOS):
        codigo_aviso = fila[COL_CODIGO_AVISO - 1].value if len(fila) >= COL_CODIGO_AVISO else None
        if codigo_aviso in (None, ""):
            continue

        provincia = fila[COL_PROVINCIA - 1].value if len(fila) >= COL_PROVINCIA else None
        monto = _num(fila[COL_MONTO - 1].value if len(fila) >= COL_MONTO else None)
        fecha = fila[COL_FECHA_ABONO - 1].value if len(fila) >= COL_FECHA_ABONO else None

        if provincia is None:
            continue
        provincia = str(provincia).strip()

        grupo = resultado.grupos_provincia.setdefault(provincia, GrupoProvincia(provincia))
        grupo.n_beneficiarios += 1
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
