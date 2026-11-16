"""Evalúa estrategias en la partición fija de validación o prueba y exporta un CSV por episodio.

Ejemplos:
    python scripts/evaluate.py --strategy referencia aleatoria
    python scripts/evaluate.py --strategy referencia dqn --model models/base_s0/best_model.zip
    python scripts/evaluate.py --split test --strategy referencia dqn --model models/base_s0/best_model.zip
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sar_bot.agents import RandomPolicy, ShortestPathBaseline
from sar_bot.config import load_config
from sar_bot.core.scenario import PROJECT_ROOT
from sar_bot.evaluation import evaluate, format_summary, summarize, write_csv

STRATEGIES = ("referencia", "aleatoria", "dqn")


def build_policy(name: str, model: str | None):
    if name == "referencia":
        return ShortestPathBaseline()
    if name == "aleatoria":
        return RandomPolicy(seed=0)
    if model is None:
        raise SystemExit("la estrategia 'dqn' necesita --model")
    from sar_bot.agents.dqn import DQNPolicy

    return DQNPolicy.load(model)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None, help="archivo TOML (por defecto configs/base.toml)")
    parser.add_argument("--strategy", nargs="+", choices=STRATEGIES, default=["referencia"])
    parser.add_argument("--model", default=None, help="modelo DQN .zip")
    parser.add_argument("--split", choices=("validation", "test"), default="validation")
    parser.add_argument("--limit", type=int, default=None, help="evaluar solo los primeros N escenarios")
    parser.add_argument("--out", default=None, help="CSV de salida (por defecto outputs/eval_<config>_<split>.csv)")
    args = parser.parse_args()

    config = load_config(args.config)
    rows = []
    for name in args.strategy:
        policy_rows = evaluate(build_policy(name, args.model), config, split=args.split, limit=args.limit)
        print(format_summary(name, summarize(policy_rows)))
        rows.extend(policy_rows)

    out = Path(args.out) if args.out else PROJECT_ROOT / "outputs" / f"eval_{config.name}_{args.split}.csv"
    print(f"\nResultados por episodio en {write_csv(rows, out)}")


if __name__ == "__main__":
    main()
