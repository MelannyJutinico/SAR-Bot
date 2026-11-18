"""Solicitudes inmutables de preparacion; ningun trabajador escribe en Pygame."""
from concurrent.futures import CancelledError
from dataclasses import dataclass
from threading import Event

from sar_bot.core import Scenario, ViabilityResult, ViabilityStatus, certify_viability
from .playback import Episode, prepare_episode
from .resources import validate_ui_scenario


@dataclass(frozen=True)
class PreparationRequest:
    generation: int
    configuration_id: str
    strategy: str
    model: str | None
    seed: int


@dataclass(frozen=True)
class PreparedMission:
    request: PreparationRequest
    viability: ViabilityResult
    episode: Episode | None
    error: str | None = None


def prepare_mission(request: PreparationRequest, scenario: Scenario, cancelled: Event) -> PreparedMission:
    if cancelled.is_set():
        raise CancelledError()
    if scenario.configuration_id != request.configuration_id:
        raise ValueError("La solicitud no coincide con el escenario")
    validate_ui_scenario(scenario)
    viability = certify_viability(scenario)
    # El certificador publico es acotado por acciones, pero no es interrumpible.
    # Comprobar antes y despues impide iniciar un episodio ya invalidado.
    if cancelled.is_set():
        raise CancelledError()
    if viability.status is ViabilityStatus.STRUCTURAL_INVALID:
        return PreparedMission(request, viability, None, viability.message)
    try:
        episode = prepare_episode(scenario, request.strategy, request.model, request.seed,
                                  cancel_event=cancelled)
    except CancelledError:
        raise
    except Exception as error:
        return PreparedMission(request, viability, None, str(error))
    if cancelled.is_set():
        raise CancelledError()
    return PreparedMission(request, viability, episode)
