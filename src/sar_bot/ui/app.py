"""Interfaz Pygame. Reproduce los estados del motor, sin duplicar sus reglas."""

from concurrent.futures import ThreadPoolExecutor
import math
from pathlib import Path
import traceback

import pygame

from sar_bot.core import RescueSimulation, Scenario, damage_rate
from .playback import Playback, prepare_episode

SIZE = (1280, 860)
BG = (10, 17, 28)
PANEL = (17, 27, 42)
INSET = (23, 36, 53)
BORDER = (39, 55, 74)
TEXT = (230, 238, 246)
MUTED = (144, 163, 183)
CYAN = (56, 205, 216)
PURPLE = (169, 144, 255)
GOLD = (255, 193, 91)
GREEN = (100, 221, 168)
RED = (255, 119, 111)
ROBOT_COLORS = (CYAN, PURPLE)

STRATEGIES = [
    ("dqn", "DQN entrenado", "Control aprendido mediante recompensas."),
    ("shortest", "Ruta más corta", "Coordina recorridos sin considerar el calor."),
    ("thermal", "Ruta con riesgo térmico", "Equilibra pasos y exposición al calor."),
    ("random", "Movimientos aleatorios", "Selecciona acciones al azar, con semilla fija."),
]
SCENARIO_NAMES = {
    "rescate_inicial": "Rescate inicial",
    "ruta_caliente": "Ruta caliente",
    "pasillo_compartido": "Pasillo compartido",
    "warmup_sin_calor": "Rescate cercano sin calor",
    "navegacion_sin_calor": "Navegación sin calor",
    "paso_compartido_cercano": "Paso compartido cercano",
    "validacion_foco_desplazado": "Foco desplazado",
    "validacion_victimas_pasillo": "Víctimas en el pasillo",
    "prueba_rescate_intermedio": "Rescate intermedio",
    "prueba_obstaculos_pasillo": "Pasillo con otros obstáculos",
}


def heat_color(temperature):
    stops = [(25, (22, 44, 58)), (40, (66, 58, 43)), (60, (113, 61, 40)),
             (80, (157, 53, 43)), (160, (191, 48, 47))]
    for (low, first), (high, second) in zip(stops, stops[1:]):
        if temperature <= high:
            ratio = max(0, (temperature - low) / (high - low))
            return tuple(round(a + ratio * (b - a)) for a, b in zip(first, second))
    return stops[-1][1]


