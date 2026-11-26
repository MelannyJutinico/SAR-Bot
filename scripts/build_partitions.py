"""Construye, verifica o resume particiones experimentales congeladas (SARB-009).

Ejemplos:
    python scripts/build_partitions.py build --config configs/partitions/v2_12x12.config.json
    python scripts/build_partitions.py verify --manifest configs/partitions/v2_12x12.json
    python scripts/build_partitions.py summary --manifest configs/partitions/v2_12x12.json
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.partitions import (  # noqa: E402
    build_partitions,
    check_training_configs,
    distribution,
    file_sha256,
    verify_manifest,
    write_partitions,
)

COLUMNS = ("partition", "building", "count", "easy", "intermediate", "demanding",
           "mean_distance_ratio", "victims_in_heat", "witness_thermal", "witness_shortest",
           "mean_witness_steps", "mean_witness_damage")


def print_summary(manifest_path: Path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"Manifiesto {manifest['manifest_id']} - sha256 {file_sha256(manifest_path)}")
    print(f"content_sha256 {manifest['content_sha256']}")
    print()
    print("| " + " | ".join(COLUMNS) + " |")
    print("|" + "---|" * len(COLUMNS))
    for row in distribution(manifest, ROOT):
        print("| " + " | ".join(str(row[c]) for c in COLUMNS) + " |")
    print()
    print("| building | seed | split_seed | attempts | certified | not_certified | "
          "duplicates | skipped | certified_unused |")
    print("|---|---|---|---|---|---|---|---|---|")
    for g in manifest["generation"]:
        print(f"| {g['building']} | {g['generation_seed']} | {g['split_seed']} | {g['attempts']} | "
              f"{g['certified']} | {g['not_certified']} | {g['duplicates']} | "
              f"{json.dumps(g['skipped'])} | {g['certified_unused']} |")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Genera escenarios, testigos y manifiesto; no sobrescribe")
    build.add_argument("--config", type=Path, required=True)
    verify = sub.add_parser("verify", help="Comprueba hashes, separación, cuotas y testigos")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--skip-replay", action="store_true",
                        help="No reproducir los testigos de viabilidad")
    summary = sub.add_parser("summary", help="Imprime la distribución en Markdown")
    summary.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "build":
        config = json.loads(args.config.read_text(encoding="utf-8"))
        result = build_partitions(config, ROOT)
        path = write_partitions(result, ROOT)
        print(f"Manifiesto escrito: {path.relative_to(ROOT).as_posix()}")
        problems = verify_manifest(path, ROOT)
        if problems:
            print("\n".join(problems))
            sys.exit(1)
        print_summary(path)
    elif args.command == "verify":
        problems = verify_manifest(args.manifest, ROOT, replay_witnesses=not args.skip_replay)
        problems += check_training_configs(args.manifest, sorted((ROOT / "configs").glob("dqn_*.json")))
        if problems:
            print("Manifiesto con problemas:")
            print("\n".join(f"- {p}" for p in problems))
            sys.exit(1)
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        print(f"OK {manifest['manifest_id']}: "
              + ", ".join(f"{p}={len(manifest[p])}" for p in ("training", "validation", "test"))
              + f" - sha256 {file_sha256(args.manifest)}")
    else:
        print_summary(args.manifest)


if __name__ == "__main__":
    main()
