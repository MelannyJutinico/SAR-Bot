"""Conserva un checkpoint de desarrollo y su evidencia, sin copiar todo el entrenamiento."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    sources = {
        "model.zip": "best_model.zip",
        "metadata.json": "metadata.json",
        "best_results.json": "best_results.json",
        "comparison.csv": "comparison.csv",
        "evaluations.jsonl": "evaluations.jsonl",
    }
    for source in sources.values():
        if not (args.run_dir / source).is_file():
            parser.error(f"Falta {source}; completar el entrenamiento y su comparación")
    # Conservar también las particiones consultadas y la procedencia de cada CSV.
    for optional in ("comparison.metadata.json", "validation.csv", "validation.metadata.json",
                     "test.csv", "test.metadata.json"):
        if (args.run_dir / optional).is_file():
            sources[optional] = optional
    if args.destination.exists():
        parser.error("El destino debe ser nuevo para no sobrescribir un modelo publicado")
    records = [json.loads(line) for line in (args.run_dir / "evaluations.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    best = max(records, key=lambda r: tuple(r["score"]))
    model_hash = hashlib.sha256((args.run_dir / "best_model.zip").read_bytes()).hexdigest()
    for name in ("comparison.metadata.json", "validation.metadata.json", "test.metadata.json"):
        if name in sources:
            provenance = json.loads((args.run_dir / name).read_text(encoding="utf-8"))
            if provenance["model_sha256"] != model_hash:
                parser.error(f"{name} corresponde a otro modelo; no se mezclan resultados")
    metadata = json.loads((args.run_dir / "metadata.json").read_text(encoding="utf-8"))
    partition_results = {}
    for partition, filename in (("training/development", "comparison.csv"),
                                ("validation", "validation.csv"), ("test", "test.csv")):
        if filename in sources:
            with (args.run_dir / filename).open(encoding="utf-8", newline="") as file:
                rows = [row for row in csv.DictReader(file) if row["strategy"] == "dqn"]
            partition_results[partition] = {
                "episodes": len(rows), "successes": sum(row["success"] == "True" for row in rows),
                "scenarios": [row["scenario"] for row in rows],
            }
    summary = {
        "scope": "checkpoint selected on development; one training seed; held-out checks listed separately",
        "selected_checkpoint": best,
        "last_checkpoint": records[-1],
        "model_sha256": model_hash,
        "observation_mode": metadata["config"].get("observation_mode", "full"),
        "dqn_successes_by_partition": partition_results,
    }
    args.destination.mkdir(parents=True)
    for target, source in sources.items():
        shutil.copyfile(args.run_dir / source, args.destination / target)
    (args.destination / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Modelo y resultados guardados en {args.destination}")
    print(f"Checkpoint seleccionado: {best['steps']} pasos; entrenamiento total: {records[-1]['steps']}")


if __name__ == "__main__":
    main()
