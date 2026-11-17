"""Generación reproducible y acotada de configuraciones V2 sobre una plantilla."""

from dataclasses import dataclass
from enum import Enum
import random

from .simulation import Position, Scenario, damage_rate
from .viability import ViabilityResult, ViabilityStatus, certify_viability


class Difficulty(str, Enum):
    EASY = "easy"
    INTERMEDIATE = "intermediate"
    DEMANDING = "demanding"


@dataclass(frozen=True)
class GeneratedConfiguration:
    scenario: Scenario
    difficulty: Difficulty
    viability: ViabilityResult


@dataclass(frozen=True)
class GenerationSummary:
    seed: int
    requested: int
    max_attempts: int
    attempts: int
    accepted: tuple[GeneratedConfiguration, ...]
    not_certified: tuple[GeneratedConfiguration, ...]
    structural_invalid: int
    duplicates: int

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def generated_ids(self) -> tuple[str, ...]:
        return tuple(item.scenario.scenario_id for item in self.accepted)

    def to_dict(self) -> dict:
        def item(value: GeneratedConfiguration) -> dict:
            return {
                "difficulty": value.difficulty.value,
                "victims": [list(position) for position in value.scenario.victims],
                "scenario_id": value.scenario.scenario_id,
                "configuration_id": value.scenario.configuration_id,
                "viability": value.viability.status.value,
            }

        return {
            "seed": self.seed,
            "requested": self.requested,
            "max_attempts": self.max_attempts,
            "attempts": self.attempts,
            "accepted": [item(value) for value in self.accepted],
            "not_certified": [item(value) for value in self.not_certified],
            "structural_invalid": self.structural_invalid,
            "duplicates": self.duplicates,
            "generated_ids": list(self.generated_ids),
        }


def classify_difficulty(template: Scenario, positions: tuple[Position, ...]) -> Difficulty:
    """Clasifica por distancia normalizada y exposición inicial de las personas.

    Es una familia explicable para generación, no una medida de desempeño de DQN.
    La certificación posterior decide si existe un testigo positivo.
    """
    maximum = max(1, template.width + template.height - 2)
    distance_ratio = sum(
        abs(x - template.base[0]) + abs(y - template.base[1]) for x, y in positions
    ) / (len(positions) * maximum)
    hot = sum(damage_rate(template.temperature_at(position)) > 0 for position in positions)
    if distance_ratio <= 0.20 and hot <= 1:
        return Difficulty.EASY
    if distance_ratio >= 0.50 or (distance_ratio >= 0.35 and hot >= 2):
        return Difficulty.DEMANDING
    return Difficulty.INTERMEDIATE


def generate_configurations(
    template: Scenario,
    *,
    seed: int,
    requested: int,
    max_attempts: int,
    difficulties: tuple[Difficulty, ...] = (
        Difficulty.EASY, Difficulty.INTERMEDIATE, Difficulty.DEMANDING,
    ),
    action_budget: int | None = None,
) -> GenerationSummary:
    """Genera tres posiciones, deduplica por ``scenario_id`` y certifica.

    Solo los casos certificados cuentan como aceptados. Los casos no certificados
    se conservan por separado para diagnóstico y el bucle termina siempre al
    alcanzar ``requested`` o ``max_attempts``.
    """
    if template.victim_count != 3:
        raise ValueError("La generación V2 requiere una plantilla de tres personas")
    if type(seed) is not int:
        raise ValueError("La semilla debe ser un entero")
    if type(requested) is not int or requested < 1:
        raise ValueError("requested debe ser un entero positivo")
    if type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("max_attempts debe ser un entero positivo")
    if not difficulties or any(not isinstance(value, Difficulty) for value in difficulties):
        raise ValueError("Se requiere al menos una dificultad válida")

    cells = [
        (x, y) for y in range(template.height) for x in range(template.width)
        if template.walkable((x, y)) and (x, y) != template.base
    ]
    if len(cells) < 3:
        raise ValueError("La plantilla no tiene tres celdas disponibles")
    maximum = max(1, template.width + template.height - 2)
    safe_near = [position for position in cells if
                 abs(position[0] - template.base[0]) + abs(position[1] - template.base[1])
                 <= 0.30 * maximum and damage_rate(template.temperature_at(position)) == 0]
    far_or_hot = [position for position in cells if
                  abs(position[0] - template.base[0]) + abs(position[1] - template.base[1])
                  >= 0.40 * maximum or damage_rate(template.temperature_at(position)) > 0]

    rng = random.Random(seed)
    accepted = []
    not_certified = []
    seen = set()
    duplicates = structural_invalid = 0
    attempts = 0
    while attempts < max_attempts and len(accepted) < requested:
        attempts += 1
        desired = difficulties[len(accepted) % len(difficulties)]
        pool = safe_near if desired is Difficulty.EASY else far_or_hot if desired is Difficulty.DEMANDING else cells
        if len(pool) < 3:
            pool = cells
        positions = tuple(rng.sample(pool, 3))
        try:
            scenario = template.with_victims(
                positions, name=f"{template.name}_{desired.value}_{len(accepted) + 1}"
            )
        except ValueError:
            structural_invalid += 1
            continue
        if scenario.scenario_id in seen:
            duplicates += 1
            continue
        seen.add(scenario.scenario_id)
        actual = classify_difficulty(template, scenario.victims)
        if actual is not desired:
            continue
        viability = certify_viability(scenario, action_budget=action_budget)
        generated = GeneratedConfiguration(scenario, actual, viability)
        if viability.status is ViabilityStatus.CERTIFIED:
            accepted.append(generated)
        elif viability.status is ViabilityStatus.NOT_CERTIFIED:
            not_certified.append(generated)
        else:
            structural_invalid += 1

    return GenerationSummary(
        seed, requested, max_attempts, attempts, tuple(accepted),
        tuple(not_certified), structural_invalid, duplicates,
    )
