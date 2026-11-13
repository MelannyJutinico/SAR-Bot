"""Carga de un controlador entrenado para usarlo con el motor y la interfaz."""

from sar_bot.env import RescueEnv
from sar_bot.learning import observation_mode_for_model


class DQNPolicy:
    def __init__(self, simulation, model_path):
        from stable_baselines3 import DQN
        import torch

        torch.set_num_threads(1)
        self.model = DQN.load(model_path, device="cpu")
        self.env = RescueEnv([simulation.scenario],
                             observation_mode=observation_mode_for_model(self.model, simulation.scenario))
        self.env.simulation = simulation
        if self.model.observation_space.shape != self.env.observation_space.shape:
            raise ValueError("El modelo no coincide con las dimensiones del escenario")
        if self.model.action_space.n != 25:
            raise ValueError("El modelo no corresponde a las 25 acciones conjuntas")

    def act(self, state):
        action, _ = self.model.predict(self.env.observation(), deterministic=True)
        return int(action)
