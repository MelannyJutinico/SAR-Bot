"""Render Pygame del estado del motor.

Solo dibuja un :class:`RescueSim`: no calcula daño ni decide rescates.
La persona 3 puede rediseñar colores, iconos y panel sin tocar las reglas.
"""

from __future__ import annotations

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from sar_bot.core.engine import Outcome, RescueSim, VictimStatus  # noqa: E402
from sar_bot.core.grid import Pos  # noqa: E402
from sar_bot.core.rules import RulesConfig  # noqa: E402

FLOOR = (237, 232, 223)
GRID_LINE = (196, 188, 175)
WALL = (59, 63, 69)
BASE = (143, 209, 143)
BASE_EDGE = (52, 128, 60)
HEAT_COLORS = ((247, 215, 116), (242, 158, 76), (214, 66, 40), (160, 30, 30))
HOTSPOT = (120, 20, 20)
VICTIM = (123, 63, 191)
ROBOT_COLORS = ((31, 111, 235), (13, 148, 136))
DESTROYED = (120, 120, 120)
PANEL_BG = (30, 34, 40)
TEXT = (236, 236, 236)
MUTED = (160, 167, 178)
GOOD = (92, 200, 120)
BAD = (232, 84, 72)
WARN = (240, 182, 62)

OUTCOME_LABELS = {
    Outcome.RUNNING: ("En curso", TEXT),
    Outcome.SUCCESS: ("Misión completa", GOOD),
    Outcome.DESTROYED: ("Robot destruido", BAD),
    Outcome.TIMEOUT: ("Límite de pasos", WARN),
}

CONTROLS = (
    "Espacio  pausa / continúa",
    "→  un paso (en pausa)",
    "R  reiniciar escenario",
    "N / B  siguiente / anterior",
    "+ / -  velocidad",
    "E  cambiar estrategia",
    "Esc  salir",
)

_FONT_NAMES = "segoeui,arial,dejavusans"


