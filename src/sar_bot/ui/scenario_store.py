"""Biblioteca personal local. Usa exclusivamente la persistencia publica de Scenario."""
from pathlib import Path
from sar_bot.core import Scenario
import json
from .local_files import atomic_text
from .resources import load_ui_scenario, validate_ui_scenario


class ScenarioStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory).resolve()

    def _path(self, name):
        path = (self.directory / name).resolve()
        if path.parent != self.directory or path.suffix.lower() != ".json":
            raise ValueError("Selecciona un JSON de la biblioteca personal")
        return path

    def save(self, scenario: Scenario):
        path = self._path(scenario.configuration_id[:20] + ".json")
        validate_ui_scenario(scenario)
        with atomic_text(path, lambda temporary: Scenario.load(temporary)) as stream:
            json.dump(scenario.to_dict(), stream, ensure_ascii=False, indent=2)
        return path

    def load(self, name):
        scenario = load_ui_scenario(self._path(name))
        if scenario.victim_count != 3:
            raise ValueError("El editor requiere un escenario de tres personas")
        if max(scenario.width, scenario.height) > 24:
            raise ValueError("La interfaz admite mapas de hasta 24 celdas por lado")
        return scenario

    def list_files(self):
        if not self.directory.exists():
            return ()
        return tuple(sorted(p.name for p in self.directory.glob("*.json") if p.is_file()))


def draw_library(app):
    app.card((876, 112, 376, 718))
    app.text("CONFIGURACIONES PERSONALES", (900, 140), 16, bold=True)
    app.wrap("outputs/custom_scenarios · Archivos locales", 900, 177, 320, 13)
    start = app.library_page * 6
    for i, name in enumerate(app.library_files[start:start + 6]):
        label = name if len(name) <= 30 else name[:24] + "...json"
        app.button(f"file_{start+i}", label, (900, 240 + i * 58, 328, 44))
    if not app.library_files:
        app.wrap("No hay archivos. Guarda primero un borrador completo.", 900, 250, 320)
    app.button("library_prev", "Anterior", (900, 605, 155, 38), enabled=start > 0)
    app.button("library_next", "Siguiente", (1070, 605, 158, 38),
               enabled=start + 6 < len(app.library_files))
    app.text(f"Pagina {app.library_page + 1}", (900, 660), 14)
    app.wrap(app.file_message, 900, 690, 320, 13)
    app.button("library_close", "Volver", (900, 770, 328, 38))
