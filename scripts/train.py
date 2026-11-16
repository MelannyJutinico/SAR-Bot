"""Entrena el controlador DQN centralizado.

Ejemplos:
    python scripts/train.py
    python scripts/train.py --config configs/sin_calor.toml --timesteps 100000
    python scripts/train.py --config configs/base.toml --seed 1 --name base_s1
"""

from __future__ import annotations

import argparse
import dataclasses
import sys

from sar_bot.config import load_config
from sar_bot.training import train


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None, help="archivo TOML (por defecto configs/base.toml)")
    parser.add_argument("--timesteps", type=int, default=None, help="pasos de entrenamiento")
    parser.add_argument("--seed", type=int, default=None, help="semilla de entrenamiento")
    parser.add_argument("--name", default=None, help="nombre de la corrida (por defecto <config>_s<semilla>)")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.seed is not None:
        config = dataclasses.replace(config, training=dataclasses.replace(config.training, seed=args.seed))
    run_name = args.name or f"{config.name}_s{config.training.seed}"

    model_dir = train(config, run_name, total_timesteps=args.timesteps)
    best = model_dir / "best_model.zip"
    model_path = best if best.exists() else model_dir / "final_model.zip"
    print(f"\nModelo guardado en {model_dir}")
    print(f"Evaluar con: python scripts/evaluate.py --config {args.config or 'configs/base.toml'} "
          f"--strategy referencia dqn --model {model_path}")


if __name__ == "__main__":
    main()
