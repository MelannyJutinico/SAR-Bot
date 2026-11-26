"""Contrato común de estrategias para interfaz, evaluación y herramientas del equipo."""

from pathlib import Path
from typing import Protocol

from sar_bot.core import MissionState, RescueSimulation
from .reference import RandomPolicy, ShortestPathPolicy, ThermalPathPolicy


class Policy(Protocol):
    def act(self, state: MissionState) -> int: ...


def create_policy(simulation: RescueSimulation, strategy: str, *, model_path: str | Path | None = None,
                  seed: int = 0, thermal_damage_weight: float = 2.0) -> Policy:
    """Nueva política por episodio. No cambia estrategia si una política falla."""
    if strategy == "shortest":
        return ShortestPathPolicy(simulation)
    if strategy == "thermal":
        return ThermalPathPolicy(simulation, damage_weight=thermal_damage_weight)
    if strategy == "random":
        return RandomPolicy(simulation, seed)
    if strategy == "dqn":
        if model_path is None:
            raise ValueError("La estrategia DQN requiere un modelo guardado")
        from .dqn import DQNPolicy
        return DQNPolicy(simulation, model_path)
    raise ValueError(f"Estrategia desconocida: {strategy}")
