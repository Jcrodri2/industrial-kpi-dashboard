"""Producción diaria sintética por pozo y su lectura y escritura en CSV.

Cada pozo arranca con una tasa inicial, declina de forma exponencial, su corte de
agua sube con el tiempo y algunos días tiene paradas parciales o totales.
"""

from __future__ import annotations

import csv
import math
import random
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

FIELDS = ("date", "well", "oil_bopd", "water_bwpd", "gas_kscfd", "uptime_h")


@dataclass(frozen=True)
class DailyRecord:
    """Producción de un pozo en un día.

    oil_bopd: barriles de petróleo por día.
    water_bwpd: barriles de agua por día.
    gas_kscfd: miles de pies cúbicos estándar de gas por día.
    uptime_h: horas en operación (0 a 24).
    """

    date: date
    well: str
    oil_bopd: float
    water_bwpd: float
    gas_kscfd: float
    uptime_h: float


def generate(
    wells: int = 12,
    days: int = 180,
    start: date = date(2026, 1, 1),
    seed: int = 42,
    downtime_probability: float = 0.06,
) -> list[DailyRecord]:
    """Genera `days` días de producción para `wells` pozos, siempre igual para la misma semilla."""
    if wells < 1:
        raise ValueError("wells debe ser al menos 1")
    if days < 1:
        raise ValueError("days debe ser al menos 1")
    if not 0 <= downtime_probability < 1:
        raise ValueError("downtime_probability debe estar entre 0 y 1")

    rng = random.Random(seed)
    records: list[DailyRecord] = []
    for index in range(1, wells + 1):
        well = f"POZO-{index:02d}"
        initial_rate = rng.uniform(150, 900)
        daily_decline = rng.uniform(0.0008, 0.003)
        initial_water_cut = rng.uniform(0.15, 0.6)
        water_cut_growth = rng.uniform(0.0003, 0.0012)
        gas_oil_ratio = rng.uniform(0.3, 1.2)
        for offset in range(days):
            uptime = 24.0
            if rng.random() < downtime_probability:
                uptime = round(rng.uniform(0, 20), 1)
            potential = initial_rate * math.exp(-daily_decline * offset)
            oil = potential * uptime / 24 * rng.uniform(0.97, 1.03)
            water_cut = min(0.95, initial_water_cut + water_cut_growth * offset)
            water = oil * water_cut / (1 - water_cut)
            records.append(
                DailyRecord(
                    date=start + timedelta(days=offset),
                    well=well,
                    oil_bopd=round(oil, 1),
                    water_bwpd=round(water, 1),
                    gas_kscfd=round(oil * gas_oil_ratio, 1),
                    uptime_h=uptime,
                )
            )
    return records


def write_csv(records: Iterable[DailyRecord], path: Path) -> None:
    """Escribe los registros en un CSV con encabezado."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        for r in records:
            writer.writerow(
                [r.date.isoformat(), r.well, r.oil_bopd, r.water_bwpd, r.gas_kscfd, r.uptime_h]
            )


def read_csv(path: Path) -> list[DailyRecord]:
    """Lee un CSV con las columnas de `FIELDS`."""
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            DailyRecord(
                date=date.fromisoformat(row["date"]),
                well=row["well"],
                oil_bopd=float(row["oil_bopd"]),
                water_bwpd=float(row["water_bwpd"]),
                gas_kscfd=float(row["gas_kscfd"]),
                uptime_h=float(row["uptime_h"]),
            )
            for row in csv.DictReader(handle)
        ]
