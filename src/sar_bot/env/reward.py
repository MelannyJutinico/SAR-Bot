"""Recompensa compartida calculada a partir de los eventos del motor.

No recalcula reglas: usa el ``StepResult`` de cada paso global.
"""

from __future__ import annotations

from sar_bot.config import RewardConfig
from sar_bot.core.engine import Outcome, StepResult


def compute_reward(result: StepResult, config: RewardConfig) -> float:
    reward = config.step
    reward += config.damage * sum(result.damage)
    reward += config.pickup * sum(p is not None for p in result.picked_up)
    reward += config.delivery * sum(d is not None for d in result.delivered)
    reward += config.blocked * (sum(result.blocked_by_wall) + sum(result.blocked_by_robot))
    if result.outcome is Outcome.SUCCESS:
        reward += config.success
    elif result.outcome is Outcome.DESTROYED:
        reward += config.destruction
    return float(reward)
