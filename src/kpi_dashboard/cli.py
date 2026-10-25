"""Línea de comandos: genera o lee los datos, valida su calidad y construye el tablero."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from .quality import check
from .report import render
from .synthetic import generate, read_csv, write_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kpi-dashboard",
        description="Genera producción sintética, valida su calidad y construye el tablero HTML.",
    )
    parser.add_argument("--wells", type=int, default=12, help="número de pozos (12 por defecto)")
    parser.add_argument("--days", type=int, default=180, help="días de historia (180 por defecto)")
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        default=date(2026, 1, 1),
        help="fecha inicial AAAA-MM-DD",
    )
    parser.add_argument("--seed", type=int, default=42, help="semilla para reproducir los datos")
    parser.add_argument("--input", type=Path, help="CSV propio en lugar de datos sintéticos")
    parser.add_argument("--out", type=Path, default=Path("site"), help="carpeta de salida")
    parser.add_argument(
        "--strict", action="store_true", help="termina con error si hay problemas de calidad"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Construye el tablero y devuelve el código de salida.

    0: tablero construido. 1: hay problemas de calidad y se pidió --strict.
    2: el CSV no existe, le faltan columnas, trae valores inválidos o está vacío.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    seed: int | None = None
    if args.input:
        try:
            records = read_csv(args.input)
        except OSError as error:
            print(f"No se pudo leer {args.input}: {error.strerror or error}", file=sys.stderr)
            return 2
        except KeyError as error:
            print(f"Al CSV {args.input} le falta la columna {error}.", file=sys.stderr)
            return 2
        except (TypeError, ValueError) as error:
            print(
                f"El CSV {args.input} tiene un valor inválido o una fila incompleta: {error}",
                file=sys.stderr,
            )
            return 2
    else:
        try:
            records = generate(wells=args.wells, days=args.days, start=args.start, seed=args.seed)
        except ValueError as error:
            parser.error(str(error))
        seed = args.seed
    if not records:
        print(f"El CSV {args.input} no tiene registros.", file=sys.stderr)
        return 2

    issues = check(records)
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(records, args.out / "produccion.csv")
    (args.out / "index.html").write_text(render(records, issues, seed=seed), encoding="utf-8")
    print(
        f"Tablero en {args.out / 'index.html'} · {len(records)} registros · "
        f"{len(issues)} problemas de calidad"
    )
    return 1 if args.strict and issues else 0
