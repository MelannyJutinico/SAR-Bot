"""Estados iniciales de entrenamiento: completar uno, dos y tres rescates.

La evaluación y la interfaz usan RescueEnv normal. Las personas inicialmente
entregadas solo simplifican el objetivo de las primeras etapas de entrenamiento.
"""

from sar_bot.core import MissionState
from .rescue_env import RescueEnv


class CurriculumRescueEnv(RescueEnv):
    def __init__(self, scenarios, rewards=None, observation_mode="sensors", pending_victims=None):
        super().__init__(scenarios, rewards, observation_mode)
        self.pending_victims = self.victim_count if pending_victims is None else pending_victims
        if type(self.pending_victims) is not int or not 1 <= self.pending_victims <= self.victim_count:
            raise ValueError("pending_victims debe estar entre uno y la cantidad del perfil")

    def reset(self, *, seed=None, options=None):
        observation, info = super().reset(seed=seed, options=options)
        if self.pending_victims == self.victim_count:
            return observation, info
        pending = set(self.np_random.choice(self.victim_count, self.pending_victims, replace=False).tolist())
        rescued = frozenset(set(range(self.victim_count)) - pending)
        self.simulation.state = MissionState(self.simulation.state.robots, rescued=rescued)
        return self.observation(), {**self._info(), "curriculum_initial_rescued": sorted(rescued)}
