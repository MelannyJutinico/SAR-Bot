"""Estrategias de referencia. Todavía no hay una política entrenada."""

from .reference import RandomPolicy, ShortestPathPolicy, ThermalPathPolicy
from .factory import Policy, create_policy

__all__ = ["RandomPolicy", "ShortestPathPolicy", "ThermalPathPolicy", "Policy", "create_policy"]
