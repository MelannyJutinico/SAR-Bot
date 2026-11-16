"""Evaluación por episodio con las mismas reglas para todas las estrategias.

Cada fila registra lo pedido en docs/CONTEXTO.md §9: escenario, semilla,
estrategia, víctimas rescatadas, éxito, causa de finalización, pasos,
daño por robot y total, integridad final y retorno.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from pathlib import Path

from sar_bot.agents.base import Policy
from sar_bot.config import ProjectConfig
from sar_bot.core.scenario import Scenario
from sar_bot.env.rescue_env import RescueEnv
from sar_bot.env.sampling import Split


def run_episode(env: RescueEnv, policy: Policy, scenario: Scenario | None = None) -> dict[str, object]:
    options = {"scenario": scenario} if scenario is not None else None
    observation, _ = env.reset(options=options)
    policy.reset(env.sim)
    while True:
        action = policy.act(observation, env.sim)
        observation, _, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break
    return {
        "strategy": policy.name,
        "split": env.split,
        "layout": env.sim.layout.name,
        **info["metrics"],
    }


def evaluate(
    policy: Policy,
    config: ProjectConfig,
    split: Split = "validation",
    limit: int | None = None,
) -> list[dict[str, object]]:
    """Ejecuta la estrategia en la lista fija de validación o prueba."""
    if split == "train":
        raise ValueError("la evaluación usa las particiones fijas 'validation' o 'test'")
    env = RescueEnv(config, split=split)
    scenarios: Sequence[Scenario] = env.sampler.fixed[:limit] if limit else env.sampler.fixed
    return [run_episode(env, policy, scenario) for scenario in scenarios]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarize(rows: Iterable[dict[str, object]]) -> dict[str, object]:
    rows = list(rows)
    successes = [r for r in rows if r["success"]]
    return {
        "episodes": len(rows),
        "success_rate": _mean([float(r["success"]) for r in rows]),
        "destroyed_rate": _mean([float(r["outcome"] == "robot_destruido") for r in rows]),
        "timeout_rate": _mean([float(r["outcome"] == "limite_de_pasos") for r in rows]),
        "rescued_mean": _mean([float(r["rescued"]) for r in rows]),
        "damage_total_mean": _mean([float(r["damage_total"]) for r in rows]),
        "steps_mean": _mean([float(r["steps"]) for r in rows]),
        # Duración comparada solo entre misiones exitosas, para no favorecer fracasos tempranos.
        "steps_mean_success": _mean([float(r["steps"]) for r in successes]),
        "damage_total_mean_success": _mean([float(r["damage_total"]) for r in successes]),
        "return_mean": _mean([float(r["return"]) for r in rows]),
    }


def format_summary(name: str, summary: dict[str, object]) -> str:
    def fmt(value: object, pct: bool = False) -> str:
        if value is None:
            return "-"
        return f"{value:.1%}" if pct else f"{value:.2f}"

    return (
        f"{name:<12} episodios={summary['episodes']:<4} "
        f"éxito={fmt(summary['success_rate'], True):>7} "
        f"destruido={fmt(summary['destroyed_rate'], True):>7} "
        f"límite={fmt(summary['timeout_rate'], True):>7} "
        f"rescatadas={fmt(summary['rescued_mean'])} "
        f"daño={fmt(summary['damage_total_mean'])} "
        f"pasos(éxito)={fmt(summary['steps_mean_success'])} "
        f"daño(éxito)={fmt(summary['damage_total_mean_success'])} "
        f"retorno={fmt(summary['return_mean'])}"
    )


def write_csv(rows: Sequence[dict[str, object]], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("no hay filas para exportar")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path
