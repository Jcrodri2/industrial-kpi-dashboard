import math
from datetime import date, timedelta

import pytest

from kpi_dashboard.kpis import field_daily_oil, field_kpis, monthly_decline, water_cut, well_kpis
from kpi_dashboard.synthetic import DailyRecord, generate


def rec(day, well="POZO-01", oil=100.0, water=0.0, uptime=24.0):
    return DailyRecord(date(2026, 1, 1) + timedelta(days=day), well, oil, water, 0.0, uptime)


def test_water_cut():
    assert water_cut(75, 25) == 0.25
    assert water_cut(0, 0) == 0.0


def test_monthly_decline_recovers_an_exponential_rate():
    b = 0.002
    points = [(d, 500 * math.exp(-b * d)) for d in range(120)]
    assert monthly_decline(points) == pytest.approx((1 - math.exp(-30 * b)) * 100)


def test_monthly_decline_needs_two_positive_days():
    assert monthly_decline([(0, 100.0)]) is None
    assert monthly_decline([(0, 0.0), (1, 0.0)]) is None
    assert monthly_decline([(3, 100.0), (3, 90.0)]) is None


def test_well_and_field_kpis_on_known_data():
    records = [
        rec(0, "POZO-01", oil=100, water=100),
        rec(1, "POZO-01", oil=80, water=120, uptime=12),
        rec(0, "POZO-02", oil=300, water=100),
        rec(1, "POZO-02", oil=300, water=100),
    ]
    wells = well_kpis(records)
    assert [k.well for k in wells] == ["POZO-02", "POZO-01"]
    pozo_01 = wells[1]
    assert pozo_01.oil_total_bbl == 180
    assert pozo_01.oil_avg_bopd == 90
    assert pozo_01.water_cut == pytest.approx(220 / 400)
    assert pozo_01.uptime_pct == pytest.approx(75)
    assert pozo_01.decline_pct_month is None

    field = field_kpis(records)
    assert (field.days, field.wells) == (2, 2)
    assert field.oil_total_bbl == 780
    assert field.oil_avg_bopd == 390
    assert field.water_cut == pytest.approx(420 / 1200)
    assert field.uptime_pct == pytest.approx(87.5)
    assert field_daily_oil(records) == [(date(2026, 1, 1), 400), (date(2026, 1, 2), 380)]


def test_field_kpis_rejects_empty_input():
    with pytest.raises(ValueError):
        field_kpis([])


def test_synthetic_wells_decline_between_2_and_9_percent_per_month():
    for k in well_kpis(generate(wells=6, days=180, seed=5)):
        assert k.decline_pct_month is not None
        assert 2 < k.decline_pct_month < 9
