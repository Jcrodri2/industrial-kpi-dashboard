from dataclasses import replace
from datetime import date, timedelta

import pytest

from kpi_dashboard.quality import check
from kpi_dashboard.synthetic import generate, read_csv, write_csv


def test_generate_is_reproducible_with_the_same_seed():
    assert generate(wells=3, days=10, seed=7) == generate(wells=3, days=10, seed=7)


def test_generate_changes_with_another_seed():
    assert generate(wells=3, days=10, seed=7) != generate(wells=3, days=10, seed=8)


def test_generate_shape_and_ranges():
    records = generate(wells=4, days=30, start=date(2026, 3, 1), seed=1)
    assert len(records) == 120
    assert {r.well for r in records} == {"POZO-01", "POZO-02", "POZO-03", "POZO-04"}
    assert min(r.date for r in records) == date(2026, 3, 1)
    assert max(r.date for r in records) == date(2026, 3, 30)
    assert all(r.oil_bopd >= 0 and r.water_bwpd >= 0 and r.gas_kscfd >= 0 for r in records)
    assert all(0 <= r.uptime_h <= 24 for r in records)


@pytest.mark.parametrize("kwargs", [{"wells": 0}, {"days": 0}, {"downtime_probability": 1}])
def test_generate_rejects_invalid_arguments(kwargs):
    with pytest.raises(ValueError):
        generate(**kwargs)


def test_csv_round_trip(tmp_path):
    records = generate(wells=2, days=5, seed=3)
    path = tmp_path / "produccion.csv"
    write_csv(records, path)
    assert read_csv(path) == records


def test_clean_synthetic_data_has_no_issues():
    assert check(generate(wells=5, days=60, seed=11)) == []


def test_check_detects_every_rule():
    d = generate(wells=1, days=5, seed=2)
    broken = [
        d[0],
        replace(d[0], oil_bopd=-1.0),
        replace(d[2], uptime_h=25.0),
        replace(d[3], uptime_h=0.0, oil_bopd=10.0),
        replace(d[4], date=d[4].date + timedelta(days=3)),
    ]
    issues = check(broken)
    assert sorted({i.rule for i in issues}) == [
        "duplicado",
        "fechas_faltantes",
        "horas_fuera_de_rango",
        "negativo",
        "produccion_sin_operacion",
    ]
    gaps = [i.detail for i in issues if i.rule == "fechas_faltantes"]
    assert gaps == ["falta 1 día", "faltan 3 días"]
