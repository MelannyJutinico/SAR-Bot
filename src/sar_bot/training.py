"""Entrenamiento DQN con evaluación periódica en validación.

Salidas (ignoradas por git):

- ``models/<corrida>/best_model.zip``: mejor modelo en validación, elegido por
  tasa de éxito y, a igualdad, por retorno de la tarea (sin la guía).
- ``models/<corrida>/final_model.zip``: modelo al terminar.
- ``models/<corrida>/metadata.json``: configuración, versiones, tiempos y
  resumen de la mejor evaluación.
- ``runs/<corrida>/``: registro de Monitor y ``evaluations.npz`` con la curva
  de validación (éxito, retorno de la tarea, daño y pasos).

No se elige por el retorno con guía: con γ < 1, la guía por potencial suma
``(1 − γ)·trabajo_pendiente`` por cada paso de espera, de modo que el retorno
sin descontar puede premiar políticas que se quedan quietas lejos del objetivo.
"""

from __future__ import annotations

import json
import math
import platform
import time
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor

from sar_bot.agents.dqn import DQNPolicy, make_dqn
from sar_bot.config import ProjectConfig
from sar_bot.core.scenario import PROJECT_ROOT
from sar_bot.env.rescue_env import RescueEnv
from sar_bot.evaluation import run_episode, summarize

MODELS_DIR = PROJECT_ROOT / "models"
RUNS_DIR = PROJECT_ROOT / "runs"


def _versions() -> dict[str, str]:
    packages = ("numpy", "gymnasium", "stable-baselines3", "torch", "pygame")
    return {"python": platform.python_version(), **{p: version(p) for p in packages}}


def selection_key(summary: dict[str, object]) -> tuple[float, float]:
    """Orden para elegir el mejor modelo: primero éxito, luego retorno de la tarea."""
    success = summary.get("success_rate")
    task_return = summary.get("task_return_mean")
    return (
        -math.inf if success is None else float(success),
        -math.inf if task_return is None else float(task_return),
    )


class ValidationCallback(BaseCallback):
    """Evalúa la política greedy en toda la validación cada ``eval_freq`` pasos."""

    def __init__(self, eval_env: RescueEnv, eval_freq: int, model_dir: Path, run_dir: Path, verbose: int = 1):
        super().__init__(verbose)
        self.eval_env = eval_env
        self.eval_freq = eval_freq
        self.model_dir = model_dir
        self.run_dir = run_dir
        self.best_key: tuple[float, float] = (-math.inf, -math.inf)
        self.best: dict[str, object] | None = None
        self.history: dict[str, list[float]] = {
            k: [] for k in ("timesteps", "success_rate", "task_return", "damage", "steps_success")
        }

    def _on_step(self) -> bool:
        if self.eval_freq > 0 and self.n_calls % self.eval_freq == 0:
            self.evaluate()
        return True

    def evaluate(self) -> dict[str, object]:
        policy = DQNPolicy(self.model)
        rows = [run_episode(self.eval_env, policy, s) for s in self.eval_env.sampler.fixed]
        summary = summarize(rows)
        values = {
            "timesteps": self.num_timesteps,
            "success_rate": summary["success_rate"],
            "task_return": summary["task_return_mean"],
            "damage": summary["damage_total_mean"],
            "steps_success": summary["steps_mean_success"] if summary["steps_mean_success"] is not None else math.nan,
        }
        for key, value in values.items():
            self.history[key].append(float(value))
        np.savez(self.run_dir / "evaluations.npz", **{k: np.asarray(v) for k, v in self.history.items()})
        for key in ("success_rate", "task_return", "damage"):
            self.logger.record(f"eval/{key}", values[key])

        improved = selection_key(summary) > self.best_key
        if improved:
            self.best_key = selection_key(summary)
            self.best = {"timesteps": self.num_timesteps, **summary}
            self.model.save(self.model_dir / "best_model")
        if self.verbose:
            mark = "  * mejor" if improved else ""
            print(
                f"[validación] {self.num_timesteps:>8} pasos  éxito={values['success_rate']:6.1%}  "
                f"retorno_tarea={values['task_return']:7.2f}  daño={values['damage']:6.2f}{mark}",
                flush=True,
            )
        return summary


def train(
    config: ProjectConfig,
    run_name: str,
    *,
    total_timesteps: int | None = None,
    init_model: str | Path | None = None,
    models_dir: str | Path | None = None,
    runs_dir: str | Path | None = None,
    verbose: int = 1,
) -> Path:
    """Entrena y guarda el modelo; devuelve el directorio del modelo.

    Con ``init_model`` se parte de los pesos de un modelo previo (por ejemplo,
    de la etapa anterior) y se sigue con los hiperparámetros de ``config``.
    """
    model_dir = Path(models_dir or MODELS_DIR) / run_name
    run_dir = Path(runs_dir or RUNS_DIR) / run_name
    model_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    timesteps = int(total_timesteps or config.training.total_timesteps)
    if config.training.threads > 0:
        import torch

        torch.set_num_threads(config.training.threads)

    train_env = Monitor(RescueEnv(config, split="train"), str(run_dir / "train"), info_keywords=("is_success",))
    eval_env = RescueEnv(config, split="validation")

    model = make_dqn(train_env, config.training, verbose=0)
    if init_model is not None:
        model.set_parameters(str(init_model), exact_match=True, device=config.training.device)
    callback = ValidationCallback(eval_env, config.training.eval_freq, model_dir, run_dir, verbose=verbose)

    started = datetime.now().isoformat(timespec="seconds")
    clock = time.perf_counter()
    model.learn(total_timesteps=timesteps, callback=callback)
    model.save(model_dir / "final_model")
    if callback.best is None:
        callback.evaluate()

    metadata = {
        "run_name": run_name,
        "config_name": config.name,
        "config": config.to_dict(),
        "init_model": str(init_model) if init_model is not None else None,
        "total_timesteps": timesteps,
        "validation_episodes": len(eval_env.sampler.fixed),
        "selection": "max (success_rate, task_return_mean) en validación",
        "best": callback.best,
        "started": started,
        "duration_s": round(time.perf_counter() - clock, 1),
        "versions": _versions(),
    }
    (model_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    train_env.close()
    eval_env.close()
    return model_dir
