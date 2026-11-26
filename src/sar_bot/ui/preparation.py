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
    learning: bool = False
    session_dir: str | None = None
    project_root: str | None = None


@dataclass(frozen=True)
class PreparedMission:
    request: PreparationRequest
    viability: ViabilityResult
    episode: Episode | None
    error: str | None = None
    learning_stats: dict | None = None


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
        if request.learning:
            if request.strategy != "dqn" or not request.model or not request.session_dir:
                raise ValueError("La sesion de aprendizaje requiere DQN y un modelo base")
            from sar_bot.online import LearningSession
            if not request.project_root:
                raise ValueError("Falta la raiz de la sesion")
            session = LearningSession.for_project(request.project_root, request.model, scenario)
            if str(session.directory) != request.session_dir:
                raise ValueError("La identidad de la sesion cambio")
            episode = session.prepare_episode(scenario, request.seed, cancelled)
            snapshot = session.snapshot()
            stats = {key:snapshot.metadata[key] for key in ("missions","transitions","updates","buffer_size")}
            stats["recovered"] = snapshot.recovered
        else:
            episode = prepare_episode(scenario, request.strategy, request.model, request.seed,
                                      cancel_event=cancelled)
            stats = None
    except CancelledError:
        raise
    except Exception as error:
        return PreparedMission(request, viability, None, str(error))
    if cancelled.is_set():
        raise CancelledError()
    return PreparedMission(request, viability, episode, learning_stats=stats)


def learn_completed_episode(request, episode):
    """Transacción en un trabajador; no toca controles ni superficies Pygame."""
    from sar_bot.online import LearningSession
    session = LearningSession.for_project(request.project_root, request.model, episode.scenario)
    if str(session.directory) != request.session_dir:
        raise ValueError("La identidad de la sesion cambio")
    return session.learn_episode(episode)
