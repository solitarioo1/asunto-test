import datetime
from dataclasses import dataclass, field

from app.services.padrones.planilla_extractor import ResultadoPlanilla

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "setiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _fmt_fecha(fecha) -> str:
    if isinstance(fecha, (datetime.date, datetime.datetime)):
        return f"{fecha.day} de {MESES_ES.get(fecha.month, fecha.month)}"
    if fecha in (None, ""):
        return "[FECHA NO ENCONTRADA]"
    return str(fecha)


@dataclass
class Bullet:
    codigo: str
    provincia: str
    monto: float
    n_productores: int


@dataclass
class CorreoDepartamento:
    departamento: str
    bullets: list = field(default_factory=list)
    archivos: list = field(default_factory=list)
    fecha: object = None
    texto: str | None = None


@dataclass
class GrupoObservado:
    departamento: str
    motivo: str
    detalle: list = field(default_factory=list)


def _fmt_monto(monto: float) -> str:
    return f"S/ {monto:,.2f}"


def _texto_correo(grupo: CorreoDepartamento) -> str:
    total_personas = sum(b.n_productores for b in grupo.bullets)
    total_monto = sum(b.monto for b in grupo.bullets)

    fecha_fmt = _fmt_fecha(grupo.fecha)
    if total_personas == 1:
        linea_personas = (
            f"De manera atenta, envío adjunta la relación de 1 persona, cuyo pago fue "
            f"realizado el {fecha_fmt}."
        )
    else:
        linea_personas = (
            f"De manera atenta, envío adjunta la relación de {total_personas} personas, "
            f"cuyos pagos fueron realizados el {fecha_fmt}."
        )

    lineas_bullets = []
    for b in grupo.bullets:
        etiqueta = "productor" if b.n_productores == 1 else "productores"
        lineas_bullets.append(
            f"- {b.codigo}: {_fmt_monto(b.monto)} – ({b.n_productores} {etiqueta}) – "
            f"Provincia: {b.provincia}."
        )

    return (
        "Buenos días, estimado(a) Ing. [NOMBRE],\n\n"
        f"{linea_personas}\n\n"
        f"El monto total de este envío asciende a {_fmt_monto(total_monto)}\n\n"
        + "\n".join(lineas_bullets)
    )


def armar_correos(planillas: list[ResultadoPlanilla]) -> dict:
    """Agrupa resultados de planillas por departamento (preservando el orden de carga)
    y arma el texto de correo por grupo, separando los que tienen alertas."""
    alertas_archivo = []
    grupos: dict[str, CorreoDepartamento] = {}
    orden_departamentos: list[str] = []

    for planilla in planillas:
        if planilla.error:
            alertas_archivo.append(f"[{planilla.nombre_archivo}] {planilla.error}")
            continue

        if planilla.alerta_descuadre:
            alertas_archivo.append(f"[{planilla.nombre_archivo}] descuadre: {planilla.alerta_descuadre}")

        depto = planilla.departamento
        if depto not in grupos:
            grupos[depto] = CorreoDepartamento(departamento=depto)
            orden_departamentos.append(depto)

        grupo = grupos[depto]
        grupo.archivos.append(planilla.nombre_archivo)
        for provincia, g in planilla.grupos_provincia.items():
            grupo.bullets.append(Bullet(planilla.codigo_planilla, provincia, g.monto, g.n_beneficiarios))

        for fecha in planilla.fechas:
            if grupo.fecha is None:
                grupo.fecha = fecha
            elif grupo.fecha != fecha:
                grupo.fecha = "__MULTIPLE__"

    correos_listos = []
    grupos_con_alerta = []

    for depto in orden_departamentos:
        grupo = grupos[depto]

        if grupo.fecha == "__MULTIPLE__":
            detalle = []
            for planilla in planillas:
                if planilla.departamento == depto and not planilla.error:
                    detalle.append(f"{planilla.nombre_archivo}: {', '.join(str(f) for f in planilla.fechas)}")
            grupos_con_alerta.append(GrupoObservado(
                departamento=depto,
                motivo="fechas de abono distintas entre archivos del mismo departamento",
                detalle=detalle,
            ))
            continue

        if any(a.startswith(f"[{nombre}]") for nombre in grupo.archivos for a in alertas_archivo):
            grupos_con_alerta.append(GrupoObservado(
                departamento=depto,
                motivo="uno o más archivos de este departamento tienen descuadre de monto/personas",
                detalle=[a for a in alertas_archivo if any(a.startswith(f"[{n}]") for n in grupo.archivos)],
            ))
            continue

        grupo.texto = _texto_correo(grupo)
        correos_listos.append(grupo)

    return {
        "correos_listos": correos_listos,
        "grupos_con_alerta": grupos_con_alerta,
        "alertas_archivo": alertas_archivo,
    }
