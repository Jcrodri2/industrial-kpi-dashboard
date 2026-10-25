"""Tablero HTML estático: tarjetas de KPIs, gráficos SVG, tabla por pozo y calidad de datos."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date
from html import escape

from . import __version__
from .kpis import WellKpi, field_daily_oil, field_kpis, well_kpis
from .quality import Issue
from .synthetic import DailyRecord

MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
MAX_ISSUES_SHOWN = 50

STYLE = """
:root { --bg: #f6f7f9; --card: #ffffff; --ink: #1b1f24; --muted: #5b6470; --line: #dde2e8;
  --accent: #0b6bcb; --accent-soft: rgba(11, 107, 203, 0.12); --ok: #1a7f37; --warn: #b54708; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #0f1216; --card: #171b21; --ink: #e8ecf1; --muted: #9aa4b2; --line: #2a313a;
    --accent: #5aa9ff; --accent-soft: rgba(90, 169, 255, 0.16); --ok: #4ac26b; --warn: #f79009; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 980px; margin: 0 auto; padding: 32px 16px 48px; }
h1 { font-size: 26px; margin: 0; }
h2 { font-size: 16px; margin: 0 0 2px; }
header p, .sub, footer { color: var(--muted); }
header p { margin: 4px 0 0; }
.sub { font-size: 13px; margin: 0 0 12px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px;
  margin: 24px 0 8px; }
.card, section { background: var(--card); border: 1px solid var(--line); border-radius: 10px; }
.card { padding: 14px 16px; }
.card .label { color: var(--muted); font-size: 13px; }
.card .value { font-size: 24px; font-weight: 650; }
.card .unit { color: var(--muted); font-size: 13px; font-weight: 400; margin-left: 4px; }
section { padding: 18px 18px 14px; margin-top: 16px; }
.chart { overflow-x: auto; }
svg { width: 100%; min-width: 600px; height: auto; display: block; }
svg text { fill: var(--muted); font-size: 12px; }
svg .value-label { fill: var(--ink); font-weight: 600; }
svg .grid { stroke: var(--line); }
svg .line { fill: none; stroke: var(--accent); stroke-width: 2; }
svg .area { fill: var(--accent-soft); }
svg .bar { fill: var(--accent); }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 8px 6px; border-bottom: 1px solid var(--line); text-align: right;
  white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
th { color: var(--muted); font-size: 13px; font-weight: 600; }
.ok { color: var(--ok); margin: 0; }
.warn, .issues { color: var(--warn); }
footer { font-size: 13px; margin-top: 24px; }
a { color: var(--accent); }
"""


def fmt(value: float, decimals: int = 0) -> str:
    """Formato numérico colombiano: punto de miles y coma decimal."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def pct(value: float, decimals: int = 1) -> str:
    """Porcentaje con coma decimal y espacio antes del signo, por ejemplo 45,3 %."""
    return f"{fmt(value, decimals)} %"


def day_label(day: date) -> str:
    """Fecha corta en español, por ejemplo 3 feb 2026."""
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def nice_step(value: float) -> float:
    """El menor paso 'limpio' (1, 2, 2,5 o 5 × 10^n) mayor o igual a `value`."""
    if value <= 0:
        return 1.0
    base = 10 ** math.floor(math.log10(value))
    for factor in (1, 2, 2.5, 5, 10):
        if value <= factor * base:
            return factor * base
    return 10 * base  # pragma: no cover - el ciclo siempre retorna antes


def trend_title(series: Sequence[tuple[date, float]]) -> str:
    """Titular del gráfico: compara el promedio de la primera y la última semana."""
    values = [v for _, v in series]
    window = min(7, len(values))
    first = sum(values[:window]) / window
    last = sum(values[-window:]) / window
    if first == 0:
        return "Producción diaria del campo"
    change = (last - first) / first * 100
    if abs(change) < 0.5:
        return f"La producción del campo se mantuvo cerca de {fmt(last)} bopd"
    verb = "bajó" if change < 0 else "subió"
    sign = "−" if change < 0 else "+"
    return (
        f"La producción del campo {verb} de {fmt(first)} a {fmt(last)} bopd "
        f"({sign}{pct(abs(change))})"
    )


def line_chart(series: Sequence[tuple[date, float]]) -> str:
    """Línea de la producción diaria del campo con etiquetas de inicio y fin."""
    width, height = 760, 280
    left, right, top, bottom = 64, 80, 20, 40
    plot_w, plot_h = width - left - right, height - top - bottom
    values = [v for _, v in series]
    step = nice_step(max(values) / 4)
    top_value = step * 4

    def x(i: int) -> float:
        return left + (plot_w * i / (len(series) - 1) if len(series) > 1 else plot_w / 2)

    def y(v: float) -> float:
        return top + plot_h * (1 - v / top_value)

    parts = []
    for k in range(5):
        tick = step * k
        parts.append(
            f'<line class="grid" x1="{left}" x2="{width - right}" y1="{y(tick):.1f}" '
            f'y2="{y(tick):.1f}"/>'
            f'<text x="{left - 8}" y="{y(tick) + 4:.1f}" text-anchor="end">{fmt(tick)}</text>'
        )
    points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
    base = f"{x(len(values) - 1):.1f},{y(0):.1f} {x(0):.1f},{y(0):.1f}"
    parts.append(f'<polygon class="area" points="{points} {base}"/>')
    parts.append(f'<polyline class="line" points="{points}"/>')
    for i in sorted({0, len(series) // 2, len(series) - 1}):
        anchor = "start" if i == 0 else "end" if i == len(series) - 1 else "middle"
        parts.append(
            f'<text x="{x(i):.1f}" y="{height - 12}" text-anchor="{anchor}">'
            f"{day_label(series[i][0])}</text>"
        )
    parts.append(
        f'<text class="value-label" x="{x(0) + 4:.1f}" y="{y(values[0]) - 10:.1f}">'
        f"{fmt(values[0])}</text>"
    )
    parts.append(
        f'<text class="value-label" x="{x(len(values) - 1) + 8:.1f}" '
        f'y="{y(values[-1]) + 4:.1f}">{fmt(values[-1])}</text>'
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Producción diaria del campo en barriles por día">{"".join(parts)}</svg>'
    )


def bar_chart(kpis: Sequence[WellKpi]) -> str:
    """Barras horizontales del petróleo acumulado por pozo, cada una con su valor."""
    width, row_h, top = 760, 30, 6
    left, right = 92, 120
    height = top * 2 + row_h * len(kpis)
    peak = max(k.oil_total_bbl for k in kpis) or 1
    parts = []
    for i, k in enumerate(kpis):
        y = top + i * row_h
        bar_w = (width - left - right) * k.oil_total_bbl / peak
        parts.append(
            f'<text x="{left - 10}" y="{y + 19}" text-anchor="end">{escape(k.well)}</text>'
            f'<rect class="bar" x="{left}" y="{y + 6}" width="{bar_w:.1f}" height="{row_h - 12}" '
            f'rx="3"><title>{escape(k.well)}: {fmt(k.oil_total_bbl)} bbl</title></rect>'
            f'<text class="value-label" x="{left + bar_w + 8:.1f}" y="{y + 19}">'
            f"{fmt(k.oil_total_bbl)} bbl</text>"
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Petróleo acumulado por pozo">{"".join(parts)}</svg>'
    )


def wells_table(kpis: Sequence[WellKpi]) -> str:
    """Tabla con los KPIs de cada pozo."""
    rows = []
    for k in kpis:
        decline = "—" if k.decline_pct_month is None else pct(k.decline_pct_month)
        rows.append(
            f"<tr><td>{escape(k.well)}</td><td>{fmt(k.oil_total_bbl)}</td>"
            f"<td>{fmt(k.oil_avg_bopd, 1)}</td><td>{pct(k.water_cut * 100)}</td>"
            f"<td>{pct(k.uptime_pct)}</td><td>{decline}</td></tr>"
        )
    header = (
        "<tr><th>Pozo</th><th>Petróleo acumulado (bbl)</th><th>Promedio (bopd)</th>"
        "<th>Corte de agua</th><th>Disponibilidad</th><th>Declinación mensual</th></tr>"
    )
    body = "".join(rows)
    return (
        f'<div class="table-wrap"><table><thead>{header}</thead><tbody>{body}</tbody></table></div>'
    )


def quality_block(issues: Sequence[Issue], total_records: int) -> str:
    """Resumen de calidad: confirmación si no hay problemas o la lista de hallazgos."""
    if not issues:
        return (
            f'<p class="ok">Sin problemas de calidad en {fmt(total_records)} registros: '
            "sin duplicados, valores negativos, horas fuera de rango ni fechas faltantes.</p>"
        )
    items = "".join(
        f"<li>{escape(i.well)} · {day_label(i.date)} · {escape(i.rule)}: {escape(i.detail)}</li>"
        for i in issues[:MAX_ISSUES_SHOWN]
    )
    hidden = len(issues) - MAX_ISSUES_SHOWN
    more = f'<p class="sub">Y {fmt(hidden)} más en el CSV.</p>' if hidden > 0 else ""
    return (
        f'<p class="warn">{fmt(len(issues))} problemas de calidad en {fmt(total_records)} '
        f'registros</p><ul class="issues">{items}</ul>{more}'
    )


def card(label: str, value: str, unit: str = "") -> str:
    """Tarjeta de un KPI con su unidad."""
    unit_html = f'<span class="unit">{unit}</span>' if unit else ""
    return (
        f'<div class="card"><div class="label">{label}</div>'
        f'<div class="value">{value}{unit_html}</div></div>'
    )


def render(records: Sequence[DailyRecord], issues: Sequence[Issue], seed: int | None = None) -> str:
    """Construye el HTML completo del tablero."""
    field = field_kpis(records)
    wells = well_kpis(records)
    series = field_daily_oil(records)
    start, end = series[0][0], series[-1][0]
    period = f"{day_label(start)} a {day_label(end)} ({field.days} días)"
    origin = (
        f"Datos sintéticos generados con semilla {seed}: no representan pozos reales."
        if seed is not None
        else "Datos cargados desde un CSV propio."
    )
    cards = "".join(
        [
            card("Petróleo acumulado", fmt(field.oil_total_bbl), "bbl"),
            card("Promedio del campo", fmt(field.oil_avg_bopd), "bopd"),
            card("Corte de agua", pct(field.water_cut * 100)),
            card("Disponibilidad", pct(field.uptime_pct)),
        ]
    )
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>Tablero de producción · datos sintéticos</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<header>
<h1>Tablero de producción</h1>
<p>Campo sintético · {field.wells} pozos · {period}</p>
</header>
<div class="cards">{cards}</div>
<section>
<h2>{trend_title(series)}</h2>
<p class="sub">Producción diaria del campo en barriles por día (bopd). El cambio compara el promedio
de la primera y la última semana.</p>
<div class="chart">{line_chart(series)}</div>
</section>
<section>
<h2>Petróleo acumulado por pozo</h2>
<p class="sub">Barriles (bbl) producidos en el periodo, de mayor a menor.</p>
<div class="chart">{bar_chart(wells)}</div>
</section>
<section>
<h2>Indicadores por pozo</h2>
<p class="sub">La declinación mensual se estima solo con los días de operación completa.</p>
{wells_table(wells)}
</section>
<section>
<h2>Calidad de datos</h2>
{quality_block(issues, len(records))}
</section>
<footer>{origin} <a href="produccion.csv">Descargar los datos (CSV)</a> ·
industrial-kpi-dashboard v{__version__}</footer>
</main>
</body>
</html>
"""
