"""Entrena el controlador DQN centralizado.

Ejemplos:
    python scripts/train.py
    python scripts/train.py --config configs/sin_calor.toml --timesteps 100000
    python scripts/train.py --config configs/base.toml --seed 1 --name base_s1
    python scripts/train.py --set training.train_freq=1 --set training.learning_rate=0.00025
    python scripts/train.py --config configs/base.toml --init-model models/etapa2_s0/best_model.zip \\
        --set training.exploration_initial_eps=0.3
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
    parser.add_argument("--threads", type=int, default=None, help="hilos de torch (útil con varias corridas a la vez)")
    parser.add_argument("--init-model", default=None, help="partir de los pesos de un modelo previo (.zip)")
    parser.add_argument(
        "--set", action="append", default=[], metavar="SECCION.CLAVE=VALOR",
        help="cambia un valor de la configuración, p. ej. --set training.gamma=0.95 (repetible)",
    )
    args = parser.parse_args()

    config = load_config(args.config, overrides=args.set)
    overrides = {}
    if args.seed is not None:
        overrides["seed"] = args.seed
    if args.threads is not None:
        overrides["threads"] = args.threads
    if overrides:
        config = dataclasses.replace(config, training=dataclasses.replace(config.training, **overrides))
    run_name = args.name or f"{config.name}_s{config.training.seed}"

    model_dir = train(config, run_name, total_timesteps=args.timesteps, init_model=args.init_model)
    print(f"\nModelo guardado en {model_dir}")
    print(f"Evaluar con: python scripts/evaluate.py --config {args.config or 'configs/base.toml'} "
          f"--strategy referencia dqn --model {model_dir / 'best_model.zip'}")


if __name__ == "__main__":
    main()
