"""Controlador centralizado DQN (Stable-Baselines3) sobre las 25 acciones conjuntas."""

from __future__ import annotations

from pathlib import Path

import gymnasium as gym
import numpy as np
from stable_baselines3 import DQN

from sar_bot.config import TrainingConfig
from sar_bot.core.engine import RescueSim


def make_dqn(env: gym.Env, training: TrainingConfig, verbose: int = 0) -> DQN:
    return DQN(
        "MlpPolicy",
        env,
        learning_rate=training.learning_rate,
        buffer_size=training.buffer_size,
        learning_starts=training.learning_starts,
        batch_size=training.batch_size,
        gamma=training.gamma,
        train_freq=training.train_freq,
        gradient_steps=training.gradient_steps,
        target_update_interval=training.target_update_interval,
        exploration_fraction=training.exploration_fraction,
        exploration_initial_eps=training.exploration_initial_eps,
        exploration_final_eps=training.exploration_final_eps,
        policy_kwargs={"net_arch": list(training.net_arch)},
        seed=training.seed,
        device=training.device,
        verbose=verbose,
    )


class DQNPolicy:
    """Política aprendida: usa solo la observación, con acción greedy (determinista)."""

    name = "dqn"

    def __init__(self, model: DQN) -> None:
        self.model = model

    @classmethod
    def load(cls, path: str | Path, device: str = "cpu") -> DQNPolicy:
        return cls(DQN.load(str(path), device=device))

    def reset(self, sim: RescueSim) -> None:
        pass

    def act(self, observation: np.ndarray, sim: RescueSim) -> int:
        action, _ = self.model.predict(observation, deterministic=True)
        return int(action)
