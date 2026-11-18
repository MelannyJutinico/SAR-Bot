"""Genera las tablas y figuras del informe desde resultados conservados (SARB-022).

Ejemplos:
    # Referencias sobre la validación 12 × 12 (evidencia de SARB-020).
    python scripts/report_figures.py \
        --results results/sarb020/v2_12x12_validation_referencias.csv \
        --output-dir results/sarb022/validacion_12x12

    # Evaluación con DQN y las curvas de entrenamiento de esos mismos modelos.
    python scripts/report_figures.py --results results/final/test.csv \
        --training artifacts/<semilla0> --training artifacts/<semilla1> \
        --training artifacts/<semilla2> --output-dir results/final/figuras

    # Comprobar que un directorio sigue coincidiendo con sus fuentes.
    python scripts/report_figures.py --check results/sarb022/validacion_12x12
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.report import SOURCES_FILE, build_report, check_report, write_report  # noqa: E402


def relative(path: Path) -> str:
    absolute = path if path.is_absolute() else ROOT / path
    try:
        return absolute.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return absolute.as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path,
                        help="CSV de scripts/evaluate_experiment.py con sus trazas y metadatos")
    parser.add_argument("--training", type=Path, action="append", default=[],
                        help="Carpeta de un entrenamiento (evaluations.jsonl, metadata.json); "
                             "repetir por semilla")
    parser.add_argument("--output-dir", type=Path, help="Directorio de tablas y figuras")
    parser.add_argument("--skip-replay", action="store_true",
                        help="Solo comprobar el hash del CSV, sin reproducir las trazas")
    parser.add_argument("--check", type=Path, metavar="DIR",
                        help="Regenerar desde las fuentes registradas y comparar")
    args = parser.parse_args()

    if args.check:
        problems = check_report(args.check, ROOT)
        if problems:
            print("Las tablas o figuras no coinciden con sus fuentes:")
            print("\n".join(f"- {p}" for p in problems))
            sys.exit(1)
        print(f"OK: {args.check} coincide con lo que producen las fuentes de {SOURCES_FILE}")
        return

    if not args.results and not args.training:
        parser.error("Indicar --results, --training o --check")
    if not args.output_dir:
        parser.error("Indicar --output-dir")
    output_dir = relative(args.output_dir)
    try:
        files = build_report(ROOT, results=relative(args.results) if args.results else None,
                             training=[relative(path) for path in args.training],
                             output_dir=output_dir, replay=not args.skip_replay)
    except ValueError as error:
        raise SystemExit(f"No se generó nada: {error}")
    for path in write_report(files, ROOT / output_dir):
        print(f"- {path.relative_to(ROOT).as_posix()}")
    print("Para comprobarlo después: python scripts/report_figures.py --check " + output_dir)


if __name__ == "__main__":
    main()
