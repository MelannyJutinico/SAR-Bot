"""Preparación de episodios y reloj visual, sin dependencia de Pygame."""

from concurrent.futures import CancelledError
from dataclasses import dataclass
from math import isfinite
from hashlib import sha256, file_digest
import sys
from pathlib import Path

from sar_bot.agents import create_policy
from sar_bot.core import MissionState, RescueSimulation, Scenario
from .resources import validate_ui_scenario, MAX_EPISODE_STATES


@dataclass(frozen=True)
class Episode:
    scenario: Scenario
    states: tuple[MissionState, ...]
    actions: tuple[int, ...]
    checkpoint_sha256: str | None = None
    engine_sha256: str | None = None
    learning_id: str | None = None
    decisions: tuple = ()

    @property
    def scenario_id(self):
        return self.scenario.fingerprint()

    @property
    def configuration_id(self):
        return self.scenario.configuration_id


def prepare_episode(scenario_path: Scenario | str | Path, strategy: str, model_path: Path | None = None,
                    seed: int = 0, *, cancel_event=None) -> Episode:
    """Calcula una misión real antes de reproducirla; no fabrica estados visuales."""
    if cancel_event is not None and cancel_event.is_set():
        raise CancelledError()
    scenario = scenario_path if isinstance(scenario_path, Scenario) else Scenario.load(scenario_path)
    validate_ui_scenario(scenario)
    engine_hash = sha256(Path(sys.modules[RescueSimulation.__module__].__file__).read_bytes()).hexdigest()
    model_hash = None
    if strategy == "dqn" and model_path is not None:
        with Path(model_path).open("rb") as stream:
            model_hash = file_digest(stream, "sha256").hexdigest()
    simulation = RescueSimulation(scenario)
    policy = create_policy(simulation, strategy, model_path=model_path, seed=seed)
    states, actions = [simulation.state], []
    while simulation.state.outcome == "running":
        if len(states) >= MAX_EPISODE_STATES:
            raise ValueError("La traza supera 5000 estados permitidos por la interfaz")
        if cancel_event is not None and cancel_event.is_set():
            raise CancelledError()
        action = policy.act(simulation.state)
        actions.append(action)
        states.append(simulation.step(action))
    if model_hash is not None:
        with Path(model_path).open("rb") as stream:
            if file_digest(stream, "sha256").hexdigest() != model_hash:
                raise ValueError("El checkpoint cambio durante la preparacion")
    return Episode(simulation.scenario, tuple(states), tuple(actions), model_hash, engine_hash,
                   decisions=tuple(getattr(policy,"decisions",())))


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
