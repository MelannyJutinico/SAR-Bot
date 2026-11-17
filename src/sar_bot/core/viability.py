"""Certificación positiva y acotada mediante trayectorias del motor real."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping

from .simulation import MissionState, RescueSimulation, Scenario


class ViabilityStatus(str, Enum):
    """Estados inequívocos; ``not_certified`` nunca significa imposible."""

    STRUCTURAL_INVALID = "structural_invalid"
    CERTIFIED = "certified"
    NOT_CERTIFIED = "not_certified"


@dataclass(frozen=True)
class CertificationAttempt:
    strategy: str
    actions_executed: int
    outcome: str
    rescued: int
    planning_failures: int = 0
    error: str | None = None


@dataclass(frozen=True)
class ViabilityCertificate:
    """Trayectoria testigo ejecutada por :class:`RescueSimulation`."""

    strategy: str
    scenario_id: str
    configuration_id: str
    steps: int
    rescued: int
    damage_total: int
    final_integrities: tuple[int, int]
    actions: tuple[int, ...]
    outcome: str

    def __post_init__(self):
        if self.strategy not in ("thermal", "shortest"):
            raise ValueError("El certificado requiere una estrategia de referencia")
        if self.outcome != "success":
            raise ValueError("Un certificado solo puede representar una misión exitosa")
        if type(self.steps) is not int or self.steps < 1 or self.steps != len(self.actions):
            raise ValueError("Los pasos del certificado deben coincidir con sus acciones")
        if type(self.rescued) is not int or self.rescued < 1:
            raise ValueError("El certificado debe incluir personas rescatadas")
        if type(self.damage_total) is not int or self.damage_total < 0:
            raise ValueError("El daño certificado debe ser un entero no negativo")
        if len(self.final_integrities) != 2 or any(
            type(value) is not int or value <= 0 for value in self.final_integrities
        ):
            raise ValueError("Ambos robots deben terminar operativos")
        if any(type(action) is not int or not 0 <= action < 25 for action in self.actions):
            raise ValueError("El certificado contiene una acción conjunta inválida")
        if not self.scenario_id or not self.configuration_id:
            raise ValueError("El certificado requiere ambos identificadores")


@dataclass(frozen=True)
class ViabilityResult:
    status: ViabilityStatus
    message: str
    scenario_id: str | None = None
    configuration_id: str | None = None
    certificate: ViabilityCertificate | None = None
    attempts: tuple[CertificationAttempt, ...] = ()

    def __post_init__(self):
        if not isinstance(self.status, ViabilityStatus) or not self.message:
            raise ValueError("El resultado requiere estado y mensaje")
        if self.status is ViabilityStatus.CERTIFIED:
            if self.certificate is None:
                raise ValueError("Un resultado certified requiere certificado")
            if (self.scenario_id, self.configuration_id) != (
                self.certificate.scenario_id, self.certificate.configuration_id
            ):
                raise ValueError("Los identificadores del resultado y certificado deben coincidir")
        elif self.certificate is not None:
            raise ValueError("Solo un resultado certified puede incluir certificado")
        if self.status is ViabilityStatus.STRUCTURAL_INVALID:
            if self.scenario_id is not None or self.configuration_id is not None:
                raise ValueError("Una entrada estructuralmente inválida no tiene identificadores")
        elif self.scenario_id is None or self.configuration_id is None:
            raise ValueError("Un escenario validado requiere ambos identificadores")


ScenarioInput = Scenario | Mapping | str | Path


def _scenario_from(value: ScenarioInput) -> Scenario:
    if isinstance(value, Scenario):
        return value
    if isinstance(value, Mapping):
        return Scenario.from_dict(dict(value))
    if isinstance(value, (str, Path)):
        return Scenario.load(value)
    raise ValueError("Se requiere un Scenario, objeto JSON o ruta de escenario")


def certify_viability(
    scenario_input: ScenarioInput,
    *,
    strategies: tuple[str, ...] = ("thermal", "shortest"),
    action_budget: int | None = None,
) -> ViabilityResult:
    """Busca un certificado positivo sin confundir fallo heurístico con imposibilidad.

    El presupuesto es el número total de acciones que pueden ejecutar todos los
    intentos. Cada acción y todo daño pasan por ``RescueSimulation``. DQN no es
    una estrategia admitida para certificación.
    """
    try:
        scenario = _scenario_from(scenario_input)
    except (ValueError, TypeError, OSError) as error:
        return ViabilityResult(ViabilityStatus.STRUCTURAL_INVALID, str(error))

    if not strategies or any(strategy not in ("thermal", "shortest") for strategy in strategies):
        raise ValueError("Las estrategias de certificación admitidas son thermal y shortest")
    if action_budget is None:
        action_budget = scenario.max_steps * len(strategies)
    if type(action_budget) is not int or action_budget < 0:
        raise ValueError("El presupuesto de acciones debe ser un entero no negativo")

    attempts = []
    remaining = action_budget
    # Importación local para mantener el núcleo del motor libre de ciclos al
    # exportar esta API desde sar_bot.core.
    from sar_bot.agents.factory import create_policy

    for strategy in strategies:
        simulation = RescueSimulation(scenario)
        policy = create_policy(simulation, strategy)
        actions = []
        planning_failures = 0
        error = None
        while simulation.state.outcome == "running" and remaining:
            try:
                action = policy.act(simulation.state)
            except (RuntimeError, ValueError) as caught:
                error = str(caught)
                break
            planning_failures += int(not getattr(policy, "last_plan_found", True))
            actions.append(action)
            remaining -= 1
            simulation.step(action)

        state = simulation.state
        attempts.append(CertificationAttempt(
            strategy, len(actions), state.outcome, len(state.rescued), planning_failures, error
        ))
        if (
            state.outcome == "success"
            and len(state.rescued) == scenario.victim_count
            and all(robot.integrity > 0 for robot in state.robots)
            and state.steps <= scenario.max_steps
        ):
            certificate = ViabilityCertificate(
                strategy=strategy,
                scenario_id=scenario.scenario_id,
                configuration_id=scenario.configuration_id,
                steps=state.steps,
                rescued=len(state.rescued),
                damage_total=sum(robot.damage for robot in state.robots),
                final_integrities=tuple(robot.integrity for robot in state.robots),
                actions=tuple(actions),
                outcome=state.outcome,
            )
            return ViabilityResult(
                ViabilityStatus.CERTIFIED,
                f"Trayectoria certificada por {strategy}",
                scenario.scenario_id,
                scenario.configuration_id,
                certificate,
                tuple(attempts),
            )

    return ViabilityResult(
        ViabilityStatus.NOT_CERTIFIED,
        "No se encontró una trayectoria testigo dentro del presupuesto; no demuestra imposibilidad",
        scenario.scenario_id,
        scenario.configuration_id,
        attempts=tuple(attempts),
    )


def replay_certificate(scenario: Scenario, certificate: ViabilityCertificate) -> MissionState:
    """Reproduce y verifica un testigo usando exclusivamente el motor real."""
    if scenario.scenario_id != certificate.scenario_id:
        raise ValueError("El scenario_id del certificado no coincide")
    if scenario.configuration_id != certificate.configuration_id:
        raise ValueError("El configuration_id del certificado no coincide")
    simulation = RescueSimulation(scenario)
    for action in certificate.actions:
        if simulation.state.outcome != "running":
            raise ValueError("El certificado contiene acciones posteriores a la finalización")
        simulation.step(action)
    state = simulation.state
    observed = (
        state.outcome,
        state.steps,
        len(state.rescued),
        sum(robot.damage for robot in state.robots),
        tuple(robot.integrity for robot in state.robots),
    )
    expected = (
        certificate.outcome,
        certificate.steps,
        certificate.rescued,
        certificate.damage_total,
        certificate.final_integrities,
    )
    if observed != expected or state.outcome != "success":
        raise ValueError("La reproducción no coincide con el certificado")
    return state
