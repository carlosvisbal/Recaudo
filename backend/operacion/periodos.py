"""Cálculo de tramos de cobro: un solo pago, cada mes o cada quincena."""

from __future__ import annotations

import calendar
from datetime import date


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
    inicio, fin = rango_cobro(cobro_cada, ref)
    if cobro_cada == "quincena":
        return f"Esta quincena ({inicio.strftime('%d/%m')} – {fin.strftime('%d/%m/%Y')})"
    return f"Este mes ({inicio.strftime('%m/%Y')})"
