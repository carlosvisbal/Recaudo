"""Cálculo de tramos de cobro: un solo pago, cada mes o cada quincena."""

from __future__ import annotations

import calendar
from datetime import date

MESES_ES = (
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def rango_cobro(
    cobro_cada: str,
    ref: date | None = None,
    *,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
) -> tuple[date, date]:
    """Devuelve (inicio, fin) inclusive del tramo vigente."""
    ref = ref or date.today()
    if cobro_cada == "una_vez":
        inicio = fecha_inicio or date(1970, 1, 1)
        fin = fecha_fin or date(9999, 12, 31)
        return inicio, fin
    if cobro_cada == "quincena":
        if ref.day <= 15:
            return ref.replace(day=1), ref.replace(day=15)
        ultimo = calendar.monthrange(ref.year, ref.month)[1]
        return ref.replace(day=16), ref.replace(day=ultimo)
    # mes (default)
    ultimo = calendar.monthrange(ref.year, ref.month)[1]
    return ref.replace(day=1), ref.replace(day=ultimo)


def inicio_periodo(cobro_cada: str, ref: date | None = None) -> date:
    """Clave estable del período (día 1 del mes o 1/16 de quincena)."""
    inicio, _ = rango_cobro(cobro_cada, ref)
    return inicio


def etiqueta_periodo_clave(cobro_cada: str, periodo_inicio: date) -> str:
    if cobro_cada == "una_vez":
        return "Un solo pago"
    if cobro_cada == "quincena":
        mitad = "1ª quincena" if periodo_inicio.day <= 15 else "2ª quincena"
        return f"{mitad} de {MESES_ES[periodo_inicio.month]} {periodo_inicio.year}"
    return f"{MESES_ES[periodo_inicio.month].capitalize()} {periodo_inicio.year}"


def etiqueta_cobro(
    cobro_cada: str,
    ref: date | None = None,
    *,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
) -> str:
    ref = ref or date.today()
    if cobro_cada == "una_vez":
        if fecha_inicio and fecha_fin:
            return (
                f"Un solo pago "
                f"({fecha_inicio.strftime('%d/%m/%Y')} – {fecha_fin.strftime('%d/%m/%Y')})"
            )
        return "Un solo pago (toda la actividad)"
    inicio, _ = rango_cobro(cobro_cada, ref)
    return etiqueta_periodo_clave(cobro_cada, inicio)


def listar_periodos(
    cobro_cada: str,
    *,
    desde: date,
    hasta: date,
    alrededor: date | None = None,
    meses_atras: int = 14,
    meses_adelante: int = 3,
) -> list[dict]:
    """
    Lista períodos elegibles para asignar un pago (atrasados o adelantados).
    Cada item: {inicio, fin, label, value}
    """
    alrededor = alrededor or date.today()
    items: list[dict] = []

    if cobro_cada == "una_vez":
        inicio, fin = rango_cobro(
            cobro_cada, alrededor, fecha_inicio=desde, fecha_fin=hasta
        )
        items.append(
            {
                "inicio": inicio.isoformat(),
                "fin": fin.isoformat(),
                "label": "Un solo pago (toda la actividad)",
                "value": inicio.isoformat(),
            }
        )
        return items

    # Ventana: desde actividad o N meses atrás, hasta N meses adelante
    year = alrededor.year
    month = alrededor.month - meses_atras
    while month <= 0:
        month += 12
        year -= 1
    cursor = date(year, month, 1)
    end_year = alrededor.year
    end_month = alrededor.month + meses_adelante
    while end_month > 12:
        end_month -= 12
        end_year += 1
    limite = date(end_year, end_month, 1)

    # Respetar fechas de la actividad cuando existan
    if desde and cursor < date(desde.year, desde.month, 1):
        cursor = date(desde.year, desde.month, 1)
    if hasta:
        tope_act = date(hasta.year, hasta.month, 1)
        if limite > tope_act:
            limite = tope_act

    while cursor <= limite:
        if cobro_cada == "quincena":
            for day in (1, 16):
                ref = cursor.replace(day=day)
                inicio, fin = rango_cobro("quincena", ref)
                if hasta and inicio > hasta:
                    continue
                if desde and fin < desde:
                    continue
                items.append(
                    {
                        "inicio": inicio.isoformat(),
                        "fin": fin.isoformat(),
                        "label": etiqueta_periodo_clave("quincena", inicio),
                        "value": inicio.isoformat(),
                    }
                )
        else:
            inicio, fin = rango_cobro("mes", cursor)
            if not (hasta and inicio > hasta) and not (desde and fin < desde):
                items.append(
                    {
                        "inicio": inicio.isoformat(),
                        "fin": fin.isoformat(),
                        "label": etiqueta_periodo_clave("mes", inicio),
                        "value": inicio.isoformat(),
                    }
                )
        # avanzar un mes
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    items.sort(key=lambda x: x["inicio"], reverse=True)
    return items
