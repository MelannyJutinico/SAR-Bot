"""Limites de presentacion; no cambian el contrato ni las reglas del nucleo."""
import json
from pathlib import Path
from sar_bot.core import Scenario

MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_EPISODE_STATES = 5000
MAX_UI_SIDE = 24
MAX_UI_VICTIMS = 3


def check_ui_limits(data):
    for key, maximum in (("width", MAX_UI_SIDE), ("height", MAX_UI_SIDE),
                         ("max_steps", MAX_EPISODE_STATES - 1)):
        value = data.get(key)
        if type(value) is int and value > maximum:
            raise ValueError(f"Limite de interfaz: {key} no puede superar {maximum}")
    victims = data.get("victims")
    if isinstance(victims, (list, tuple)) and len(victims) > MAX_UI_VICTIMS:
        raise ValueError("La interfaz representa como maximo tres personas")


def validate_ui_scenario(scenario):
    check_ui_limits({"width": scenario.width, "height": scenario.height,
                     "max_steps": scenario.max_steps, "victims": scenario.victims})
    return scenario


def load_ui_scenario(path):
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("El archivo personal supera 16 MiB")
    with path.open("rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("El archivo personal supera 16 MiB")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("El escenario debe ser un objeto JSON")
    check_ui_limits(data)
    return Scenario.from_dict(data)
