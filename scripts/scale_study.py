"""Estudio de escala, reparto de rescates y dificultad (SARB-031).

Subcomandos:
    # Generar un conjunto de desarrollo con posiciones variables (no es una partición).
    python scripts/scale_study.py generate --template scenarios/v2/building_10x10.json \
        --set-id v2_10x10_dev_v1 --building building10 --seed 1010001 --requested 30 \
        --record configs/development/v2_10x10_dev.json \
        --scenario-dir scenarios/development/v2_10x10

    # Comprobar un conjunto de desarrollo.
    python scripts/scale_study.py verify --record configs/development/v2_10x10_dev.json

    # Generar las tablas desde CSV de scripts/evaluate_experiment.py.
    python scripts/scale_study.py analyze --results <a.csv> <b.csv> --output-dir results/sarb031

    # Comprobar que las tablas siguen coincidiendo con sus fuentes.
    python scripts/scale_study.py check results/sarb031
"""

import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.development import (  # noqa: E402
    build_development_set,
    verify_development_set,
    write_development_set,
)
from sar_bot.study import build_study, check_study  # noqa: E402


def relative(path: Path) -> str:
    absolute = path if path.is_absolute() else ROOT / path
    try:
        return absolute.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return absolute.as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="Generar un conjunto de desarrollo")
    generate.add_argument("--template", type=Path, required=True)
    generate.add_argument("--set-id", required=True)
    generate.add_argument("--building", required=True)
    generate.add_argument("--seed", type=int, required=True)
    generate.add_argument("--requested", type=int, default=30)
    generate.add_argument("--max-attempts", type=int, default=3000)
    generate.add_argument("--record", type=Path, required=True)
    generate.add_argument("--scenario-dir", required=True)
    verify = commands.add_parser("verify", help="Comprobar un conjunto de desarrollo")
    verify.add_argument("--record", type=Path, required=True)
    analyze = commands.add_parser("analyze", help="Generar las tablas del estudio")
    analyze.add_argument("--results", type=Path, nargs="+", required=True)
    analyze.add_argument("--output-dir", type=Path, required=True)
    analyze.add_argument("--skip-replay", action="store_true")
    check = commands.add_parser("check", help="Regenerar y comparar")
    check.add_argument("directory", type=Path)
    args = parser.parse_args()

    if args.command == "generate":
        record, scenarios = build_development_set(
            template_path=relative(args.template), root=ROOT, set_id=args.set_id,
            building=args.building, seed=args.seed, requested=args.requested,
            max_attempts=args.max_attempts, scenario_dir=args.scenario_dir,
            created_on=date.today().isoformat())
        path = write_development_set(record, scenarios, args.record, ROOT)
        generation = record["generation"]
        print(f"{len(record['entries'])} casos certificados en {generation['attempts']} intentos")
        print(f"Registro: {relative(path)}")
    elif args.command == "verify":
        problems = verify_development_set(ROOT / relative(args.record), ROOT)
        if problems:
            print("\n".join(f"- {p}" for p in problems))
            sys.exit(1)
        print(f"OK: {relative(args.record)} está íntegro")
    elif args.command == "analyze":
        output_dir = relative(args.output_dir)
        try:
            files = build_study(ROOT, [relative(p) for p in args.results], output_dir=output_dir,
                                replay=not args.skip_replay)
        except ValueError as error:
            raise SystemExit(f"No se generó nada: {error}")
        target = ROOT / output_dir
        target.mkdir(parents=True, exist_ok=True)
        for name, data in sorted(files.items()):
            (target / name).write_bytes(data)
            print(f"- {output_dir}/{name}")
    else:
        problems = check_study(args.directory, ROOT)
        if problems:
            print("\n".join(f"- {p}" for p in problems))
            sys.exit(1)
        print(f"OK: {relative(args.directory)} coincide con sus fuentes")


if __name__ == "__main__":
    main()
