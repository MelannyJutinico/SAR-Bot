"""Describe episodios conservados a partir de sus trazas (SARB-023).

Ejemplos:
    python scripts/trace_story.py --cases configs/analysis/sarb023_casos.json \
        --output-dir results/sarb023
    python scripts/trace_story.py --check results/sarb023
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.trace_analysis import build_trace_report, check_trace_report  # noqa: E402


def relative(path: Path) -> str:
    absolute = path if path.is_absolute() else ROOT / path
    try:
        return absolute.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return absolute.as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", type=Path, help="JSON con los episodios a describir")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--check", type=Path, metavar="DIR",
                        help="Regenerar desde las fuentes registradas y comparar")
    args = parser.parse_args()
    if args.check:
        problems = check_trace_report(args.check, ROOT)
        if problems:
            print("\n".join(f"- {p}" for p in problems))
            sys.exit(1)
        print(f"OK: {relative(args.check)} coincide con sus fuentes")
        return
    if not args.cases or not args.output_dir:
        parser.error("Indicar --cases y --output-dir, o --check")
    try:
        files = build_trace_report(relative(args.cases), ROOT)
    except ValueError as error:
        raise SystemExit(f"No se generó nada: {error}")
    target = ROOT / relative(args.output_dir)
    target.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(files.items()):
        (target / name).write_bytes(data)
        print(f"- {relative(target / name)}")


if __name__ == "__main__":
    main()
