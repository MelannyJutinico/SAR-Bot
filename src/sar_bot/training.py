"""Configuración del entrenamiento independiente de librerías de aprendizaje."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class StageExploration:
    """Traduce el progreso acumulado de SB3 a exploración local de una etapa.

    Con reset_num_timesteps=False, el progreso de SB3 incluye pasos anteriores.
    Cada nueva etapa puede necesitar explorar otra vez en lugar de continuar al 5%.
    """

    start_step: int
    steps: int
    initial: float = 0.6
    final: float = 0.05
    fraction: float = 0.8

    def __post_init__(self):
        if self.start_step < 0 or self.steps < 1:
            raise ValueError("El inicio debe ser no negativo y la duración positiva")
        if not all(isfinite(v) for v in (self.initial, self.final, self.fraction)):
            raise ValueError("Los parámetros de exploración deben ser finitos")
        if not 0 <= self.final <= self.initial <= 1 or not 0 < self.fraction <= 1:
            raise ValueError("Se requiere 0 <= final <= inicial <= 1 y 0 < fracción <= 1")

    def __call__(self, progress_remaining: float) -> float:
        cumulative_step = (self.start_step + self.steps) * (1 - progress_remaining)
        local_step = max(0.0, cumulative_step - self.start_step)
        progress = min(1.0, local_step / (self.steps * self.fraction))
        return self.initial + (self.final - self.initial) * progress
