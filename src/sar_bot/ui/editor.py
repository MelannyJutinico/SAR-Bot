"""Borrador visual independiente; la validez del escenario pertenece al núcleo."""

from dataclasses import dataclass
from sar_bot.core import Scenario


class ScenarioDraft:
    def __init__(self, template: Scenario):
        if template.victim_count != 3:
            raise ValueError("El editor requiere una plantilla de tres personas")
        self.template = template
        self.selected = 0
        self._positions = list(template.victims)
        self.message = "Selecciona una persona y haz clic en el mapa."
        self.invalid = False

    @property
    def positions(self):
        return tuple(self._positions)

    @property
    def missing(self):
        return self._positions.count(None)

    def select(self, person):
        if type(person) is not int or not 0 <= person < 3:
            raise ValueError("Selecciona Persona 1, 2 o 3")
        self.selected = person
        self.message = f"Persona {person + 1} seleccionada. Haz clic en el mapa."
        self.invalid = False

    def place(self, position):
        try:
            # Una sola persona también es un Scenario válido: valida límites,
            # base, paredes, tipos y conectividad sin completar el borrador.
            self.template.with_victims((position,))
            position = tuple(position)
            if any(i != self.selected and value == position
                   for i, value in enumerate(self._positions)):
                raise ValueError("La celda ya está ocupada por otra persona")
        except (ValueError, TypeError) as error:
            self.message, self.invalid = str(error), True
            return False
        self._positions[self.selected] = position
        if not self.missing:
            self.build()
        self.message = f"Persona {self.selected + 1} colocada en {chr(65 + position[0])}{position[1] + 1}."
        self.invalid = False
        return True

    def clear(self):
        self._positions = [None] * 3
        self.message, self.invalid = "Coloca las tres personas en el mapa.", False

    def restore(self):
        self._positions = list(self.template.victims)
        self.message, self.invalid = "Posiciones originales restauradas.", False

    def build(self):
        if self.missing:
            raise ValueError(f"Faltan {self.missing} personas por ubicar")
        return self.template.with_victims(self.positions)


@dataclass(frozen=True)
class Viewport:
    """La misma transformación para dibujar y recibir clics, incluido letterbox."""
    window: tuple[int, int]
    canvas: tuple[int, int] = (1280, 860)

    @property
    def scale(self):
        return min(self.window[0] / self.canvas[0], self.window[1] / self.canvas[1])

    @property
    def size(self):
        return tuple(max(1, round(v * self.scale)) for v in self.canvas)

    @property
    def offset(self):
        return tuple((w - s) // 2 for w, s in zip(self.window, self.size))

    def logical(self, position):
        x, y = (position[i] - self.offset[i] for i in range(2))
        if not 0 <= x < self.size[0] or not 0 <= y < self.size[1]:
            return (-1, -1)
        return (x * self.canvas[0] / self.size[0], y * self.canvas[1] / self.size[1])


def pixel_to_cell(position, grid, shape):
    gx, gy, cell = grid
    x, y = position
    width, height = shape
    if cell <= 0 or not gx <= x < gx + width * cell or not gy <= y < gy + height * cell:
        return None
    return (int((x - gx) // cell), int((y - gy) // cell))


def draw_editor_controls(app):
    """Presentación del editor usando los mismos componentes de RescueApp."""
    draft = app.editor
    app.text("EDITOR DE PERSONAS", (900, 137), 18, bold=True)
    app.wrap("Elige una persona y colócala en una celda libre del mapa.", 900, 180, 320)
    for i, position in enumerate(draft.positions):
        state = "Sin ubicar" if position is None else f"Celda {chr(65 + position[0])}{position[1] + 1}"
        app.button(f"person_{i}", f"{'>' if draft.selected == i else ' '} Persona {i + 1} · {state}",
                   (900, 253 + i * 58, 328, 46), primary=draft.selected == i)
    app.text(f"Faltan por ubicar: {draft.missing} / 3", (900, 440), 18, bold=True)
    app.button("editor_clear", "Limpiar posiciones", (900, 486, 328, 40))
    app.button("editor_restore", "Restaurar plantilla", (900, 538, 328, 40))
    app.wrap(app.file_message or draft.message, 900, 590, 320, 14, (255, 119, 111) if draft.invalid else (230, 238, 246))
    status = "Borrador incompleto" if draft.missing else "Configuración estructural válida"
    app.text(status, (900, 650), 14)
    app.button("save_file", "Guardar", (900, 674, 155, 30), enabled=draft.missing == 0)
    app.button("load_file", "Cargar personal", (1070, 674, 158, 30))
    app.button("editor_apply", "Validar y preparar mision", (900, 710, 328, 40),
               primary=True, enabled=draft.missing == 0)
    app.button("editor_exit", "Volver a mision · conservar borrador", (900, 762, 328, 38))
