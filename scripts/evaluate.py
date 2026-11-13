"""Evalúa referencias en escenarios de desarrollo y exporta un CSV."""

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.agents import RandomPolicy, ShortestPathPolicy, ThermalPathPolicy
from sar_bot.core import RescueSimulation, Scenario
from sar_bot.evaluation import evaluate_episode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", nargs="+", type=Path,
                        default=sorted((ROOT / "scenarios").glob("*.json")))
    parser.add_argument("--strategy", choices=("all", "shortest", "thermal", "random"), default="all")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/reference_results.csv")
    args = parser.parse_args()
    strategies = ("shortest", "thermal", "random") if args.strategy == "all" else (args.strategy,)
    results = []
    for path in args.scenarios:
        scenario = Scenario.load(path)
        for strategy in strategies:
            simulation = RescueSimulation(scenario)
            policy = (ShortestPathPolicy(simulation) if strategy == "shortest" else
                      ThermalPathPolicy(simulation) if strategy == "thermal" else
                      RandomPolicy(simulation, args.seed))
            result = evaluate_episode(simulation, policy, strategy,
                                      args.seed if strategy == "random" else None)
            results.append(result)
            print(f"{result['scenario']} | {strategy} | {result['outcome']} | "
                  f"rescates={result['rescued']}/2 | pasos={result['steps']} | "
                  f"daño={result['damage_total']}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResultados: {args.output}")
    print("Evaluación de desarrollo: un episodio por escenario y estrategia; sin agente aprendido.")


if __name__ == "__main__":
    main()
