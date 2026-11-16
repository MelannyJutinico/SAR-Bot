"""Núcleo del simulador: plano, acciones, calor, escenarios y motor."""

from sar_bot.core.actions import (
    N_ACTIONS,
    N_JOINT_ACTIONS,
    N_ROBOTS,
    Action,
    decode_joint,
    encode_joint,
)
from sar_bot.core.engine import (
    MoveResolution,
    Outcome,
    RescueSim,
    RobotState,
    StepResult,
    VictimState,
    VictimStatus,
    resolve_moves,
)
from sar_bot.core.grid import Layout, Pos, manhattan
from sar_bot.core.heat import HeatFieldConfig, temperature_field
from sar_bot.core.rules import DEFAULT_DAMAGE_BANDS, RulesConfig, damage_rate
from sar_bot.core.scenario import (
    LAYOUTS_DIR,
    Scenario,
    estimate_viability,
    generate_scenario,
    load_layouts,
    min_damage_path,
)

__all__ = [
    "DEFAULT_DAMAGE_BANDS",
    "LAYOUTS_DIR",
    "N_ACTIONS",
    "N_JOINT_ACTIONS",
    "N_ROBOTS",
    "Action",
    "HeatFieldConfig",
    "Layout",
    "MoveResolution",
    "Outcome",
    "Pos",
    "RescueSim",
    "RobotState",
    "RulesConfig",
    "Scenario",
    "StepResult",
    "VictimState",
    "VictimStatus",
    "damage_rate",
    "decode_joint",
    "encode_joint",
    "estimate_viability",
    "generate_scenario",
    "load_layouts",
    "manhattan",
    "min_damage_path",
    "resolve_moves",
    "temperature_field",
]
