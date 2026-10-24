"""Reglas de calidad de datos para la producción diaria."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import pairwise

from .synthetic import DailyRecord


@dataclass(frozen=True)
class Issue:
    """Un problema de calidad: qué regla falló, en qué pozo y en qué fecha."""

    rule: str
    well: str
    date: date
    detail: str


def check(records: Iterable[DailyRecord]) -> list[Issue]:
    """Devuelve los problemas de calidad ordenados por pozo, fecha y regla."""
    issues: list[Issue] = []
    seen: set[tuple[str, date]] = set()
    dates_by_well: dict[str, set[date]] = defaultdict(set)

    for r in records:
        key = (r.well, r.date)
        if key in seen:
            issues.append(Issue("duplicado", r.well, r.date, "registro repetido para el mismo día"))
        seen.add(key)
        dates_by_well[r.well].add(r.date)

        negatives = [
            name
            for name, value in (
                ("petróleo", r.oil_bopd),
                ("agua", r.water_bwpd),
                ("gas", r.gas_kscfd),
            )
            if value < 0
        ]
        if negatives:
            detail = "valor negativo en " + ", ".join(negatives)
            issues.append(Issue("negativo", r.well, r.date, detail))
        if not 0 <= r.uptime_h <= 24:
            detail = f"{r.uptime_h} horas en un día"
            issues.append(Issue("horas_fuera_de_rango", r.well, r.date, detail))
        if r.uptime_h == 0 and r.oil_bopd > 0:
            detail = "reporta petróleo con 0 horas en operación"
            issues.append(Issue("produccion_sin_operacion", r.well, r.date, detail))

    for well, dates in dates_by_well.items():
        for previous, current in pairwise(sorted(dates)):
            gap = (current - previous).days - 1
            if gap > 0:
                detail = "falta 1 día" if gap == 1 else f"faltan {gap} días"
                missing_from = previous + timedelta(days=1)
                issues.append(Issue("fechas_faltantes", well, missing_from, detail))

    return sorted(issues, key=lambda i: (i.well, i.date, i.rule))
