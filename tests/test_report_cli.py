import runpy
import sys
from dataclasses import replace

import pytest

from kpi_dashboard.cli import main
from kpi_dashboard.quality import check
from kpi_dashboard.report import fmt, nice_step, pct, render, trend_title
from kpi_dashboard.synthetic import generate, read_csv


def test_numbers_use_colombian_separators():
    assert fmt(1234567.891, 1) == "1.234.567,9"
    assert fmt(12.6) == "13"
    assert pct(45.27) == "45,3 %"


@pytest.mark.parametrize(
    ("value", "expected"), [(0, 1.0), (0.3, 0.5), (1625, 2000), (2400, 2500), (9100, 10000)]
)
def test_nice_step(value, expected):
    assert nice_step(value) == expected


def test_trend_title_describes_the_change():
    falling = [(None, 100.0)] * 7 + [(None, 80.0)] * 7
    assert trend_title(falling) == "La producción del campo bajó de 100 a 80 bopd (−20,0 %)"
    flat = [(None, 50.0)] * 10
    assert trend_title(flat) == "La producción del campo se mantuvo cerca de 50 bopd"
    assert trend_title([(None, 0.0)] * 3) == "Producción diaria del campo"


def test_render_contains_kpis_charts_and_seed():
    records = generate(wells=3, days=20, seed=4)
    html = render(records, check(records), seed=4)
    assert html.startswith("<!doctype html>")
    assert "default-src 'none'" in html
    assert "<script" not in html
    assert html.count("<svg") == 2
    assert "POZO-03" in html
    assert "Sin problemas de calidad" in html
    assert "semilla 4" in html


def test_render_escapes_untrusted_well_names():
    records = [replace(r, well="<script>x</script>") for r in generate(wells=1, days=3, seed=1)]
    html = render(records, check(records))
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html
    assert "CSV propio" in html


def test_render_lists_quality_issues():
    records = generate(wells=1, days=3, seed=1)
    broken = records + [records[0]]
    html = render(broken, check(broken))
    assert "1 problemas de calidad" in html
    assert "duplicado" in html


def test_cli_builds_the_site(tmp_path, capsys):
    out = tmp_path / "site"
    assert main(["--wells", "2", "--days", "10", "--seed", "9", "--out", str(out)]) == 0
    assert (out / "index.html").read_text(encoding="utf-8").startswith("<!doctype html>")
    assert len(read_csv(out / "produccion.csv")) == 20
    assert "20 registros" in capsys.readouterr().out


def test_cli_reads_a_csv_and_fails_in_strict_mode(tmp_path):
    first = tmp_path / "a"
    main(["--wells", "1", "--days", "5", "--out", str(first)])
    csv_path = tmp_path / "propio.csv"
    lines = (first / "produccion.csv").read_text(encoding="utf-8").splitlines()
    csv_path.write_text("\n".join([*lines, lines[1]]) + "\n", encoding="utf-8")
    second = tmp_path / "b"
    assert main(["--input", str(csv_path), "--out", str(second)]) == 0
    assert main(["--input", str(csv_path), "--out", str(second), "--strict"]) == 1


def test_cli_handles_an_empty_csv(tmp_path, capsys):
    empty = tmp_path / "vacio.csv"
    empty.write_text("date,well,oil_bopd,water_bwpd,gas_kscfd,uptime_h\n", encoding="utf-8")
    assert main(["--input", str(empty), "--out", str(tmp_path / "out")]) == 2
    assert "no tiene registros" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (None, "No se pudo leer"),
        ("date,well,oil_bopd\n2026-01-01,POZO-01,10\n", "le falta la columna 'water_bwpd'"),
        (
            "date,well,oil_bopd,water_bwpd,gas_kscfd,uptime_h\n2026-01-01,POZO-01,diez,1,1,24\n",
            "valor inválido",
        ),
        (
            "date,well,oil_bopd,water_bwpd,gas_kscfd,uptime_h\n2026-01-01,POZO-01,10\n",
            "fila incompleta",
        ),
    ],
)
def test_cli_explains_unreadable_csv_files(tmp_path, capsys, content, message):
    path = tmp_path / "datos.csv"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    assert main(["--input", str(path), "--out", str(tmp_path / "out")]) == 2
    captured = capsys.readouterr()
    assert message in captured.err
    assert "Traceback" not in captured.err


def test_module_runs_with_python_dash_m(tmp_path, monkeypatch):
    argv = ["kpi_dashboard", "--wells", "1", "--days", "2", "--out", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("kpi_dashboard", run_name="__main__")
    assert exc.value.code == 0
    assert (tmp_path / "index.html").exists()


def test_cli_rejects_invalid_arguments():
    with pytest.raises(SystemExit) as exc:
        main(["--wells", "0"])
    assert exc.value.code == 2
