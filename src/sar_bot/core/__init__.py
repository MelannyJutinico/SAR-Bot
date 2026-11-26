"""Reglas independientes de la interfaz y del algoritmo de aprendizaje."""

from .simulation import Action, HeatSource, MissionState, RescueSimulation, Robot, Scenario, damage_rate
from .viability import (
    CertificationAttempt,
    ViabilityCertificate,
    ViabilityResult,
    ViabilityStatus,
    certify_viability,
    replay_certificate,
)
from .generation import (
    Difficulty,
    GeneratedConfiguration,
    GenerationSummary,
    classify_difficulty,
    generate_configurations,
)

__all__ = [
    "Action", "CertificationAttempt", "HeatSource", "MissionState", "RescueSimulation",
    "Robot", "Scenario", "ViabilityCertificate", "ViabilityResult", "ViabilityStatus",
    "Difficulty", "GeneratedConfiguration", "GenerationSummary",
    "certify_viability", "classify_difficulty", "damage_rate",
    "generate_configurations", "replay_certificate",
]
