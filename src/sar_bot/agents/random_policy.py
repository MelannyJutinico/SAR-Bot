from __future__ import annotations

import numpy as np

from sar_bot.core.actions import N_JOINT_ACTIONS
from sar_bot.core.engine import RescueSim


class RandomPolicy:
    """Acción conjunta uniforme; sirve como cota inferior y prueba de humo."""

    name = "aleatoria"

    def __init__(self, seed: int = 0) -> None:
        self._seed = seed
        self._rng = np.random.default_rng(seed)

    def reset(self, sim: RescueSim) -> None:
        pass

    def act(self, observation: np.ndarray, sim: RescueSim) -> int:
        return int(self._rng.integers(N_JOINT_ACTIONS))