class RescueApp:
    def __init__(self, root: Path, scenario_path: Path, strategy="dqn", model_path=None,
                 seed=0, asynchronous=True):
        self.root, self.model_path, self.seed = root, model_path, seed
        self.options = [(p, Scenario.load(p)) for p in sorted((root / "scenarios").rglob("*.json"))]
        if scenario_path.resolve() not in {p.resolve() for p, _ in self.options}:
            self.options.append((scenario_path, Scenario.load(scenario_path)))
        self.scenario_index = next(i for i, (p, _) in enumerate(self.options)
                                   if p.resolve() == scenario_path.resolve())
        self.strategy_index = next(i for i, s in enumerate(STRATEGIES) if s[0] == strategy)
        self.playback = None
        self.speed = 3
        self.show_heat = True
        self.show_paths = True
        self.dropdown = None
        self.error = None
        self.fonts = {}
        self.controls = {}
        self.dropdown_rows = []
        self.executor = ThreadPoolExecutor(max_workers=1) if asynchronous else None
        self.future = None
        self.mouse = (-1, -1)
        self.canvas = pygame.Surface(SIZE)
        self._select()

    @property
    def scenario(self):
        return self.options[self.scenario_index][1]

    @property
    def state(self):
        return self.playback.state if self.playback else self.preview

    def _select(self):
        if self.future:
            self.future.cancel()
        self.playback, self.error, self.dropdown = None, None, None
        self.preview = RescueSimulation(self.scenario).state
        args = (self.options[self.scenario_index][0], STRATEGIES[self.strategy_index][0],
                self.model_path, self.seed)
        if self.executor:
            self.future = self.executor.submit(prepare_episode, *args)
        else:
            self.playback = Playback(prepare_episode(*args), self.speed)

    def update(self, seconds):
        if self.future and self.future.done():
            future, self.future = self.future, None
            try:
                self.playback = Playback(future.result(), self.speed)
            except ImportError:
                self.error = "Faltan dependencias del modelo. Ejecuta: uv sync --extra ui --extra rl"
            except FileNotFoundError:
                self.error = "No se encontró el modelo. Revisa su ruta o selecciona otra estrategia."
            except Exception:
                self.error = "No se pudo preparar esta estrategia. Selecciona otra y revisa el detalle en la consola."
                traceback.print_exc()
        if self.playback and self.dropdown is None:
            self.playback.tick(seconds)

    def close(self):
        if self.executor:
            self.executor.shutdown(wait=False, cancel_futures=True)

    def text(self, value, position, size=16, color=TEXT, bold=False, center=False):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = pygame.font.SysFont("segoeui", size, bold=bold)
        rendered = self.fonts[key].render(str(value), True, color)
        rect = rendered.get_rect(center=position) if center else rendered.get_rect(topleft=position)
        self.canvas.blit(rendered, rect)
        return rect

    def wrap(self, value, x, y, width, size=15, color=MUTED):
        # Medir con la misma fuente que se usa al dibujar.
        if (size, False) not in self.fonts:
            self.fonts[size, False] = pygame.font.SysFont("segoeui", size)
        font = self.fonts[size, False]
        line = ""
        for word in value.split():
            candidate = f"{line} {word}".strip()
            if font.size(candidate)[0] > width and line:
                self.text(line, (x, y), size, color)
                y += size + 6
                line = word
            else:
                line = candidate
        if line:
            self.text(line, (x, y), size, color)
        return y + size + 6

    def card(self, rect, color=PANEL, radius=16):
        rect = pygame.Rect(rect)
        pygame.draw.rect(self.canvas, color, rect, border_radius=radius)
        pygame.draw.rect(self.canvas, BORDER, rect, 1, border_radius=radius)
        return rect

    def button(self, key, label, rect, primary=False, enabled=True):
        rect = pygame.Rect(rect)
        self.controls[key] = rect
        hovered = rect.collidepoint(self.mouse) and enabled and self.dropdown is None
        color = CYAN if primary and enabled else ((36, 56, 76) if hovered else INSET)
        pygame.draw.rect(self.canvas, color, rect, border_radius=9)
        if not primary:
            pygame.draw.rect(self.canvas, BORDER, rect, 1, border_radius=9)
        self.text(label, rect.center, 16, BG if primary and enabled else TEXT if enabled else MUTED,
                  bold=primary, center=True)

    def switch(self, key, label, value, y):
        self.text(label, (900, y + 3), 16)
        rect = pygame.Rect(1190, y, 38, 24)
        self.controls[key] = pygame.Rect(900, y - 4, 328, 32)
        pygame.draw.rect(self.canvas, CYAN if value else BORDER, rect, border_radius=12)
        pygame.draw.circle(self.canvas, BG if value else MUTED,
                           (rect.x + (26 if value else 12), rect.centery), 8)

    def action(self, key):
        if key == "scenario":
            self.dropdown = None if self.dropdown == "scenario" else "scenario"
        elif key == "strategy":
            self.dropdown = None if self.dropdown == "strategy" else "strategy"
        elif key == "heat":
            self.show_heat = not self.show_heat
        elif key == "paths":
            self.show_paths = not self.show_paths
        elif key in ("slower", "faster"):
            self.speed = max(1, min(12, self.speed + (1 if key == "faster" else -1)))
            if self.playback:
                self.playback.set_speed(self.speed)
        elif self.playback:
            if key == "play":
                self.playback.toggle()
            elif key == "step":
                self.playback.step()
            elif key == "reset":
                self.playback.reset()

    def click(self, position):
        if self.dropdown:
            for index, rect in self.dropdown_rows:
                if rect.collidepoint(position):
                    if self.dropdown == "scenario":
                        self.scenario_index = index
                    else:
                        self.strategy_index = index
                    self._select()
                    return
            self.dropdown = None
            return
        for key, rect in self.controls.items():
            if rect.collidepoint(position):
                self.action(key)
                return

    def key(self, key):
        if key == pygame.K_ESCAPE:
            self.dropdown = None
        elif self.dropdown is None:
            action = {pygame.K_SPACE: "play", pygame.K_n: "step", pygame.K_r: "reset",
                      pygame.K_h: "heat", pygame.K_t: "paths", pygame.K_PLUS: "faster",
                      pygame.K_EQUALS: "faster", pygame.K_MINUS: "slower"}.get(key)
            if action:
                self.action(action)

    def _status(self):
        if self.error:
            return "ERROR DE CARGA", RED
        if not self.playback:
            return "PREPARANDO MISIÓN", GOLD
        state = self.state
        if state.outcome == "success":
            return "RESCATE COMPLETO", GREEN
        if state.outcome == "destroyed":
            return "ROBOT DESTRUIDO", RED
        if state.outcome == "time_limit":
            return "TIEMPO AGOTADO", GOLD
        if self.playback.playing:
            return "MISIÓN EN CURSO", CYAN
        return ("LISTO PARA INICIAR" if state.steps == 0 else "EN PAUSA"), MUTED

    def render(self, mouse=(-1, -1)):
        self.mouse, self.controls = mouse, {}
        self.canvas.fill(BG)
        pygame.draw.rect(self.canvas, CYAN, (28, 29, 34, 34), border_radius=10)
        pygame.draw.rect(self.canvas, BG, (42, 36, 6, 20), border_radius=2)
        pygame.draw.rect(self.canvas, BG, (35, 43, 20, 6), border_radius=2)
        self.text("SAR-Bot", (77, 21), 30, bold=True)
        self.text("Dos robots. Una misión de rescate.", (78, 62), 15, MUTED)
        status, status_color = self._status()
        pygame.draw.circle(self.canvas, status_color, (1037, 47), 4)
        self.text(status, (1050, 37), 13, status_color, bold=True)
        self.card((28, 112, 824, 598))
        self.card((876, 112, 376, 718))
        self._board()
        self._robots()
        self._controls()
        self.text("Tiempo simulado · La velocidad de reproducción no modifica el daño.",
                  (30, 838), 12, MUTED)
        if self.dropdown:
            self._dropdown()
        return self.canvas

    def _board(self):
        scenario, state = self.scenario, self.state
        name = SCENARIO_NAMES.get(scenario.name, scenario.name.replace("_", " "))
        self.text(name, (52, 130), 21, bold=True)
        self.text(f"{scenario.width} × {scenario.height}  /  edificio simulado", (582, 138), 13, MUTED)
        for x, label, value, color in (
            (52, "PERSONAS RESCATADAS", f"{len(state.rescued)} / 2", GREEN),
            (314, "PASOS DE LA MISIÓN", f"{state.steps} / {scenario.max_steps}", TEXT),
            (576, "DAÑO DEL EQUIPO", str(sum(r.damage for r in state.robots)), GOLD),
        ):
            pygame.draw.rect(self.canvas, INSET, (x, 170, 252, 54), border_radius=9)
            self.text(label, (x + 14, 177), 10, MUTED, bold=True)
            self.text(value, (x + 14, 190), 23, color, bold=True)
        cell = min(432 // scenario.width, 432 // scenario.height)
        gx, gy = 60, 246
        self.grid = (gx, gy, cell)
        for x in range(scenario.width):
            self.text(chr(65 + x), (gx + x * cell + cell // 2, gy - 12), 11, MUTED, center=True)
        for y in range(scenario.height):
            self.text(y + 1, (gx - 14, gy + y * cell + cell // 2), 11, MUTED, center=True)
        max_temp = max(t for row in scenario.temperatures for t in row)
        focus = next(((x, y) for y in range(scenario.height) for x in range(scenario.width)
                      if scenario.temperature_at((x, y)) == max_temp), None) if max_temp > 35 else None
        for y in range(scenario.height):
            for x in range(scenario.width):
                rect = pygame.Rect(gx + x * cell + 2, gy + y * cell + 2, cell - 4, cell - 4)
                position, temperature = (x, y), scenario.temperature_at((x, y))
                color = heat_color(temperature) if self.show_heat else INSET
                pygame.draw.rect(self.canvas, color, rect, border_radius=5)
                if position in scenario.walls:
                    pygame.draw.rect(self.canvas, (51, 65, 81), rect, border_radius=5)
                    for delta in range(12, cell - 8, 14):
                        pygame.draw.line(self.canvas, (68, 82, 97),
                                         (rect.x + 8, rect.y + delta), (rect.x + delta, rect.y + 8), 2)
                elif self.show_heat:
                    self.text(f"{temperature:.0f}°", (rect.right - 27, rect.bottom - 18), 10, MUTED)
                if position == scenario.base:
                    pygame.draw.rect(self.canvas, GREEN, rect.inflate(-13, -13), 2, border_radius=7)
                    self.text("BASE", (rect.x + 10, rect.y + 6), 9, GREEN, bold=True)
                if position == focus:
                    fx, fy = rect.x + 8, rect.y + 7
                    pygame.draw.polygon(self.canvas, GOLD,
                                        [(fx + 5, fy), (fx + 12, fy + 8), (fx + 10, fy + 15),
                                         (fx + 2, fy + 15), (fx, fy + 8), (fx + 3, fy + 5)])
        if self.playback and self.show_paths:
            overlay = pygame.Surface(SIZE, pygame.SRCALPHA)
            for robot_id, color in enumerate(ROBOT_COLORS):
                points = []
                for snapshot in self.playback.episode.states[:self.playback.index + 1]:
                    x, y = snapshot.robots[robot_id].position
                    point = (gx + x * cell + cell // 2 + robot_id * 4 - 2,
                             gy + y * cell + cell // 2 + robot_id * 4 - 2)
                    if not points or point != points[-1]:
                        points.append(point)
                if len(points) > 1:
                    pygame.draw.lines(overlay, (*color, 110), False, points, 3)
            self.canvas.blit(overlay, (0, 0))
        for victim_id, (x, y) in enumerate(scenario.victims):
            if victim_id in state.rescued or any(r.carrying == victim_id for r in state.robots):
                continue
            cx, cy = gx + x * cell + cell // 2, gy + y * cell + cell // 2
            pygame.draw.circle(self.canvas, GOLD, (cx, cy - 9), 7)
            pygame.draw.rect(self.canvas, GOLD, (cx - 8, cy + 1, 16, 16), border_radius=5)
        together = state.robots[0].position == state.robots[1].position
        for i, robot in enumerate(state.robots):
            x, y = robot.position
            cx = gx + x * cell + cell // 2 + ((i * 2 - 1) * 15 if together else 0)
            cy = gy + y * cell + cell // 2
            radius = 16 if together else 21
            pygame.draw.circle(self.canvas, BG, (cx, cy), radius + 3)
            pygame.draw.circle(self.canvas, ROBOT_COLORS[i], (cx, cy), radius)
            self.text(i + 1, (cx, cy - 1), 18, BG, bold=True, center=True)
            if robot.carrying is not None:
                pygame.draw.circle(self.canvas, GOLD, (cx + radius - 1, cy - radius + 1), 7)
                self.text("+", (cx + radius - 1, cy - radius), 13, BG, bold=True, center=True)
        self._mission_details()
        self.text("1 / 2  Robots     •     Persona     •     Base segura     •     # Obstáculo",
                  (60, 686), 12, MUTED)
        mx, my = self.mouse
        if self.dropdown is None and gx <= mx < gx + cell * scenario.width and gy <= my < gy + cell * scenario.height:
            x, y = (mx - gx) // cell, (my - gy) // cell
            t = scenario.temperature_at((x, y))
            rect = pygame.Rect(532, 609, 294, 68)
            pygame.draw.rect(self.canvas, INSET, rect, border_radius=7)
            self.text(f"Celda {chr(65+x)}{y+1}  ·  {t:g} °C", (546, 619), 14, bold=True)
            label = ("Obstáculo · no transitable" if (x, y) in scenario.walls else
                     f"{damage_rate(t)} de daño por paso de exposición")
            self.text(label, (546, 647), 12, MUTED)

    def _mission_details(self):
        state = self.state
        self.text("SOBREVIVIENTES", (532, 248), 11, MUTED, bold=True)
        for victim_id in range(2):
            y = 274 + victim_id * 78
            delivered = victim_id in state.rescued
            carrier = next((i + 1 for i, r in enumerate(state.robots) if r.carrying == victim_id), None)
            status = "En la base" if delivered else f"Con robot {carrier}" if carrier else "Por rescatar"
            color = GREEN if delivered else CYAN if carrier else GOLD
            self.card((532, y, 294, 64), INSET, 9)
            pygame.draw.circle(self.canvas, color, (550, y + 21), 4)
            self.text(f"Persona {victim_id + 1}", (563, y + 9), 15, bold=True)
            self.text(status, (550, y + 35), 13, color)
        self.text("EXPOSICIÓN TÉRMICA", (532, 442), 11, MUTED, bold=True)
        for i, (label, damage, temperature) in enumerate((
            ("Menos de 40 °C", 0, 25), ("40 a <60 °C", 2, 45),
            ("60 a <80 °C", 5, 65), ("80 °C o más", 10, 90)
        )):
            y = 475 + i * 31
            pygame.draw.rect(self.canvas, heat_color(temperature), (532, y, 14, 14), border_radius=3)
            self.text(label, (557, y - 3), 14, MUTED)
            self.text(f"{'−' if damage else ''}{damage} / paso", (740, y - 3), 13, TEXT)
        self.wrap("Cada paso expone a ambos robots, incluso si esperan.", 532, 615, 288, 14)

    def _robots(self):
        for i, robot in enumerate(self.state.robots):
            x, y = 28 + i * 420, 728
            color = ROBOT_COLORS[i]
            self.card((x, y, 404, 102))
            pygame.draw.circle(self.canvas, color, (x + 22, y + 24), 5)
            self.text(f"Robot {i + 1}", (x + 36, y + 11), 18, bold=True)
            status = ("Fuera de servicio" if robot.integrity == 0 else
                      "En traslado" if robot.carrying is not None else
                      "En base" if robot.position == self.scenario.base else "Buscando")
            self.text(status, (x + 133, y + 16), 12, MUTED)
            self.text(f"{robot.integrity}%", (x + 334, y + 10), 21, color, bold=True)
            pygame.draw.rect(self.canvas, INSET, (x + 20, y + 47, 364, 6), border_radius=3)
            if robot.integrity:
                pygame.draw.rect(self.canvas, color if robot.integrity > 30 else RED,
                                 (x + 20, y + 47, round(364 * robot.integrity / 100), 6), border_radius=3)
            temperature = self.scenario.temperature_at(robot.position)
            cargo = f"Persona {robot.carrying + 1}" if robot.carrying is not None else "Sin carga"
            self.text(f"{temperature:g} °C     ·     Daño {robot.damage}     ·     {cargo}",
                      (x + 20, y + 69), 13, MUTED)

    def _controls(self):
        self.text("CONTROL DE MISIÓN", (900, 137), 12, MUTED, bold=True)
        self.text("ESCENARIO", (900, 174), 11, MUTED, bold=True)
        name = SCENARIO_NAMES.get(self.scenario.name, self.scenario.name)
        self.button("scenario", name, (900, 194, 328, 42))
        self.text("ESTRATEGIA", (900, 257), 11, MUTED, bold=True)
        _, label, description = STRATEGIES[self.strategy_index]
        self.button("strategy", label, (900, 277, 328, 42))
        for y in (215, 298):
            pygame.draw.lines(self.canvas, MUTED, False, [(1202, y - 3), (1207, y + 2), (1212, y - 3)], 2)
        self.wrap(description, 901, 330, 326, 14)
        if self.playback:
            label = ("Repetir misión" if self.playback.finished else
                     "Pausar" if self.playback.playing else
                     "Iniciar misión" if self.state.steps == 0 else "Continuar")
        else:
            label = "No disponible" if self.error else "Preparando…"
        self.button("play", label, (900, 388, 328, 48), primary=True, enabled=self.playback is not None)
        self.button("step", "Un paso", (900, 448, 158, 40),
                    enabled=self.playback is not None and not self.playback.finished)
        self.button("reset", "Reiniciar", (1070, 448, 158, 40), enabled=self.playback is not None)
        self.text("VELOCIDAD", (900, 514), 11, MUTED, bold=True)
        self.button("slower", "−", (900, 539, 42, 34))
        self.text(f"{self.speed} pasos / segundo", (1064, 556), 15, TEXT, center=True)
        self.button("faster", "+", (1186, 539, 42, 34))
        self.switch("heat", "Mapa de calor", self.show_heat, 598)
        self.switch("paths", "Mostrar recorridos", self.show_paths, 638)
        pygame.draw.line(self.canvas, BORDER, (900, 686), (1228, 686))
        if self.error:
            self.wrap(self.error, 900, 701, 328, 13, RED)
        else:
            self.wrap("Cambiar escenario o estrategia reinicia la misión.", 900, 701, 328, 13)
            self.text("ESPACIO  Pausa / continúa", (900, 754), 12, MUTED)
            self.text("N  Un paso     R  Reiniciar", (900, 779), 12, MUTED)
            self.text("H  Calor     T  Recorridos", (900, 801), 12, MUTED)

    def _dropdown(self):
        self.dropdown_rows = []
        is_scenario = self.dropdown == "scenario"
        values = [SCENARIO_NAMES.get(s.name, s.name) for _, s in self.options] if is_scenario else [s[1] for s in STRATEGIES]
        selected = self.scenario_index if is_scenario else self.strategy_index
        y = 240 if is_scenario else 323
        self.card((894, y, 340, 36 * len(values) + 12), (24, 39, 57), 10)
        for index, label in enumerate(values):
            rect = pygame.Rect(900, y + 6 + 36 * index, 328, 36)
            self.dropdown_rows.append((index, rect))
            if index == selected or rect.collidepoint(self.mouse):
                pygame.draw.rect(self.canvas, (38, 61, 79), rect, border_radius=6)
            self.text(label, (rect.x + 10, rect.y + 7), 14, CYAN if index == selected else TEXT)


def run_app(app: RescueApp):
    desktop_width, desktop_height = pygame.display.get_desktop_sizes()[0]
    initial_scale = min(1.0, max(1, desktop_width - 64) / SIZE[0],
                        max(1, desktop_height - 96) / SIZE[1])
    initial_size = tuple(max(1, round(value * initial_scale)) for value in SIZE)
    window = pygame.display.set_mode(initial_size, pygame.RESIZABLE)
    pygame.display.set_caption("SAR-Bot · Rescate cooperativo")
    clock = pygame.time.Clock()
    running = True
    try:
        while running:
            elapsed = clock.tick(60) / 1000
            width, height = window.get_size()
            scale = min(width / SIZE[0], height / SIZE[1])
            offset = ((width - round(SIZE[0] * scale)) // 2, (height - round(SIZE[1] * scale)) // 2)
            def logical(position):
                return (int((position[0] - offset[0]) / scale), int((position[1] - offset[1]) / scale))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    app.click(logical(event.pos))
                elif event.type == pygame.KEYDOWN:
                    app.key(event.key)
            app.update(elapsed)
            canvas = app.render(logical(pygame.mouse.get_pos()))
            window.fill(BG)
            scaled = pygame.transform.smoothscale(canvas, (max(1, round(SIZE[0] * scale)), max(1, round(SIZE[1] * scale))))
            window.blit(scaled, offset)
            pygame.display.flip()
    finally:
        app.close()
        pygame.quit()
