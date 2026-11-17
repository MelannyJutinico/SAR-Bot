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

__all__ = [
    "Action", "CertificationAttempt", "HeatSource", "MissionState", "RescueSimulation",
    "Robot", "Scenario", "ViabilityCertificate", "ViabilityResult", "ViabilityStatus",
    "certify_viability", "damage_rate", "replay_certificate",
]
