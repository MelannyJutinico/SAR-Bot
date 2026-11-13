"""Carga una política guardada y compara resultados con referencias."""

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import torch
from stable_baselines3 import DQN

from sar_bot.agents import RandomPolicy, ShortestPathPolicy, ThermalPathPolicy
from sar_bot.core import RescueSimulation, Scenario
from sar_bot.evaluation import evaluate_episode
from sar_bot.learning import evaluate_model
from sar_bot.env import RewardConfig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--scenarios", nargs="+", type=Path,
                        default=sorted((ROOT / "scenarios").glob("*.json")))
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/dqn_comparison.csv")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--metadata", type=Path, help="Configuración del experimento; por defecto junto al modelo")
    args = parser.parse_args()
    torch.set_num_threads(1)
    model = DQN.load(args.model, device="cpu")
    scenarios = [Scenario.load(path) for path in args.scenarios]
    metadata_path = args.metadata or args.model.parent / "metadata.json"
    if args.metadata and not metadata_path.exists():
        parser.error("No existe el archivo de metadatos indicado")
    rewards = (RewardConfig(**json.loads(metadata_path.read_text(encoding="utf-8"))["rewards"])
               if metadata_path.exists() else RewardConfig())
    results = evaluate_model(model, scenarios, rewards)
    for scenario in scenarios:
        for strategy in ("shortest", "thermal", "random"):
            sim = RescueSimulation(scenario)
            policy = (ShortestPathPolicy(sim) if strategy == "shortest" else
                      ThermalPathPolicy(sim) if strategy == "thermal" else
                      RandomPolicy(sim, args.seed))
            results.append(evaluate_episode(sim, policy, strategy,
                                            args.seed if strategy == "random" else None))
    columns = sorted({key for result in results for key in result})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)
    for r in results:
        print(f"{r['scenario']} | {r['strategy']} | {r['outcome']} | "
              f"rescates={r['rescued']}/2 | pasos={r['steps']} | daño={r['damage_total']}")
    print(f"CSV: {args.output}")
    print("Un episodio determinista por escenario y una semilla aleatoria; no demuestra generalización.")


if __name__ == "__main__":
    main()
