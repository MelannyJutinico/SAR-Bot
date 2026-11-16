"""Interfaz común de estrategias: referencia programada, aleatoria y DQN."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from sar_bot.core.engine import RescueSim


class Policy(Protocol):
    name: str

    def reset(self, sim: RescueSim) -> None:
        """Se llama al iniciar cada episodio."""

    def act(self, observation: np.ndarray, sim: RescueSim) -> int:
        """Devuelve la acción conjunta en [0, 25).

        Las estrategias aprendidas usan solo ``observation``; la referencia
        programada lee el estado del motor (``sim``), sin modificarlo.
        """
