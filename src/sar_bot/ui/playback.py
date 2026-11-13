"""Preparación de episodios y reloj visual, sin dependencia de Pygame."""

from dataclasses import dataclass
from math import isfinite
from pathlib import Path

from sar_bot.agents import create_policy
from sar_bot.core import MissionState, RescueSimulation, Scenario


@dataclass(frozen=True)
class Episode:
    scenario: Scenario
    states: tuple[MissionState, ...]
    actions: tuple[int, ...]

    @property
    def scenario_id(self):
        return self.scenario.fingerprint()

    @property
    def configuration_id(self):
        return self.scenario.configuration_id


def prepare_episode(scenario_path: Scenario | str | Path, strategy: str, model_path: Path | None = None,
                    seed: int = 0) -> Episode:
    """Calcula una misión real antes de reproducirla; no fabrica estados visuales."""
    scenario = scenario_path if isinstance(scenario_path, Scenario) else Scenario.load(scenario_path)
    simulation = RescueSimulation(scenario)
    policy = create_policy(simulation, strategy, model_path=model_path, seed=seed)
    states, actions = [simulation.state], []
    while simulation.state.outcome == "running":
        action = policy.act(simulation.state)
        actions.append(action)
        states.append(simulation.step(action))
    return Episode(simulation.scenario, tuple(states), tuple(actions))


class Playback:
    """El reloj solo revela estados ya calculados; nunca modifica exposición."""

    def __init__(self, episode: Episode, speed: int = 3):
        self.episode = episode
        self.index = 0
        self.playing = False
        self.elapsed = 0.0
        self.set_speed(speed)

    @property
    def state(self) -> MissionState:
        return self.episode.states[self.index]

    @property
    def finished(self) -> bool:
        return self.index == len(self.episode.states) - 1

    def set_speed(self, speed: int):
        if type(speed) is not int or not 1 <= speed <= 12:
            raise ValueError("La velocidad debe ser un entero entre 1 y 12")
        self.speed = speed
        self.elapsed = 0.0

    def reset(self):
        self.index, self.elapsed, self.playing = 0, 0.0, False

    def toggle(self):
        if self.finished:
            self.reset()
        self.playing = not self.playing

    def step(self):
        self.playing = False
        self.elapsed = 0.0
        if not self.finished:
            self.index += 1

    def tick(self, seconds: float):
        if not isfinite(seconds) or seconds < 0:
            raise ValueError("El tiempo visual debe ser finito y no negativo")
        if not self.playing:
            return
        self.elapsed += seconds
        while self.elapsed + 1e-9 >= 1 / self.speed and not self.finished:
            self.elapsed = max(0.0, self.elapsed - 1 / self.speed)
            self.index += 1
        if self.finished:
            self.playing = False
            self.elapsed = 0.0
