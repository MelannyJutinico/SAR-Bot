"""Compara DQN y referencias sobre los mismos casos y guarda CSV, trazas y metadatos.

Ejemplos:
    # Referencias sobre la validación congelada del perfil 12 × 12.
    python scripts/evaluate_experiment.py --manifest configs/partitions/v2_12x12.json \
        --split validation --strategies shortest thermal random --output outputs/eval/validation.csv

    # DQN y referencias sobre escenarios de desarrollo de otro perfil.
    python scripts/evaluate_experiment.py --scenarios scenarios/pasillo_compartido.json \
        --model artifacts/sensors_dqn/model.zip --output outputs/eval/dev.csv

    # Referencias y modelo de desarrollo sobre un conjunto generado (SARB-031).
    python scripts/evaluate_experiment.py --development-set configs/development/v2_10x10_dev.json         --model artifacts/v2_pilot/model.zip --output results/sarb031/v2_10x10_desarrollo.csv

    # Comprobar un CSV existente reproduciendo sus trazas.
    python scripts/evaluate_experiment.py --verify outputs/eval/validation.csv
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.experiment import (  # noqa: E402
    STRATEGIES,
    cases_from_development_set,
    cases_from_manifest,
    cases_from_paths,
    evaluate_cases,
    load_model,
    summarize,
    verify_results,
    write_results,
)
from sar_bot.final_check import check_final_models  # noqa: E402
from sar_bot.partitions import canonical_sha256, file_sha256  # noqa: E402


def git_revision():
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                                    capture_output=True, text=True, check=True).stdout.strip())
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def resolve_rewards(args, models):
    from sar_bot.env import RewardConfig

    if args.rewards:
        data = json.loads(args.rewards.read_text(encoding="utf-8"))
        return RewardConfig(**data.get("rewards", data)), args.rewards.as_posix()
    configs = {canonical_sha256(m.reward_config): m.reward_config for m in models if m.reward_config}
    if len(configs) > 1:
        raise SystemExit("Los modelos usan recompensas distintas; indicar --rewards para "
                         "calcular el retorno con una sola función")
    if configs:
        return RewardConfig(**next(iter(configs.values()))), "model_metadata"
    return RewardConfig(), "default"


def print_summary(rows):
    print("| estrategia | modelo | episodios | casos | éxitos | rescates | pasos (éxitos) "
          "| daño (éxitos) | destruidos | límite |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for s in summarize(rows):
        print(f"| {s['strategy']} | {s['model_label'] or '-'} | {s['episodes']} | "
              f"{s['configurations']} | {s['successes']}/{s['episodes']} | "
              f"{s['rescued']}/{s['victims']} | {s['mean_steps_success']} | "
              f"{s['mean_damage_success']} | {s['destroyed']} | {s['time_limit']} |")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--manifest", type=Path, help="Manifiesto de particiones congelado")
    source.add_argument("--scenarios", nargs="+", type=Path, help="Lista libre de desarrollo")
    source.add_argument("--development-set", type=Path,
                        help="Conjunto de desarrollo generado (configs/development/*.json)")
    source.add_argument("--verify", type=Path, help="CSV ya escrito para reproducir y comprobar")
    parser.add_argument("--split", choices=("training", "validation", "test"))
    parser.add_argument("--partition", default="development",
                        help="Etiqueta de partición para --scenarios (no puede ser test)")
    parser.add_argument("--final", action="store_true",
                        help="Confirma que se abre la prueba con modelos congelados (SARB-021)")
    parser.add_argument("--model", type=Path, action="append", default=[],
                        help="Modelo DQN; repetir para varias semillas")
    parser.add_argument("--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES))
    parser.add_argument("--random-seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--thermal-damage-weight", type=float, default=2.0)
    parser.add_argument("--rewards", type=Path,
                        help="JSON con 'rewards' para calcular el retorno de todas las filas")
    parser.add_argument("--limit", type=int, help="Solo los primeros N casos (no en prueba)")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/eval/comparison.csv")
    args = parser.parse_args()

    if args.verify:
        problems = verify_results(args.verify, ROOT)
        if problems:
            print("Resultados con problemas:")
            print("\n".join(f"- {p}" for p in problems[:50]))
            sys.exit(1)
        print(f"OK: cada fila de {args.verify} coincide con la reproducción de su traza")
        return

    if args.manifest:
        if not args.split:
            parser.error("--manifest requiere --split")
        if args.split == "test" and not args.final:
            parser.error("La prueba final requiere --final y modelos congelados (SARB-019/021)")
        if args.split == "test" and args.limit:
            parser.error("La prueba final no admite --limit: se evalúan todos los casos")
        if args.split == "test":
            # Antes de leer un solo caso de prueba: modelos congelados y protocolo.
            problems = check_final_models(args.manifest, args.model, ROOT)
            if problems:
                print("No se abre la prueba final; los modelos no cumplen el protocolo:")
                print("\n".join(f"- {p}" for p in problems))
                sys.exit(2)
        cases = cases_from_manifest(args.manifest, args.split, ROOT,
                                    allow_test=args.split == "test")
    elif args.scenarios:
        cases = cases_from_paths(args.scenarios, ROOT, args.partition)
    elif args.development_set:
        cases = cases_from_development_set(args.development_set, ROOT)
    else:
        parser.error("Indicar --manifest con --split, --scenarios, --development-set o --verify")
    if args.limit:
        cases = cases[:args.limit]

    strategies = tuple(args.strategies)
    if "dqn" in strategies and not args.model:
        strategies = tuple(s for s in strategies if s != "dqn")
        print("Sin --model: se evalúan solo las referencias")
    models = [load_model(path) for path in args.model] if "dqn" in strategies else []
    rewards, reward_source = resolve_rewards(args, models)
    rows, traces = evaluate_cases(cases, models=models, strategies=strategies,
                                  random_seeds=tuple(args.random_seeds), rewards=rewards,
                                  thermal_damage_weight=args.thermal_damage_weight)

    import gymnasium
    import stable_baselines3
    import torch
    scenario = cases[0].scenario
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": " ".join(sys.argv),
        "git": git_revision(),
        "python": platform.python_version(),
        "packages": {"gymnasium": gymnasium.__version__,
                     "stable_baselines3": stable_baselines3.__version__,
                     "torch": torch.__version__},
        "partition": cases[0].partition,
        "manifest": ({"path": args.manifest.as_posix(), "manifest_id": cases[0].manifest_id,
                      "sha256": file_sha256(args.manifest)} if args.manifest else None),
        "development_set": ({"path": args.development_set.as_posix(),
                             "set_id": cases[0].manifest_id,
                             "sha256": file_sha256(args.development_set)}
                            if args.development_set else None),
        "profile": {"width": scenario.width, "height": scenario.height,
                    "victims": scenario.victim_count},
        "scenarios": {c.scenario_path: c.scenario_sha256 for c in cases},
        "strategies": list(strategies),
        "models": [{"label": m.label, "path": m.path, "sha256": m.sha256,
                    "training_seed": m.training_seed,
                    "reward_config_sha256": (canonical_sha256(m.reward_config)
                                             if m.reward_config else None)} for m in models],
        "final_check": "superada" if args.split == "test" else None,
        "random_seeds": args.random_seeds if "random" in strategies else [],
        "thermal_damage_weight": args.thermal_damage_weight,
        "reward_config": vars(rewards),
        "reward_config_sha256": canonical_sha256(vars(rewards)),
        "reward_config_source": reward_source,
        "episodes_per_case": {"dqn": len(models), "shortest": 1, "thermal": 1,
                              "random": len(args.random_seeds)},
        "notes": [
            "Las referencias deterministas se ejecutan una vez por caso.",
            "El retorno solo es comparable entre filas con el mismo reward_config_sha256.",
            "compute_seconds mide cómputo en esta máquina; no es tiempo simulado.",
        ],
    }
    write_results(rows, traces, args.output, metadata)
    print_summary(rows)
    print(f"CSV: {args.output}")
    problems = verify_results(args.output, ROOT)
    if problems:
        print("La verificación de trazas falló:")
        print("\n".join(problems[:20]))
        sys.exit(1)
    print("Trazas reproducidas: las métricas coinciden con el motor.")


if __name__ == "__main__":
    main()
