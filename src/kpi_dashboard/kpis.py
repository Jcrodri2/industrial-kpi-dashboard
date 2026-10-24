"""Indicadores de producción por pozo y del campo."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from .synthetic import DailyRecord


@dataclass(frozen=True)
class WellKpi:
    """KPIs de un pozo en el periodo."""

    well: str
    oil_total_bbl: float
    oil_avg_bopd: float
    water_cut: float
    uptime_pct: float
    decline_pct_month: float | None


@dataclass(frozen=True)
class FieldKpi:
    """KPIs del campo completo en el periodo."""

    days: int
    wells: int
    oil_total_bbl: float
    oil_avg_bopd: float
    water_cut: float
    uptime_pct: float


def water_cut(oil: float, water: float) -> float:
    """Fracción de agua en el líquido producido: agua / (petróleo + agua)."""
    liquid = oil + water
    return water / liquid if liquid > 0 else 0.0


def monthly_decline(points: Sequence[tuple[int, float]]) -> float | None:
    """Declinación mensual en % con un ajuste exponencial por mínimos cuadrados.

    `points` son pares (día, tasa). Ajusta ln(tasa) = a - b·día y devuelve
    (1 - e^(-30·b))·100. Devuelve None si no hay al menos dos días distintos con tasa
    positiva.
    """
    usable = [(day, math.log(rate)) for day, rate in points if rate > 0]
    if len(usable) < 2:
        return None
    n = len(usable)
    mean_x = sum(x for x, _ in usable) / n
    mean_y = sum(y for _, y in usable) / n
    sxx = sum((x - mean_x) ** 2 for x, _ in usable)
    if sxx == 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in usable) / sxx
    return (1 - math.exp(30 * slope)) * 100


def well_kpis(records: Iterable[DailyRecord]) -> list[WellKpi]:
    """KPIs por pozo, de mayor a menor producción acumulada.

    La declinación usa solo los días con 24 horas en operación, para que las paradas
    no se confundan con caída del yacimiento.
    """
    by_well: dict[str, list[DailyRecord]] = defaultdict(list)
    for r in records:
        by_well[r.well].append(r)

    result: list[WellKpi] = []
    for well, rows in by_well.items():
        rows.sort(key=lambda r: r.date)
        oil = sum(r.oil_bopd for r in rows)
        water = sum(r.water_bwpd for r in rows)
        hours = sum(r.uptime_h for r in rows)
        first_day = rows[0].date
        full_days = [((r.date - first_day).days, r.oil_bopd) for r in rows if r.uptime_h == 24]
        result.append(
            WellKpi(
                well=well,
                oil_total_bbl=oil,
                oil_avg_bopd=oil / len(rows),
                water_cut=water_cut(oil, water),
                uptime_pct=hours / (24 * len(rows)) * 100,
                decline_pct_month=monthly_decline(full_days),
            )
        )
    return sorted(result, key=lambda k: k.oil_total_bbl, reverse=True)


def field_daily_oil(records: Iterable[DailyRecord]) -> list[tuple[date, float]]:
    """Producción diaria de petróleo del campo: la suma de todos los pozos por día."""
    totals: dict[date, float] = defaultdict(float)
    for r in records:
        totals[r.date] += r.oil_bopd
    return sorted(totals.items())


def field_kpis(records: Iterable[DailyRecord]) -> FieldKpi:
    """KPIs del campo completo."""
    rows = list(records)
    if not rows:
        raise ValueError("no hay registros")
    days = len({r.date for r in rows})
    oil = sum(r.oil_bopd for r in rows)
    water = sum(r.water_bwpd for r in rows)
    hours = sum(r.uptime_h for r in rows)
    return FieldKpi(
        days=days,
        wells=len({r.well for r in rows}),
        oil_total_bbl=oil,
        oil_avg_bopd=oil / days,
        water_cut=water_cut(oil, water),
        uptime_pct=hours / (24 * len(rows)) * 100,
    )
