"""Entrenamiento DQN con evaluación periódica en validación.

Salidas (ignoradas por git):

- ``models/<corrida>/final_model.zip``: modelo al terminar.
- ``models/<corrida>/best_model.zip``: mejor retorno medio en validación.
- ``models/<corrida>/metadata.json``: configuración, versiones y tiempos.
- ``runs/<corrida>/``: registros de Monitor y evaluaciones (``evaluations.npz``).
"""

from __future__ import annotations

import json
import platform
import time
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.monitor import Monitor

from sar_bot.agents.dqn import make_dqn
from sar_bot.config import ProjectConfig
from sar_bot.core.scenario import PROJECT_ROOT
from sar_bot.env.rescue_env import RescueEnv

MODELS_DIR = PROJECT_ROOT / "models"
RUNS_DIR = PROJECT_ROOT / "runs"


def _versions() -> dict[str, str]:
    packages = ("numpy", "gymnasium", "stable-baselines3", "torch", "pygame")
    return {"python": platform.python_version(), **{p: version(p) for p in packages}}


def train(
    config: ProjectConfig,
    run_name: str,
    *,
    total_timesteps: int | None = None,
    models_dir: str | Path | None = None,
    runs_dir: str | Path | None = None,
    verbose: int = 1,
) -> Path:
    """Entrena y guarda el modelo; devuelve el directorio del modelo."""
    model_dir = Path(models_dir or MODELS_DIR) / run_name
    run_dir = Path(runs_dir or RUNS_DIR) / run_name
    model_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    timesteps = int(total_timesteps or config.training.total_timesteps)

    train_env = Monitor(RescueEnv(config, split="train"), str(run_dir / "train"), info_keywords=("is_success",))
    eval_env = Monitor(RescueEnv(config, split="validation"))
    n_validation = len(eval_env.unwrapped.sampler.fixed)

    model = make_dqn(train_env, config.training, verbose=verbose)
    callback = EvalCallback(
        eval_env,
        n_eval_episodes=n_validation,
        eval_freq=config.training.eval_freq,
        best_model_save_path=str(model_dir),
        log_path=str(run_dir),
        deterministic=True,
        verbose=verbose,
    )

    started = datetime.now().isoformat(timespec="seconds")
    clock = time.perf_counter()
    model.learn(total_timesteps=timesteps, callback=callback)
    model.save(model_dir / "final_model")

    metadata = {
        "run_name": run_name,
        "config_name": config.name,
        "config": config.to_dict(),
        "total_timesteps": timesteps,
        "validation_episodes": n_validation,
        "best_mean_reward": None if callback.best_mean_reward == float("-inf") else callback.best_mean_reward,
        "started": started,
        "duration_s": round(time.perf_counter() - clock, 1),
        "versions": _versions(),
    }
    (model_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    train_env.close()
    eval_env.close()
    return model_dir
