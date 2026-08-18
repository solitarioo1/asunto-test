from dataclasses import dataclass, field

from app.services.validar_planillas.normalizador import normalizar_nombre
from app.services.validar_planillas.xls_reader import abrir_libro, hoja_por_nombre

HOJA_ORDEN_PAGO = "Hoja1"

# columnas 1-based del spec -> índice 0-based para xlrd
COL_NOMBRE_CLIENTE = 11
COL_MONTO_PAGO = 6

FILA_INICIO_DATOS = 7  # fila 8 (1-based); filas 0-6 son encabezado/metadata


@dataclass
class PersonaOrdenPago:
    nombre_original: str
    monto: float


@dataclass
class ResultadoOrdenPago:
    nombre_archivo: str
    personas: dict = field(default_factory=dict)  # nombre_normalizado -> PersonaOrdenPago
    error: str | None = None

    @property
    def n_personas(self) -> int:
        return len(self.personas)

    @property
    def monto_total(self) -> float:
        return sum(p.monto for p in self.personas.values())


def leer_orden_pago(nombre: str, datos: bytes) -> ResultadoOrdenPago:
    resultado = ResultadoOrdenPago(nombre_archivo=nombre)

    try:
        libro = abrir_libro(datos)
        hoja = hoja_por_nombre(libro, HOJA_ORDEN_PAGO)
    except Exception as e:
        resultado.error = f"no se pudo abrir la Orden de Pago: {e}"
        return resultado

    for fila_idx in range(FILA_INICIO_DATOS, hoja.nrows):
        fila = hoja.row_values(fila_idx)
        if len(fila) <= COL_NOMBRE_CLIENTE or not str(fila[COL_NOMBRE_CLIENTE]).strip():
            continue

        nombre_persona = str(fila[COL_NOMBRE_CLIENTE]).strip()
        monto = _num(fila[COL_MONTO_PAGO]) if len(fila) > COL_MONTO_PAGO else 0.0

        clave = normalizar_nombre(nombre_persona)
        if clave in resultado.personas:
            resultado.personas[clave].monto += monto or 0.0
        else:
            resultado.personas[clave] = PersonaOrdenPago(nombre_persona, monto or 0.0)

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
