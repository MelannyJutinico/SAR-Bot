"""Adaptador Gymnasium del motor de rescate.

- Acción: ``Discrete(25)``, la acción conjunta de ambos robots.
- Observación: vector fijo en [0, 1] (ver :mod:`sar_bot.env.observation`).
- ``terminated``: éxito o robot destruido. ``truncated``: límite de pasos.
- ``reset(options={"scenario": s})`` fuerza un escenario concreto; si no,
  se toma de la partición (``train``, ``validation`` o ``test``).
"""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from sar_bot.config import MAX_VICTIMS, ProjectConfig, load_config
from sar_bot.core.actions import N_JOINT_ACTIONS
from sar_bot.core.engine import Outcome, RescueSim
from sar_bot.core.scenario import Scenario
from sar_bot.env.observation import build_observation, heat_layer, observation_size
from sar_bot.env.reward import compute_reward
from sar_bot.env.sampling import ScenarioSampler, Split
from sar_bot.env.shaping import DistanceCache, potential


class RescueEnv(gym.Env):
    metadata = {"render_modes": ["ansi", "rgb_array"], "render_fps": 4}

    def __init__(
        self,
        config: ProjectConfig | None = None,
        split: Split = "train",
        render_mode: str | None = None,
    ) -> None:
        super().__init__()
        if render_mode is not None and render_mode not in self.metadata["render_modes"]:
            raise ValueError(f"render_mode no soportado: {render_mode}")
        self.config = config or load_config()
        self.sampler = ScenarioSampler(self.config, split)
        self.render_mode = render_mode
        self.action_space = spaces.Discrete(N_JOINT_ACTIONS)
        size = observation_size(self.sampler.shape, MAX_VICTIMS)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(size,), dtype=np.float32)
        self.sim: RescueSim | None = None
        self._heat: np.ndarray | None = None
        self._renderer = None
        self._distances = DistanceCache()
        self._potential = 0.0
        self.episode_return = 0.0
        self.task_return = 0.0

    @property
    def split(self) -> str:
        return self.sampler.split

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        scenario: Scenario | None = (options or {}).get("scenario")
        if scenario is None:
            scenario = self.sampler.sample(self.np_random)
        elif scenario.layout.shape != self.sampler.shape:
            raise ValueError("el escenario no tiene el tamaño de la observación del entorno")
        if self.sim is None:
            self.sim = RescueSim(scenario, self.config.rules)
        else:
            self.sim.reset(scenario)
        self._heat = heat_layer(scenario, self.config.rules)
        self._potential = potential(self.sim, self._distances, self.config.reward.shaping)
        self.episode_return = 0.0
        self.task_return = 0.0
        return self._observation(), self._info()

    def step(self, action):
        if self.sim is None:
            raise RuntimeError("llama a reset() antes de step()")
        result = self.sim.step_joint(int(action))
        task_reward = compute_reward(result, self.config.reward)
        next_potential = potential(self.sim, self._distances, self.config.reward.shaping)
        shaping = self.config.training.gamma * next_potential - self._potential
        self._potential = next_potential
        reward = task_reward + shaping
        self.task_return += task_reward
        self.episode_return += reward
        info = self._info()
        info["step_result"] = result
        info["reward_task"] = task_reward
        info["reward_shaping"] = shaping
        if result.done:
            info["is_success"] = result.outcome is Outcome.SUCCESS
            info["metrics"] = {
                **self.sim.episode_metrics(),
                "return": self.episode_return,
                "task_return": self.task_return,
            }
        return self._observation(), reward, result.terminated, result.truncated, info

    def _observation(self) -> np.ndarray:
        return build_observation(self.sim, self._heat, MAX_VICTIMS)

    def _info(self) -> dict[str, Any]:
        sim = self.sim
        return {
            "scenario_id": sim.scenario.scenario_id,
            "step": sim.step_count,
            "outcome": sim.outcome.value,
            "rescued": sim.rescued_count,
            "integrity": tuple(robot.integrity for robot in sim.robots),
        }

    def render(self):
        if self.render_mode is None or self.sim is None:
            return None
        if self.render_mode == "ansi":
            return self.sim.to_text()
        if self._renderer is None:
            from sar_bot.ui.renderer import Renderer

            self._renderer = Renderer(self.sampler.shape, self.config.rules)
        return self._renderer.render_array(self.sim)

    def close(self) -> None:
        self._renderer = None
