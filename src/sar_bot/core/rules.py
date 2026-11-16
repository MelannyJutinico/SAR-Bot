"""Reglas numéricas del simulador: daño térmico, integridad y tiempo.

El daño depende de la temperatura de la celda donde termina el robot y
del tiempo simulado de exposición::

    daño_i      = tasa(temperatura_en_posición_final_i) × delta_t
    integridad_i = max(0, integridad_i - daño_i)

Son reglas abstractas del simulador, no umbrales reales de seguridad.
"""

from __future__ import annotations

from dataclasses import dataclass

DamageBand = tuple[float, float]
"""``(temperatura_mínima, tasa_de_daño)``: la tasa aplica desde esa temperatura."""

DEFAULT_DAMAGE_BANDS: tuple[DamageBand, ...] = (
    (40.0, 2.0),
    (60.0, 5.0),
    (80.0, 10.0),
)
"""T < 40 → 0; 40 ≤ T < 60 → 2; 60 ≤ T < 80 → 5; T ≥ 80 → 10."""


def validate_damage_bands(bands: tuple[DamageBand, ...]) -> None:
    """Exige umbrales estrictamente crecientes y tasas no negativas y no decrecientes."""
    previous_threshold = float("-inf")
    previous_rate = 0.0
    for threshold, rate in bands:
        if threshold <= previous_threshold:
            raise ValueError("los umbrales de daño deben ser estrictamente crecientes")
        if rate < previous_rate:
            raise ValueError("las tasas de daño no pueden disminuir al subir la temperatura")
        previous_threshold, previous_rate = threshold, rate


def damage_rate(temperature: float, bands: tuple[DamageBand, ...] = DEFAULT_DAMAGE_BANDS) -> float:
    """Tasa de daño por unidad de tiempo a una temperatura dada.

    Cada franja cubre ``[umbral, siguiente_umbral)``, de modo que no hay
    huecos ni solapamientos. Por debajo del primer umbral la tasa es 0.
    """
    rate = 0.0
    for threshold, band_rate in bands:
        if temperature >= threshold:
            rate = band_rate
        else:
            break
    return rate


@dataclass(frozen=True)
class RulesConfig:
    """Parámetros de reglas compartidos por motor, entorno y evaluación."""

    initial_integrity: float = 100.0
    max_steps: int = 100
    delta_t: float = 1.0
    damage_bands: tuple[DamageBand, ...] = DEFAULT_DAMAGE_BANDS

    def __post_init__(self) -> None:
        if self.initial_integrity <= 0:
            raise ValueError("la integridad inicial debe ser positiva")
        if self.max_steps <= 0:
            raise ValueError("el límite de pasos debe ser positivo")
        if self.delta_t <= 0:
            raise ValueError("delta_t debe ser positivo")
        bands = tuple((float(t), float(r)) for t, r in self.damage_bands)
        validate_damage_bands(bands)
        object.__setattr__(self, "damage_bands", bands)

    def damage_for(self, temperature: float) -> float:
        """Daño de un paso global a la temperatura dada."""
        return damage_rate(temperature, self.damage_bands) * self.delta_t
