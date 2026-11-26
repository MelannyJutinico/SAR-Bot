"""DQN con restricciones de movimiento, sin objetivos ni rutas programadas.

La misma máscara se usa al explorar, actuar y calcular el máximo de Bellman.
Se deriva de posiciones, base y sensores de transitabilidad ya observados.
"""

import numpy as np
import torch
from stable_baselines3 import DQN
from stable_baselines3.dqn.policies import DQNPolicy, QNetwork
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

from sar_bot.core.simulation import OFFSETS


class RescueFeaturesExtractor(BaseFeaturesExtractor):
    """Prioriza estado y sensores existentes; no calcula acciones ni objetivos.

    Las matrices estáticas ya están resumidas por sensores de transitabilidad,
    temperatura y distancias. Las distancias se expresan en escala del lado.
    """
    def __init__(self, observation_space, rescue_profile):
        if rescue_profile["mode"] != "sensors":
            raise ValueError("La representación compacta requiere sensores")
        self.map_size = 2 * rescue_profile["width"] * rescue_profile["height"]
        self.state_size = 11 + 7 * rescue_profile["victims"]
        self.sensor_width = 4 + rescue_profile["victims"]
        self.distance_scale = max(rescue_profile["width"], rescue_profile["height"])
        super().__init__(observation_space, observation_space.shape[0] - self.map_size)

    def forward(self, observations):
        dynamic = observations[:, self.map_size:self.map_size+self.state_size]
        local = observations[:, self.map_size+self.state_size:].reshape(-1, 2, 5, self.sensor_width)
        sensors = torch.cat((local[..., :3], local[..., 3:] * self.distance_scale), dim=-1)
        return torch.cat((dynamic, sensors.flatten(1)), dim=1)


def joint_action_mask(observations, profile):
    """Booleanos [batch,25]: intentos transitables, sin coincidencia ni intercambio."""
    if profile["mode"] != "sensors" or observations.shape[-1] != profile["observation_size"]:
        raise ValueError("La máscara requiere el perfil de sensores declarado")
    obs = observations.reshape(-1, observations.shape[-1])
    width, height, victims = profile["width"], profile["height"], profile["victims"]
    cells = width * height
    scale = obs.new_tensor([max(1, width - 1), max(1, height - 1)])
    base = torch.round(obs[:, 2*cells:2*cells+2] * scale)
    start = 2*cells + 2*(1+victims)
    positions = torch.round(obs[:, start:start+4].reshape(-1, 2, 2) * scale)
    sensor_start = 2*cells + 11 + 7*victims
    legal = obs[:, sensor_start:].reshape(-1, 2, 5, 4+victims)[..., 0] > 0.5
    candidates = positions[:, :, None, :] + obs.new_tensor(OFFSETS)[None, None, :, :]
    first, second = candidates[:, 0, :, None, :], candidates[:, 1, None, :, :]
    same = (first == second).all(dim=-1)
    shared_base = (first == base[:, None, None, :]).all(dim=-1)
    swap = ((first == positions[:, 1, None, None, :]).all(dim=-1)
            & (second == positions[:, 0, None, None, :]).all(dim=-1)
            & (positions[:, 0] != positions[:, 1]).any(dim=-1)[:, None, None])
    return (legal[:, 0, :, None] & legal[:, 1, None, :]
            & ~(same & ~shared_base) & ~swap).reshape(-1, 25)


class MaskedQNetwork(QNetwork):
    def __init__(self, *args, rescue_profile, **kwargs):
        super().__init__(*args, **kwargs)
        self.rescue_profile = rescue_profile

    def forward(self, obs):
        values = super().forward(obs)
        return values.masked_fill(~joint_action_mask(obs, self.rescue_profile), -1e9)


class MaskedDQNPolicy(DQNPolicy):
    def __init__(self, *args, rescue_profile, **kwargs):
        self.rescue_profile = rescue_profile
        super().__init__(*args, **kwargs)

    def make_q_net(self):
        args = self._update_features_extractor(self.net_args, features_extractor=None)
        return MaskedQNetwork(**args, rescue_profile=self.rescue_profile).to(self.device)

    def _get_constructor_parameters(self):
        return {**super()._get_constructor_parameters(), "rescue_profile": self.rescue_profile}


class MaskedDQN(DQN):
    def _random_valid_actions(self, observation):
        tensor, vectorized = self.policy.obs_to_tensor(observation)
        valid = joint_action_mask(tensor, self.policy.rescue_profile).cpu().numpy()
        actions = np.array([np.random.choice(np.flatnonzero(row)) for row in valid])
        return actions if vectorized else actions.reshape(())

    def predict(self, observation, state=None, episode_start=None, deterministic=False):
        if not deterministic and np.random.rand() < self.exploration_rate:
            return self._random_valid_actions(observation), state
        return super().predict(observation, state, episode_start, deterministic=True)

    def _sample_action(self, learning_starts, action_noise=None, n_envs=1):
        if self.num_timesteps < learning_starts:
            actions = self._random_valid_actions(self._last_obs)
            return actions, actions.copy()
        return super()._sample_action(learning_starts, action_noise, n_envs)
