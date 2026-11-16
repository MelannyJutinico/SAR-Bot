"""Configuración del proyecto desde archivos TOML (``configs/*.toml``).

Cada archivo tiene las secciones ``[rules]``, ``[heat]``, ``[scenarios]``,
``[reward]`` y ``[training]``. Un archivo puede heredar de otro con
``extends = "base.toml"`` y redefinir solo algunas claves. Las claves
desconocidas producen error para evitar erratas silenciosas.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from sar_bot.core.heat import HeatFieldConfig
from sar_bot.core.rules import RulesConfig
from sar_bot.core.scenario import PROJECT_ROOT

CONFIGS_DIR = PROJECT_ROOT / "configs"
DEFAULT_CONFIG = CONFIGS_DIR / "base.toml"

MAX_VICTIMS = 2
"""Víctimas que caben en la observación de tamaño fijo."""


def _seed_range(value: Any) -> tuple[int, int]:
    start, end = (int(v) for v in value)
    if end <= start:
        raise ValueError(f"rango de semillas vacío: [{start}, {end})")
    return (start, end)


@dataclass(frozen=True)
class ScenarioConfig:
    layouts: tuple[str, ...] = ("edificio_a", "edificio_b", "edificio_c")
    n_victims: int = 2
    min_victim_base_distance: int = 2
    validation_seeds: tuple[int, int] = (100_000, 100_050)
    test_seeds: tuple[int, int] = (200_000, 200_100)

    def __post_init__(self) -> None:
        object.__setattr__(self, "layouts", tuple(self.layouts))
        if not self.layouts:
            raise ValueError("se necesita al menos un plano")
        if not 1 <= self.n_victims <= MAX_VICTIMS:
            raise ValueError(f"n_victims debe estar entre 1 y {MAX_VICTIMS}")
        val, test = _seed_range(self.validation_seeds), _seed_range(self.test_seeds)
        if val[0] < test[1] and test[0] < val[1]:
            raise ValueError("las semillas de validación y prueba no pueden solaparse")
        object.__setattr__(self, "validation_seeds", val)
        object.__setattr__(self, "test_seeds", test)


@dataclass(frozen=True)
class RewardConfig:
    step: float = -0.05
    damage: float = -0.1
    pickup: float = 2.0
    delivery: float = 10.0
    success: float = 20.0
    destruction: float = -20.0
    blocked: float = -0.1
    shaping: float = 1.0
    """Coeficiente de la guía por potencial (0 la desactiva); ver env/shaping.py."""


@dataclass(frozen=True)
class TrainingConfig:
    total_timesteps: int = 300_000
    seed: int = 0
    device: str = "cpu"
    learning_rate: float = 5e-4
    buffer_size: int = 100_000
    learning_starts: int = 1_000
    batch_size: int = 128
    gamma: float = 0.95
    train_freq: int = 4
    gradient_steps: int = 1
    target_update_interval: int = 500
    exploration_fraction: float = 0.3
    exploration_initial_eps: float = 1.0
    exploration_final_eps: float = 0.05
    net_arch: tuple[int, ...] = (256, 256)
    eval_freq: int = 10_000
    threads: int = 0
    """Hilos de torch; 0 usa el valor por defecto. Útil al entrenar varias corridas a la vez."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "net_arch", tuple(int(n) for n in self.net_arch))


@dataclass(frozen=True)
class ProjectConfig:
    rules: RulesConfig = field(default_factory=RulesConfig)
    heat: HeatFieldConfig = field(default_factory=HeatFieldConfig)
    scenarios: ScenarioConfig = field(default_factory=ScenarioConfig)
    reward: RewardConfig = field(default_factory=RewardConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    name: str = "base"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SECTIONS: dict[str, type] = {
    "rules": RulesConfig,
    "heat": HeatFieldConfig,
    "scenarios": ScenarioConfig,
    "reward": RewardConfig,
    "training": TrainingConfig,
}


def _read_toml(path: Path, chain: tuple[Path, ...] = ()) -> dict[str, dict[str, Any]]:
    path = path.resolve()
    if path in chain:
        raise ValueError(f"herencia circular entre configuraciones: {path}")
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    parent = data.pop("extends", None)
    merged: dict[str, dict[str, Any]] = {}
    if parent is not None:
        merged = _read_toml(path.parent / parent, chain + (path,))
    for section, values in data.items():
        if not isinstance(values, dict):
            raise ValueError(f"{path.name}: '{section}' debe ser una sección [..]")
        merged.setdefault(section, {}).update(values)
    return merged


def _parse_override(item: str) -> tuple[str, str, Any]:
    """``"training.gamma=0.95"`` → ``("training", "gamma", 0.95)``; el valor se lee como TOML."""
    key, sep, value = item.partition("=")
    section, dot, name = key.strip().partition(".")
    if not sep or not dot or not name:
        raise ValueError(f"cambio inválido {item!r}; formato: seccion.clave=valor")
    try:
        parsed = tomllib.loads(f"v = {value.strip()}")["v"]
    except tomllib.TOMLDecodeError:
        parsed = value.strip()
    return section, name, parsed


def load_config(path: str | Path | None = None, overrides: list[str] | None = None) -> ProjectConfig:
    """Carga una configuración; sin ruta usa ``configs/base.toml``.

    ``overrides`` aplica cambios puntuales como ``["training.gamma=0.95"]``.
    """
    path = Path(path) if path is not None else DEFAULT_CONFIG
    raw = _read_toml(path)
    for item in overrides or []:
        section, name, value = _parse_override(item)
        raw.setdefault(section, {})[name] = value
    unknown_sections = set(raw) - set(_SECTIONS)
    if unknown_sections:
        raise ValueError(f"{path.name}: secciones desconocidas {sorted(unknown_sections)}")
    kwargs: dict[str, Any] = {}
    for section, cls in _SECTIONS.items():
        values = raw.get(section, {})
        unknown = set(values) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"{path.name}: claves desconocidas en [{section}]: {sorted(unknown)}")
        kwargs[section] = cls(**values)
    return ProjectConfig(name=path.stem, **kwargs)
