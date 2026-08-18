from dataclasses import dataclass, field

from app.services.validar_planillas.normalizador import normalizar_nombre
from app.services.validar_planillas.xls_reader import abrir_libro, hoja_por_nombre

HOJA_MEMO = "SINIESTRO"

# columnas 1-based del spec -> índice 0-based para xlrd
COL_NOMBRE = 1
COL_DNI = 3
COL_MONTO = 19

FILA_INICIO_DATOS = 1  # fila 2 (1-based); fila 0 es encabezado


@dataclass
class PersonaMemo:
    nombre_original: str
    dni: str
    monto: float


@dataclass
class ResultadoMemo:
    nombre_archivo: str
    personas: dict = field(default_factory=dict)  # nombre_normalizado -> PersonaMemo (monto acumulado)
    error: str | None = None

    @property
    def n_personas(self) -> int:
        return len(self.personas)

    @property
    def monto_total(self) -> float:
        return sum(p.monto for p in self.personas.values())


def leer_memo(nombre: str, datos: bytes) -> ResultadoMemo:
    resultado = ResultadoMemo(nombre_archivo=nombre)

    try:
        libro = abrir_libro(datos)
        hoja = hoja_por_nombre(libro, HOJA_MEMO)
    except Exception as e:
        resultado.error = f"no se pudo abrir el Memo: {e}"
        return resultado

    for fila_idx in range(FILA_INICIO_DATOS, hoja.nrows):
        fila = hoja.row_values(fila_idx)
        if len(fila) <= COL_NOMBRE or not str(fila[COL_NOMBRE]).strip():
            continue

        nombre_persona = str(fila[COL_NOMBRE]).strip()
        dni = str(fila[COL_DNI]).strip() if len(fila) > COL_DNI else ""
        monto = _num(fila[COL_MONTO]) if len(fila) > COL_MONTO else 0.0

        clave = normalizar_nombre(nombre_persona)
        if clave in resultado.personas:
            resultado.personas[clave].monto += monto or 0.0
        else:
            resultado.personas[clave] = PersonaMemo(nombre_persona, dni, monto or 0.0)

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
