"""Estrategias de referencia. Todavía no hay una política entrenada."""

from .reference import RandomPolicy, ShortestPathPolicy, ThermalPathPolicy

__all__ = ["RandomPolicy", "ShortestPathPolicy", "ThermalPathPolicy"]