class Renderer:
    def __init__(
        self,
        shape: tuple[int, int],
        rules: RulesConfig | None = None,
        cell_size: int = 88,
        panel_width: int = 330,
    ) -> None:
        pygame.font.init()
        self.rules = rules or RulesConfig()
        self.rows, self.cols = shape
        self.cell = cell_size
        self.grid_size = (self.cols * cell_size, self.rows * cell_size)
        self.panel_width = panel_width
        self.size = (self.grid_size[0] + panel_width, max(self.grid_size[1], 640))
        self.fonts = {
            "title": pygame.font.SysFont(_FONT_NAMES, 26, bold=True),
            "text": pygame.font.SysFont(_FONT_NAMES, 17),
            "bold": pygame.font.SysFont(_FONT_NAMES, 17, bold=True),
            "small": pygame.font.SysFont(_FONT_NAMES, 14),
            "cell": pygame.font.SysFont(_FONT_NAMES, 13, bold=True),
        }

    # ------------------------------------------------------------------ util

    def _band(self, temperature: float) -> int:
        """Índice de la franja de daño (-1 si no causa daño)."""
        index = -1
        for i, (threshold, rate) in enumerate(self.rules.damage_bands):
            if temperature >= threshold and rate > 0:
                index = i
        return index

    def _heat_color(self, temperature: float) -> tuple[int, int, int]:
        band = self._band(temperature)
        return FLOOR if band < 0 else HEAT_COLORS[min(band, len(HEAT_COLORS) - 1)]

    def _rect(self, pos: Pos) -> pygame.Rect:
        row, col = pos
        return pygame.Rect(col * self.cell, row * self.cell, self.cell, self.cell)

    def _text(self, surface, text, pos, font="text", color=TEXT, center=False) -> int:
        image = self.fonts[font].render(text, True, color)
        rect = image.get_rect()
        if center:
            rect.center = pos
        else:
            rect.topleft = pos
        surface.blit(image, rect)
        return rect.bottom

    # ----------------------------------------------------------------- dibujo

    def draw(
        self,
        surface: pygame.Surface,
        sim: RescueSim,
        *,
        strategy: str = "",
        paused: bool = False,
        speed: float | None = None,
        episode: tuple[int, int] | None = None,
        show_controls: bool = True,
    ) -> None:
        surface.fill(PANEL_BG)
        self._draw_grid(surface, sim)
        self._draw_panel(surface, sim, strategy, paused, speed, episode, show_controls)

    def render_array(self, sim: RescueSim, **kwargs) -> np.ndarray:
        """Imagen RGB (alto, ancho, 3) sin abrir ventana."""
        surface = pygame.Surface(self.size)
        self.draw(surface, sim, **kwargs)
        return np.transpose(pygame.surfarray.array3d(surface), (1, 0, 2)).copy()

    def _draw_grid(self, surface: pygame.Surface, sim: RescueSim) -> None:
        layout, scenario = sim.layout, sim.scenario
        cell = self.cell
        for row in range(self.rows):
            for col in range(self.cols):
                pos = (row, col)
                rect = self._rect(pos)
                temperature = scenario.temperature_at(pos)
                if layout.walls[pos]:
                    color = WALL
                elif pos == layout.base:
                    color = BASE
                else:
                    color = self._heat_color(temperature)
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, GRID_LINE, rect, 1)
                if not layout.walls[pos] and pos != layout.base and self._band(temperature) >= 0:
                    self._text(surface, f"{temperature:.0f}°", (rect.x + 5, rect.y + 3), "cell", (60, 30, 20))

        base_rect = self._rect(layout.base)
        pygame.draw.rect(surface, BASE_EDGE, base_rect.inflate(-4, -4), 3)
        self._text(surface, "BASE", (base_rect.centerx, base_rect.bottom - 12), "cell", BASE_EDGE, center=True)

        if scenario.hotspot is not None and self._band(scenario.temperature_at(scenario.hotspot)) >= 0:
            hot = self._rect(scenario.hotspot)
            pygame.draw.circle(surface, HOTSPOT, (hot.right - 14, hot.y + 14), 7, 3)

        for victim in sim.victims:
            if victim.status is VictimStatus.WAITING:
                center = self._rect(victim.origin).center
                pygame.draw.circle(surface, VICTIM, center, int(cell * 0.2))
                self._text(surface, "V", center, "bold", (255, 255, 255), center=True)

        positions = [robot.pos for robot in sim.robots]
        shared = positions[0] == positions[1]
        for i, robot in enumerate(sim.robots):
            rect = self._rect(robot.pos)
            size = int(cell * (0.42 if shared else 0.58))
            body = pygame.Rect(0, 0, size, size)
            offset = int(cell * 0.2) * (-1 if i == 0 else 1) if shared else 0
            body.center = (rect.centerx + offset, rect.centery)
            alive = robot.operational
            pygame.draw.rect(surface, ROBOT_COLORS[i] if alive else DESTROYED, body, border_radius=8)
            self._text(surface, f"R{i}", body.center, "bold", (255, 255, 255), center=True)
            if robot.carrying is not None:
                pygame.draw.circle(surface, VICTIM, (body.right - 4, body.top + 4), 8)
                pygame.draw.circle(surface, (255, 255, 255), (body.right - 4, body.top + 4), 8, 2)
            if not alive:
                pygame.draw.line(surface, BAD, body.topleft, body.bottomright, 4)
                pygame.draw.line(surface, BAD, body.topright, body.bottomleft, 4)

        if self.size[1] - self.grid_size[1] >= 30:
            y = self.grid_size[1] + 12
            pygame.draw.circle(surface, VICTIM, (18, y + 9), 8)
            self._text(surface, "víctima esperando", (32, y), "small", MUTED)
            pygame.draw.circle(surface, VICTIM, (180, y + 9), 6)
            pygame.draw.circle(surface, (255, 255, 255), (180, y + 9), 6, 2)
            self._text(surface, "víctima transportada", (192, y), "small", MUTED)
            pygame.draw.circle(surface, (230, 120, 100), (360, y + 9), 7, 3)
            self._text(surface, "foco térmico", (374, y), "small", MUTED)

    def _draw_panel(self, surface, sim, strategy, paused, speed, episode, show_controls) -> None:
        x = self.grid_size[0] + 20
        width = self.panel_width - 40
        y = self._text(surface, "SAR-Bot", (x, 16), "title") + 8

        label, color = OUTCOME_LABELS[sim.outcome]
        lines = [
            ("Escenario", sim.scenario.scenario_id + (f"  ({episode[0]}/{episode[1]})" if episode else "")),
            ("Estrategia", strategy or "-"),
            ("Paso", f"{sim.step_count} / {sim.rules.max_steps}"),
            ("Rescatadas", f"{sim.rescued_count} / {len(sim.victims)}"),
        ]
        for name, value in lines:
            self._text(surface, name, (x, y), "small", MUTED)
            y = self._text(surface, value, (x + 95, y - 2), "text") + 4
        self._text(surface, "Estado", (x, y), "small", MUTED)
        y = self._text(surface, label, (x + 95, y - 2), "bold", color) + 12

        initial = sim.rules.initial_integrity
        for i, robot in enumerate(sim.robots):
            pygame.draw.rect(surface, ROBOT_COLORS[i], pygame.Rect(x, y + 3, 14, 14), border_radius=3)
            carga = f"víctima {robot.carrying}" if robot.carrying is not None else "sin carga"
            y = self._text(surface, f"Robot {i}  ·  {carga}", (x + 22, y), "bold") + 4
            fraction = max(0.0, robot.integrity / initial)
            bar = pygame.Rect(x, y, width, 12)
            pygame.draw.rect(surface, (60, 66, 76), bar, border_radius=6)
            fill_color = GOOD if fraction > 0.6 else WARN if fraction > 0.3 else BAD
            if fraction > 0:
                pygame.draw.rect(surface, fill_color, pygame.Rect(x, y, int(width * fraction), 12), border_radius=6)
            y += 16
            y = self._text(
                surface, f"Integridad {robot.integrity:g}  ·  daño acumulado {robot.damage_taken:g}", (x, y), "small", MUTED
            ) + 10

        playback = f"Reproducción: {speed:g} pasos/s" if speed is not None else ""
        if paused:
            playback += "   PAUSA"
        if playback:
            y = self._text(surface, playback, (x, y), "small", WARN if paused else MUTED) + 12

        y = self._text(surface, "Tasa de daño por paso", (x, y), "small", MUTED) + 4
        legend = [(FLOOR, f"< {self.rules.damage_bands[0][0]:g} °C  ·  0")]
        bands = self.rules.damage_bands
        for i, (threshold, rate) in enumerate(bands):
            upper = f"{bands[i + 1][0]:g}" if i + 1 < len(bands) else ""
            text = f"{threshold:g}–{upper} °C  ·  {rate:g}" if upper else f"≥ {threshold:g} °C  ·  {rate:g}"
            legend.append((HEAT_COLORS[min(i, len(HEAT_COLORS) - 1)], text))
        for swatch, text in legend:
            pygame.draw.rect(surface, swatch, pygame.Rect(x, y + 2, 16, 14), border_radius=3)
            y = self._text(surface, text, (x + 24, y), "small") + 2

        if show_controls:
            y += 10
            for line in CONTROLS:
                y = self._text(surface, line, (x, y), "small", MUTED) + 1
