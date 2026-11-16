"""Adaptador Gymnasium, observación, recompensa y particiones de escenarios."""

from gymnasium.envs.registration import register, registry

from sar_bot.env.observation import build_observation, observation_size
from sar_bot.env.rescue_env import RescueEnv
from sar_bot.env.reward import compute_reward
from sar_bot.env.sampling import SPLITS, ScenarioSampler, scenario_key

ENV_ID = "SARBot-v0"
if ENV_ID not in registry:
    register(id=ENV_ID, entry_point="sar_bot.env.rescue_env:RescueEnv")

__all__ = [
    "ENV_ID",
    "SPLITS",
    "RescueEnv",
    "ScenarioSampler",
    "build_observation",
    "compute_reward",
    "observation_size",
    "scenario_key",
]
