from dataclasses import dataclass, field

from app.services.validar_planillas.memo_extractor import ResultadoMemo
from app.services.validar_planillas.orden_pago_extractor import ResultadoOrdenPago


@dataclass
class DiscrepanciaMonto:
    nombre: str
    monto_memo: float
    monto_orden: float


@dataclass
class IncidenciaFormato:
    nombre_memo: str
    nombre_orden: str
    monto: float


@dataclass
class ReporteComparacion:
    nombre_memo: str
    nombre_orden: str
    n_personas_memo: int
    monto_total_memo: float
    n_personas_orden: int
    monto_total_orden: float
    monto_distinto: list = field(default_factory=list)
    posibles_incidencias_formato: list = field(default_factory=list)
    solo_en_memo: list = field(default_factory=list)
    solo_en_orden: list = field(default_factory=list)
    veredicto: str = "cuadra"


def comparar(memo: ResultadoMemo, orden: ResultadoOrdenPago) -> ReporteComparacion:
    reporte = ReporteComparacion(
        nombre_memo=memo.nombre_archivo,
        nombre_orden=orden.nombre_archivo,
        n_personas_memo=memo.n_personas,
        monto_total_memo=memo.monto_total,
        n_personas_orden=orden.n_personas,
        monto_total_orden=orden.monto_total,
    )

    claves_memo = set(memo.personas)
    claves_orden = set(orden.personas)

    claves_comunes = claves_memo & claves_orden
    for clave in sorted(claves_comunes):
        m = round(memo.personas[clave].monto, 2)
        o = round(orden.personas[clave].monto, 2)
        if m != o:
            reporte.monto_distinto.append(DiscrepanciaMonto(
                memo.personas[clave].nombre_original, m, o,
            ))

    pendientes_memo = {c: memo.personas[c] for c in claves_memo - claves_orden}
    pendientes_orden = {c: orden.personas[c] for c in claves_orden - claves_memo}

    # Segundo intento: emparejar por monto exactamente igual (apellido de casada,
    # tipeo, etc. — sección 5 del spec: "si el monto coincide es la misma persona").
    usados_orden = set()
    for clave_memo, persona_memo in list(pendientes_memo.items()):
        monto_memo = round(persona_memo.monto, 2)
        match = None
        for clave_orden, persona_orden in pendientes_orden.items():
            if clave_orden in usados_orden:
                continue
            if round(persona_orden.monto, 2) == monto_memo:
                match = clave_orden
                break
        if match:
            usados_orden.add(match)
            reporte.posibles_incidencias_formato.append(IncidenciaFormato(
                persona_memo.nombre_original,
                pendientes_orden[match].nombre_original,
                monto_memo,
            ))
            del pendientes_memo[clave_memo]

    for clave in usados_orden:
        del pendientes_orden[clave]

    reporte.solo_en_memo = [p.nombre_original for p in pendientes_memo.values()]
    reporte.solo_en_orden = [p.nombre_original for p in pendientes_orden.values()]

    if reporte.monto_distinto or reporte.solo_en_memo or reporte.solo_en_orden:
        reporte.veredicto = "no_cuadra"
    elif reporte.posibles_incidencias_formato:
        reporte.veredicto = "cuadra_con_observacion"
    else:
        reporte.veredicto = "cuadra"

    return reporte
