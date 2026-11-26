"""Interfaz Pygame. Reproduce los estados del motor, sin duplicar sus reglas."""

from concurrent.futures import ThreadPoolExecutor
import math
from pathlib import Path
import traceback
from threading import Event
from hashlib import file_digest

import pygame

from sar_bot.core import RescueSimulation, Scenario, damage_rate, ViabilityStatus
from .resources import load_ui_scenario
from .history import History
from .comparison import Comparison, ComparisonRequest
from .playback import Playback, prepare_episode
from .editor import ScenarioDraft, Viewport, draw_editor_controls, pixel_to_cell
from .preparation import PreparationRequest, prepare_mission
from .scenario_store import ScenarioStore, draw_library
from .model_catalog import discover_models
from .views import MissionResult, person_status, draw_preparation, draw_execution, draw_analysis, draw_models

SIZE = (1280, 860)
BG = (10, 17, 28)
PANEL = (17, 27, 42)
INSET = (23, 36, 53)
BORDER = (39, 55, 74)
TEXT = (230, 238, 246)
MUTED = (176, 191, 209)
CYAN = (56, 205, 216)
PURPLE = (169, 144, 255)
GOLD = (255, 193, 91)
GREEN = (100, 221, 168)
RED = (255, 119, 111)
ROBOT_COLORS = (CYAN, PURPLE)

STRATEGIES = [
    ("dqn", "Red neuronal", "Usa una red entrenada. El modelo elegido determina qué decisiones aprende."),
    ("shortest", "Ruta corta", "Planifica recorridos cortos. No tiene en cuenta el daño por calor."),
    ("thermal", "Ruta segura (calor)", "Planifica rutas considerando distancia y calor. Puede dar un rodeo para reducir daño."),
    ("random", "Movimientos al azar", "Mueve los robots al azar. Sirve como referencia para comparar resultados."),
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
    "edificio_10x10_tres_personas": "Edificio 10 × 10 · Tres personas",
    "v2_rescate_cercano_tres_personas": "V2 · Rescate cercano",
    "centro_coordinacion_12x12": "Centro de coordinación",
    "desvio_termico_12x12": "Desvío con calor",
    "demo_conocida_12x12": "Ejemplo aprendido (caso conocido)",
}


def scenario_label(scenario):
    return SCENARIO_NAMES.get(scenario.name, scenario.name.replace("_", " "))


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
        self._closed = False
        self.neural_focus = False
        # Solo plantillas de desarrollo, no curriculum/validation/test.
        paths = sorted([*(root / "scenarios").glob("*.json"),
                        *(root / "scenarios" / "v2").glob("*.json")])
        self.options = [(p, load_ui_scenario(p)) for p in paths]
        if scenario_path.resolve() not in {p.resolve() for p, _ in self.options}:
            self.options.append((scenario_path, load_ui_scenario(scenario_path)))
        self.scenario_index = next(i for i, (p, _) in enumerate(self.options)
                                   if p.resolve() == scenario_path.resolve())
        self.strategy_index = next(i for i, s in enumerate(STRATEGIES) if s[0] == strategy)
        self.view = "preparation"
        self.learning_enabled = False
        self.learning_executor = None
        self.learning_future = None
        self.learning_message = "Evaluacion: el modelo permanece fijo."
        self.learning_stats = None
        self.learning_submitted = set()
        self.learning_directory = None
        self._session_paths = {}
        self.history = History()
        self.history_visible = False
        self.history_selected = None
        self.history_page = 0
        self.history_event_page = 0
        self.history_step = 0
        self.history_files = None
        self.history_file_page = 0
        self.comparison_recorded = set()
        self.comparison = None
        self.last_comparison = None
        self.comparison_show_saved = False
        self.export_executor = None
        self.export_future = None
        self.export_context = None
        self.last_comparison_export = None
        self.comparison_executor = None
        self.comparison_generation = 0
        self.comparison_visible = False
        self.comparison_replaying = False
        self.comparison_message = ""
        self.last_result = None
        self.last_episode = None
        self.last_state = None
        self.models = discover_models(root, model_path)
        self.models_open = False
        self.model_page = 0
        self.playback = None
        self.editor = None
        self.speed = 3
        self.show_heat = True
        self.show_paths = True
        self.dropdown = None
        self.error = None
        self.error_kind = None
        self.fonts = {}
        self.controls = {}
        self.disabled_controls = set()
        self.dropdown_rows = []
        self.executor = ThreadPoolExecutor(max_workers=2) if asynchronous else None
        self.future = None
        self.request = None
        self.generation = 0
        self.cancelled = Event()
        self.viability = None
        self.validation_status = None
        self._template_index = None
        self.configured = None
        self.draft = None
        self.store = ScenarioStore(root / "outputs" / "custom_scenarios")
        self.file_executor = ThreadPoolExecutor(max_workers=1) if asynchronous else None
        self.file_future = None
        self.file_request = 0
        self.file_context = None
        self.file_operation = None
        self.file_message = ""
        self.last_saved_path = None
        self.library_open = False
        self.library_files = ()
        self.library_page = 0
        self.mouse = (-1, -1)
        self.canvas = pygame.Surface(SIZE)
        self._select()

    @property
    def scenario(self):
        return self.configured or self.options[self.scenario_index][1]

    @property
    def learning_active(self):
        return self.learning_enabled and STRATEGIES[self.strategy_index][0] == "dqn"

    def _start_learning(self):
        episode = self.playback.episode
        request = self.request
        if (self._closed or self.learning_future or not request.learning or not episode.learning_id
                or episode.learning_id in self.learning_submitted):
            return
        self.learning_submitted.add(episode.learning_id)
        self.learning_message = "Aprendiendo y comprobando la nueva red antes de guardarla..."
        from .preparation import learn_completed_episode
        if self.learning_executor is None:
            self.learning_executor = ThreadPoolExecutor(max_workers=1)
        self.learning_future = self.learning_executor.submit(learn_completed_episode, request, episode)

    def _poll_learning(self):
        if self.learning_future and self.learning_future.done():
            future, self.learning_future = self.learning_future, None
            try:
                self.learning_stats = future.result()
                result = self.learning_stats
                guard = result.get("last_guard")
                if guard and not guard["accepted"]:
                    self.learning_message = ("Memoria guardada. Se mantiene la red anterior: "
                                             + ("la actualización empeoró en los controles."
                                                if guard["reason"] == "regression_on_controls"
                                                else "no se pudo comprobar la actualización."))
                else:
                    self.learning_message = (f"Guardado: {result['missions']} misiones, {result['buffer_size']} recuerdos, "
                                             f"{result['updates']} actualizaciones.")
                if result.get("recovered"):
                    self.learning_message += " Se recupero un checkpoint anterior."
            except Exception as error:
                self.learning_message = "No se guardo aprendizaje: " + str(error)[:150]

    def wait_for_learning(self):
        if self.learning_future:
            try:
                self.learning_future.result()
            finally:
                self._poll_learning()
        return self.learning_stats

    @property
    def state(self):
        return self.playback.state if self.playback else self.preview

    @property
    def display_scenario(self):
        if self.comparison_replaying and self.playback and self.view != "analysis":
            return self.playback.episode.scenario
        return self.last_episode.scenario if self.view == "analysis" and self.last_episode else self.scenario

    @property
    def display_state(self):
        return self.last_state if self.view == "analysis" and self.last_state else self.state

    @property
    def comparison_for_display(self):
        if self.comparison_show_saved or self.comparison is None:
            return self.last_comparison
        return self.comparison

    def _export_context(self):
        comparison = self.comparison_for_display
        return (self._comparison_context(), self.view, self.comparison_visible,
                self.history_visible, comparison.request if comparison else None)

    def _start_comparison_export(self):
        comparison = self.comparison_for_display
        if comparison is None or (self.export_future and not self.export_future.done()):
            return
        try:
            snapshot = comparison.snapshot() if isinstance(comparison, Comparison) else comparison
        except ValueError as error:
            self.comparison_message = str(error)
            return
        if self.export_executor is None:
            self.export_executor = ThreadPoolExecutor(max_workers=1)
        self.export_context = self._export_context()
        self.comparison_message = "Exportando CSV en segundo plano..."
        self.export_future = self.export_executor.submit(snapshot.export, self.root / "outputs" / "comparisons")

    def _start_replay(self, episode, strategy, model, seed):
        self.cancelled.set()
        if self.future:
            self.future.cancel()
        self.future = None
        self.error = None
        self.error_kind = None
        self.file_message = ""
        self.viability = self.validation_status = None
        self.playback = Playback(episode, self.speed)
        self.comparison_replaying = True
        self.request = PreparationRequest(self.generation, episode.configuration_id, strategy, model, seed)
        self.set_view("execution")

    def _comparison_context(self):
        return (self.generation, self.scenario.configuration_id, self.strategy_index,
                str(Path(self.model_path).resolve()) if self.model_path else None,
                self.seed, self.draft.positions if self.draft is not None else None)

    def _invalidate_comparison(self):
        self.comparison_recorded.clear()
        self.comparison_generation += 1
        if self.comparison:
            self.comparison.close()
        self.comparison = None
        self.comparison_visible = False
        self.comparison_show_saved = False
        self.comparison_message = ""

    def _compare(self):
        if self.learning_future:
            self.learning_message = "Espera a que se guarde el aprendizaje antes de comparar."
            return
        self.history.invalidate_io()
        try:
            # Public Scenario construction validates the full snapshot, including imports.
            source = self.editor.build() if self.editor is not None else self.scenario
            frozen = Scenario.from_dict(source.to_dict())
        except (ValueError, TypeError) as error:
            self.error = str(error)
            return
        self._invalidate_comparison()
        self.cancelled.set()
        if self.future:
            self.future.cancel()
        self.future = None
        if self.playback:
            self.playback.playing = False
        model = str(Path(self.model_path).resolve()) if self.model_path else None
        request = ComparisonRequest(self.comparison_generation, self._comparison_context(),
                                    frozen, model, self.seed)
        if self.comparison_executor is None:
            self.comparison_executor = ThreadPoolExecutor(max_workers=4)
        self.comparison = Comparison(request, self.model_problem(), self.comparison_executor)
        self.set_view("analysis")
        self.comparison_visible = True
        self.history_visible = False

    def _invalidate(self):
        self.history.invalidate_io()
        self._invalidate_comparison()
        self.comparison_replaying = False
        self.file_message = ""
        self.generation += 1
        self.cancelled.set()
        if self.future:
            self.future.cancel()
        self.future, self.request = None, None
        self.cancelled = Event()
        self.playback, self.viability, self.validation_status = None, None, None
        self.error = None
        self.error_kind = None

    def _identity(self):
        strategy = STRATEGIES[self.strategy_index][0]
        model = str(Path(self.model_path).resolve()) if strategy == "dqn" and self.model_path else None
        learning = self.learning_active
        session_dir = None
        if learning and model:
            key = (model, self.scenario.width, self.scenario.height, self.scenario.victim_count)
            if key not in self._session_paths:
                try:
                    with Path(model).open("rb") as stream:
                        checksum = file_digest(stream,"sha256").hexdigest()[:12]
                    name = f"{key[1]}x{key[2]}-{key[3]}-{checksum}"
                    self._session_paths[key] = (self.root/"outputs/learning_sessions"/name).resolve()
                except OSError:
                    pass
            if key in self._session_paths:
                self.learning_directory = self._session_paths[key]
                session_dir = str(self.learning_directory)
        return PreparationRequest(self.generation, self.scenario.configuration_id,
                                  strategy, model, self.seed, learning, session_dir,
                                  str(self.root.resolve()) if learning else None)

    def _select(self):
        self.editor = None
        if self._template_index != self.scenario_index:
            self._template_index = self.scenario_index
            self.configured = self.options[self.scenario_index][1]
            self.draft = ScenarioDraft(self.configured) if self.configured.victim_count == 3 else None
        self._prepare()

    def selected_model(self):
        if self.model_path is None:
            return None
        path = Path(self.model_path).resolve()
        return next((entry for entry in self.models if entry.path == path), None)

    def model_problem(self):
        compatible = [entry for entry in self.models if entry.reason(self.scenario) is None]
        if not compatible:
            return f"DQN no disponible para {self.scenario.width}x{self.scenario.height} / {self.scenario.victim_count} personas."
        entry = self.selected_model()
        return entry.reason(self.scenario) if entry else "Selecciona un modelo con metadatos verificables."

    def set_view(self, view):
        if view != "analysis":
            self.history.invalidate_io()
        if view not in ("preparation", "execution", "analysis"):
            raise ValueError("Vista desconocida")
        if view == "preparation" and self.comparison_replaying:
            self.playback = None
            self.request = None
            self.preview = RescueSimulation(self.scenario).state
            self.comparison_replaying = False
        if self.playback:
            self.playback.playing = False
        self.dropdown = None
        self.models_open = False
        if self.library_open:
            self.file_request += 1
            if self.file_future:
                self.file_future.cancel()
            self.file_future = None
            self.library_open = False
        if view != "preparation":
            self.editor = None
        self.view = view

    def _prepare(self):
        if self.learning_future:
            self.learning_message = "Espera al guardado antes de preparar la siguiente mision."
            return
        self._invalidate()
        self.dropdown = None
        self.preview = RescueSimulation(self.scenario).state
        self.request = self._identity()
        if self.request.strategy == "dqn" and self.model_problem():
            self.error = self.model_problem() + " Selecciona otro modelo o una referencia."
            entry = self.selected_model()
            self.error_kind = ("model_invalid" if entry and entry.error else
                               "model_incompatible" if entry else "model_selection")
            return
        if self.executor:
            self.future = self.executor.submit(prepare_mission, self.request, self.scenario, self.cancelled)
        else:
            self._accept(prepare_mission(self.request, self.scenario, self.cancelled))

    def _accept(self, result):
        if self.editor is not None or self.request is None:
            return
        if result.request != self.request or self.request != self._identity():
            return
        if result.request.learning and result.learning_stats is not None:
            self.learning_stats = result.learning_stats
            self.learning_message = (f"Sesion: {self.learning_stats['missions']} misiones, "
                                     f"{self.learning_stats['buffer_size']} recuerdos. "
                                     "Se aprende y guarda al finalizar.")
            if result.learning_stats.get("recovered"):
                self.learning_message += " Recuperada copia anterior."
        if result.viability.status is not ViabilityStatus.STRUCTURAL_INVALID and (
                result.viability.configuration_id != self.request.configuration_id):
            self.error = "La certificacion no coincide con la configuracion actual"
            return
        self.viability = result.viability
        self.validation_status = result.viability.status.value
        if result.error:
            self.error = result.error
        elif result.episode is not None:
            if result.episode.configuration_id != self.request.configuration_id:
                self.error = "El episodio no coincide con la configuracion actual"
                return
            self.playback = Playback(result.episode, self.speed)

    def _apply_draft(self):
        try:
            scenario = self.editor.build()
        except ValueError as error:
            self._invalidate()
            self.validation_status = "structural_invalid"
            self.editor.message, self.editor.invalid = str(error), True
            return
        self.configured = scenario
        self.editor = None
        self.view = "execution"
        self._prepare()

    def _enter_editor(self):
        if self.scenario.victim_count != 3:
            return
        self._invalidate()
        self.dropdown = None
        self.preview = RescueSimulation(self.scenario).state
        self.editor = self.draft
        self.view = "preparation"

    def _file_identity(self):
        return (self._identity(), self.editor.positions if self.editor is not None else None)

    def _start_file(self, operation, argument=None):
        self.file_request += 1
        token = self.file_request
        if self.file_future:
            self.file_future.cancel()
        self.file_operation = operation
        self.file_context = self._file_identity()
        self.file_message = "Procesando archivo..."
        fn = {"save": self.store.save, "load": self.store.load,
              "list": self.store.list_files}[operation]
        args = () if operation == "list" else (argument,)
        if self.file_executor:
            self.file_future = self.file_executor.submit(fn, *args)
        else:
            self.file_future = None
            try:
                self._accept_file(token, fn(*args))
            except (OSError, ValueError, TypeError) as error:
                self._file_error(error)

    def _file_error(self, error):
        if isinstance(error, FileExistsError):
            self.file_message = "Ya existe esta configuracion. No se sobrescribio."
        elif isinstance(error, FileNotFoundError):
            self.file_message = "El archivo no existe o fue movido."
        elif isinstance(error, OSError):
            self.file_message = "No se pudo acceder al archivo. Revisa ruta y permisos."
        else:
            self.file_message = "Archivo invalido: " + str(error)[:110]

    def _accept_file(self, token, result):
        if token != self.file_request or self.file_context != self._file_identity():
            return
        if self.file_operation == "save":
            self.last_saved_path = result
            self.file_message = "Guardado: " + result.name
        elif self.file_operation == "list":
            self.library_files = result
            self.library_page = 0
            self.file_message = "Selecciona un archivo para cargar."
        else:
            # Public Scenario.load ya ha validado el objeto. Aplicar solo ahora:
            # un fallo de lectura nunca destruye el borrador ni la reproduccion.
            self._invalidate()
            self.configured = result
            self.draft = ScenarioDraft(result)
            self.editor = self.draft
            self.view = "preparation"
            self.preview = RescueSimulation(result).state
            self.library_open, self.dropdown = False, None
            self.file_message = "Cargado ID: " + result.configuration_id[:20] + "..."

    def _save_draft(self):
        try:
            scenario = self.editor.build() if self.editor is not None else self.scenario
            if scenario.victim_count != 3:
                raise ValueError("Selecciona una plantilla de tres personas")
        except ValueError as error:
            self.file_message = str(error)
            return
        self._start_file("save", scenario)

    def update(self, seconds):
        if self._closed:
            return
        self._poll_learning()
        if self.export_context is not None and self.export_context != self._export_context():
            self.comparison_message = ""
        if self.export_future and self.export_future.done():
            future, context = self.export_future, self.export_context
            self.export_future = None
            try:
                path = future.result()
                self.last_comparison_export = path
                if context == self._export_context():
                    self.comparison_message = "CSV exportado: " + path.name
            except (OSError, ValueError) as error:
                if context == self._export_context():
                    self.comparison_message = "No se pudo exportar CSV: " + str(error)
            self.export_context = None
        imported = self.history.poll()
        if imported:
            operation, result = imported
            if operation == "load":
                self.history_selected = result
                self.history_event_page = self.history_step = 0
                self.history_files = None
            elif operation == "list":
                self.history_files = result
                self.history_file_page = 0
        if self.comparison:
            if (self.comparison.request.generation != self.comparison_generation or
                    self.comparison.request.context != self._comparison_context()):
                self._invalidate_comparison()
            else:
                self.comparison.poll()
                if not self.comparison.futures and (self.last_comparison is None or
                        self.last_comparison.request != self.comparison.request):
                    self.last_comparison = self.comparison.snapshot()
                for strategy, row in self.comparison.rows.items():
                    if row.episode is not None and strategy not in self.comparison_recorded:
                        self.comparison_recorded.add(strategy)
                        request = self.comparison.request
                        self.history.record(row.episode, strategy,
                                            request.model if strategy == "dqn" else None, request.seed)
        if self.file_future and self.file_future.done():
            future, token, context = self.file_future, self.file_request, self.file_context
            self.file_future = None
            try:
                result = future.result()
                self._accept_file(token, result)
            except Exception as error:
                if context == self._file_identity():
                    self._file_error(error)
        if self.future and self.future.done():
            future, request = self.future, self.request
            self.future = None
            try:
                result = future.result()
                if request == self.request:
                    self._accept(result)
            except Exception as error:
                if request is not None and request == self.request and request == self._identity():
                    self.error = str(error) or "No se pudo preparar la mision"
        if self.playback and self.dropdown is None and self.editor is None and not self.library_open:
            self.playback.tick(seconds)
        if self.playback and self.state.outcome != "running" and self.request and not self.comparison_replaying and (self.last_episode is not self.playback.episode or self.last_state != self.state):
            self.last_result = MissionResult.capture(self)
            self.last_episode, self.last_state = self.playback.episode, self.state
            self.history.record(self.last_episode, self.request.strategy, self.request.model, self.request.seed)
        if (self.playback and self.playback.finished and self.request
                and self.request.learning and not self.comparison_replaying):
            self._start_learning()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.learning_executor:
            # El cierre espera el guardado acotado de una misión ya finalizada.
            self.learning_executor.shutdown(wait=True, cancel_futures=False)
            self._poll_learning()
        if self.export_executor:
            self.export_executor.shutdown(wait=False, cancel_futures=True)
        self.history.close()
        self._invalidate_comparison()
        if self.comparison_executor:
            self.comparison_executor.shutdown(wait=False, cancel_futures=True)
        self.file_request += 1
        if self.file_future:
            self.file_future.cancel()
        if self.file_executor:
            self.file_executor.shutdown(wait=False, cancel_futures=True)
        self._invalidate()
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
        words = []
        for word in value.split():
            chunk = ""
            for character in word:
                if chunk and font.size(chunk + character)[0] > width:
                    words.append(chunk)
                    chunk = ""
                chunk += character
            if chunk:
                words.append(chunk)
        line = ""
        for word in words:
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
        if not enabled:
            self.disabled_controls.add(key)
        hovered = rect.collidepoint(self.mouse) and enabled and self.dropdown is None
        color = CYAN if primary and enabled else ((36, 56, 76) if hovered else INSET)
        pygame.draw.rect(self.canvas, color, rect, border_radius=9)
        if not primary:
            pygame.draw.rect(self.canvas, BORDER, rect, 1, border_radius=9)
        self.text(label, rect.center, 16, BG if primary and enabled else TEXT if enabled else MUTED,
                  bold=primary, center=True)
        if key in ("scenario", "strategy"):
            pygame.draw.lines(self.canvas, CYAN if enabled else MUTED, False,
                              [(rect.right-21,rect.centery-3),(rect.right-16,rect.centery+2),
                               (rect.right-11,rect.centery-3)],2)

    def switch(self, key, label, value, y):
        self.text(label, (900, y + 3), 16)
        rect = pygame.Rect(1190, y, 38, 24)
        self.controls[key] = pygame.Rect(900, y - 4, 328, 32)
        pygame.draw.rect(self.canvas, CYAN if value else BORDER, rect, border_radius=12)
        pygame.draw.circle(self.canvas, BG if value else MUTED,
                           (rect.x + (26 if value else 12), rect.centery), 8)

    def compatible_models(self):
        """Índices originales para conservar la identidad al filtrar el catálogo."""
        return sorted(((i, entry) for i, entry in enumerate(self.models)
                       if entry.reason(self.scenario) is None
                       and (not self.neural_focus or entry.controller=="neural_assignment")),
                      key=lambda pair: (pair[1].controller!="neural_assignment",not pair[1].status.startswith("congelado"),
                                        pair[1].path.parent.name))

    def action(self, key):
        if key in ("mode_evaluate", "mode_learn"):
            if STRATEGIES[self.strategy_index][0] == "dqn" and not self.learning_future:
                if self.learning_enabled != (key == "mode_learn"):
                    self.action("learning_mode")
            return
        if self.learning_future and (key in {"scenario","strategy","models","edit","prepare","load_file"}
                                     or key.startswith("model_")):
            self.learning_message = "Guardando aprendizaje; espera antes de cambiar la mision."
            return
        if key == "learning_mode":
            if self.learning_future or STRATEGIES[self.strategy_index][0] != "dqn":
                self.learning_message = "Espera al guardado y selecciona DQN para cambiar el modo."
                return
            self.learning_enabled = not self.learning_enabled
            self.learning_message = ("Aprender: incorpora experiencia al finalizar cada misión nueva."
                                     if self.learning_active else "Evaluacion: el modelo permanece fijo.")
            self._prepare()
            return
        if key == "history":
            self.set_view("analysis")
            self.history_visible = True
            return
        if key == "history_close":
            self.history_visible = False
            self.history_files = None
            self.history.invalidate_io()
            return
        if key.startswith("history_"):
            directory = self.root / "outputs" / "mission_traces"
            if key.startswith("history_select_"):
                index = int(key.removeprefix("history_select_"))
                if index < len(self.history.records):
                    self.history.invalidate_io()
                    self.history_selected = self.history.records[index]
                    self.history_event_page = self.history_step = 0
            elif key == "history_prev": self.history_page = max(0, self.history_page - 1)
            elif key == "history_next" and (self.history_page+1)*5 < len(self.history.records): self.history_page += 1
            elif key == "history_events_prev": self.history_event_page = max(0, self.history_event_page-1)
            elif key == "history_events_next" and self.history_selected and (self.history_event_page+1)*6 < len(self.history_selected.events): self.history_event_page += 1
            elif key == "history_step_prev": self.history_step = max(0,self.history_step-1)
            elif key == "history_step_next" and self.history_selected: self.history_step = min(len(self.history_selected.episode.states)-1,self.history_step+1)
            elif key == "history_files": self.history.start_io("list",None,directory)
            elif key == "history_files_close": self.history_files = None;self.history.invalidate_io()
            elif key == "history_files_prev": self.history_file_page = max(0,self.history_file_page-1)
            elif key == "history_files_next" and self.history_files and (self.history_file_page+1)*6 < len(self.history_files): self.history_file_page += 1
            elif key.startswith("history_import_") and self.history_files:
                index = int(key.removeprefix("history_import_"))
                if index < len(self.history_files): self.history.start_io("load",self.history_files[index],directory)
            elif key == "history_export" and self.history_selected:
                self.history.start_io("export",self.history_selected,directory)
            elif key == "history_replay" and self.history_selected:
                record = self.history_selected
                self._start_replay(record.episode, record.strategy, record.model, record.seed)
            return
        if key == "compare":
            self._compare()
            return
        if key == "comparison_individual":
            self.comparison_visible = False
            return
        if key in ("comparison_table", "comparison_saved", "comparison_current"):
            self.comparison_show_saved = key == "comparison_saved" or self.comparison is None
            self.history_visible = False
            self.comparison_visible = True
            return
        if key == "comparison_export":
            self._start_comparison_export()
            return
        if key.startswith("replay_") and self.comparison_for_display:
            comparison = self.comparison_for_display
            row = comparison.rows.get(key.removeprefix("replay_"))
            if row and row.episode is not None:
                request = comparison.request
                self._start_replay(row.episode, row.strategy,
                                   request.model if row.strategy == "dqn" else None, request.seed)
            return
        if key.startswith("view_"):
            self.set_view(key.removeprefix("view_"))
            return
        if self.models_open:
            if key == "models_close":
                self.models_open = False
            elif key == "models_prev":
                self.model_page = max(0, self.model_page - 1)
            elif key == "models_next" and (self.model_page + 1) * 4 < len(self.compatible_models()):
                self.model_page += 1
            elif key.startswith("model_"):
                entry = self.models[int(key.split("_")[1])]
                reason = entry.reason(self.scenario)
                if reason:
                    self.error = reason
                    self.error_kind = "model_invalid" if entry.error else "model_incompatible"
                else:
                    self._invalidate_comparison()
                    self.model_path = entry.path
                    self._session_paths.clear()
                    if self.error_kind in ("model_invalid", "model_incompatible", "model_selection"):
                        self.error = self.error_kind = None
                    self.models_open = False
                    if STRATEGIES[self.strategy_index][0] == "dqn":
                        self._prepare()
            return
        if key == "models":
            self.models_open = True
            self.model_page = 0
            return
        if key == "prepare":
            self._prepare()
            return
        if key in ("play", "step"):
            self.view = "execution"
        if self.library_open:
            if key == "library_close":
                self.file_request += 1
                if self.file_future:
                    self.file_future.cancel()
                self.file_future = None
                self.library_open = False
            elif key == "library_prev":
                self.library_page = max(0, self.library_page - 1)
            elif key == "library_next" and (self.library_page + 1) * 6 < len(self.library_files):
                self.library_page += 1
            elif key.startswith("file_"):
                self._start_file("load", self.library_files[int(key.split("_")[1])])
            return
        if key == "load_file":
            self.library_open = True
            if self.playback:
                self.playback.playing = False
            self._start_file("list")
            return
        if key == "save_file":
            self._save_draft()
            return
        if self.editor is not None:
            if key.startswith("person_"):
                self.editor.select(int(key.rsplit("_", 1)[1]))
            elif key in ("editor_clear", "editor_restore"):
                self._invalidate()
                if key == "editor_clear":
                    self.editor.clear()
                else:
                    self.editor.restore()
            elif key == "editor_apply":
                self._apply_draft()
            elif key == "editor_exit":
                self.editor = None
                self._prepare()
            return
        if key == "edit":
            self._enter_editor()
            return
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
        if self.learning_future and self.dropdown:
            self.dropdown = None
            return
        if self.models_open:
            for key, rect in self.controls.items():
                if rect.collidepoint(position):
                    if key not in self.disabled_controls:
                        self.action(key)
                    break
            return
        if self.library_open:
            for key, rect in self.controls.items():
                if rect.collidepoint(position):
                    if key not in self.disabled_controls:
                        self.action(key)
                    break
            return
        if self.dropdown:
            for index, rect in self.dropdown_rows:
                if rect.collidepoint(position):
                    if self.dropdown == "scenario":
                        self.scenario_index = index
                        self._template_index = None
                    else:
                        self.strategy_index = index
                    self._select()
                    return
            self.dropdown = None
            return
        for key, rect in self.controls.items():
            if rect.collidepoint(position):
                if key not in self.disabled_controls:
                    self.action(key)
                return

        if self.editor is not None:
            cell = pixel_to_cell(position, self.grid, (self.scenario.width, self.scenario.height))
            if cell is not None:
                self._invalidate()
                self.editor.place(cell)

    def key(self, key):
        if self.models_open:
            if key == pygame.K_ESCAPE:
                self.models_open = False
            return
        if self.library_open:
            if key == pygame.K_ESCAPE:
                self.action("library_close")
            return
        if self.editor is not None:
            if key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.editor.select(key - pygame.K_1)
            return
        if key == pygame.K_ESCAPE:
            self.dropdown = None
        elif self.dropdown is None:
            action = {pygame.K_SPACE: "play", pygame.K_n: "step", pygame.K_r: "reset",
                      pygame.K_h: "heat", pygame.K_t: "paths", pygame.K_PLUS: "faster",
                      pygame.K_EQUALS: "faster", pygame.K_MINUS: "slower"}.get(key)
            if action:
                self.action(action)

    def _status(self):
        if self.view == "analysis" and self.history_visible:
            return "HISTORIAL / TRAZAS", CYAN
        if self.view == "analysis" and self.comparison_for_display and self.comparison_visible:
            return ("COMPARANDO" if self.comparison_for_display.futures else "COMPARACIÓN LISTA"), CYAN
        if self.view == "analysis" and self.last_result is not None:
            return "RESULTADO CONSERVADO", CYAN
        if self.editor is not None:
            return "EDICIÓN · SIN EJECUTAR", CYAN
        if self.error:
            if self.error_kind in ("model_incompatible", "model_selection"):
                label = "DQN NO DISPONIBLE" if not any(e.reason(self.scenario) is None for e in self.models) else "MODELO INCOMPATIBLE" if self.error_kind == "model_incompatible" else "SELECCIONA MODELO"
                return label, GOLD
            if self.error_kind == "model_invalid":
                return "MODELO INVALIDO", RED
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
        self.disabled_controls.clear()
        self.canvas.fill(BG)
        pygame.draw.rect(self.canvas, CYAN, (28, 29, 34, 34), border_radius=10)
        pygame.draw.rect(self.canvas, BG, (42, 36, 6, 20), border_radius=2)
        pygame.draw.rect(self.canvas, BG, (35, 43, 20, 6), border_radius=2)
        self.text("SAR-Bot", (77, 21), 30, bold=True)
        self.text("Dos robots. Una misión de rescate.", (78, 62), 15, MUTED)
        status, status_color = self._status()
        pygame.draw.circle(self.canvas, status_color, (1037, 47), 4)
        self.text(status, (1050, 37), 13, status_color, bold=True)
        for i,(name,label) in enumerate((("preparation","Preparacion"),("execution","Ejecucion"),("analysis","Analisis"))):
            self.button("view_"+name,label,(340+i*180,30,165,35),primary=self.view==name)
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
        scenario, state = self.display_scenario, self.display_state
        name = SCENARIO_NAMES.get(scenario.name, scenario.name.replace("_", " "))
        self.text(name, (52, 130), 21, bold=True)
        self.text(f"{scenario.width} × {scenario.height}  /  edificio simulado", (582, 138), 13, MUTED)
        for x, label, value, color in (
            (52, "PERSONAS RESCATADAS", f"{len(state.rescued)} / {scenario.victim_count}", GREEN),
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
        foci = {source.focus for source in scenario.heat_sources if source.peak > 35}
        if not foci and max_temp > 35:
            foci = {next((x, y) for y in range(scenario.height) for x in range(scenario.width)
                         if scenario.temperature_at((x, y)) == max_temp)}
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
                    self.text(f"{temperature:.0f}°", (rect.right - 27, rect.bottom - 18), 10, TEXT)
                if position == scenario.base:
                    pygame.draw.rect(self.canvas, GREEN, rect.inflate(-13, -13), 2, border_radius=7)
                    self.text("BASE", (rect.x + 10, rect.y + 6), 9, GREEN, bold=True)
                if position in foci:
                    fx, fy = rect.x + 8, rect.y + 7
                    pygame.draw.polygon(self.canvas, GOLD,
                                        [(fx + 5, fy), (fx + 12, fy + 8), (fx + 10, fy + 15),
                                         (fx + 2, fy + 15), (fx, fy + 8), (fx + 3, fy + 5)])
        if self.playback and self.show_paths and self.view != "analysis":
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
        positions = self.editor.positions if self.editor is not None else scenario.victims
        for victim_id, position in enumerate(positions):
            if position is None:
                continue
            x, y = position
            if victim_id in state.rescued or any(r.carrying == victim_id for r in state.robots):
                continue
            cx, cy = gx + x * cell + cell // 2, gy + y * cell + cell // 2
            head = max(3, min(7, cell // 10))
            pygame.draw.circle(self.canvas, GOLD, (cx, cy - head - 2), head)
            pygame.draw.rect(self.canvas, GOLD, (cx - head - 1, cy + 1, 2 * head + 2, 2 * head + 2), border_radius=4)
            if self.editor is not None:
                badge = pygame.Rect(gx + x * cell + 3, gy + y * cell + 3, 17, 17)
                pygame.draw.rect(self.canvas, BG, badge, border_radius=4)
                self.text(victim_id + 1, badge.center, 13, GOLD, bold=True, center=True)
                if victim_id == self.editor.selected:
                    pygame.draw.rect(self.canvas, CYAN,
                                     (gx + x * cell + 1, gy + y * cell + 1, cell - 2, cell - 2), 2, border_radius=5)
        together = state.robots[0].position == state.robots[1].position
        for i, robot in enumerate(state.robots):
            x, y = robot.position
            radius = min(16, max(7, cell // 4 - 1)) if together else min(21, max(9, cell // 3))
            cx = gx + x * cell + cell // 2 + ((i * 2 - 1) * (radius - 1) if together else 0)
            cy = gy + y * cell + cell // 2
            pygame.draw.circle(self.canvas, BG, (cx, cy), radius + 3)
            pygame.draw.circle(self.canvas, ROBOT_COLORS[i], (cx, cy), radius)
            self.text(i + 1, (cx, cy - 1), min(18, max(11, cell // 3)), BG, bold=True, center=True)
            if robot.carrying is not None:
                badge = min(7, max(4, cell // 10))
                pygame.draw.circle(self.canvas, GOLD, (cx + radius - 1, cy - radius + 1), badge)
                self.text("+", (cx + radius - 1, cy - radius), min(13, 2 * badge), BG, bold=True, center=True)
        self._mission_details()
        self.text("1 / 2  Robots     •     Persona     •     Base segura     •     # Obstáculo",
                  (60, 686), 12, MUTED)
        hovered_cell = pixel_to_cell(self.mouse, self.grid, (scenario.width, scenario.height))
        if self.dropdown is None and hovered_cell is not None:
            x, y = hovered_cell
            t = scenario.temperature_at((x, y))
            rect = pygame.Rect(532, 609, 294, 68)
            pygame.draw.rect(self.canvas, INSET, rect, border_radius=7)
            self.text(f"Celda {chr(65+x)}{y+1}  ·  {t:g} °C", (546, 619), 14, bold=True)
            label = ("Obstáculo · no transitable" if (x, y) in scenario.walls else
                     f"{damage_rate(t)} de daño por paso de exposición")
            self.text(label, (546, 647), 12, MUTED)

    def _mission_details(self):
        state = self.display_state
        self.text("SOBREVIVIENTES", (532, 248), 11, MUTED, bold=True)
        count = self.display_scenario.victim_count
        for victim_id in range(min(count, 3)):
            y = 274 + victim_id * (78 if count <= 2 else 54)
            delivered = victim_id in state.rescued
            carrier = next((i + 1 for i, r in enumerate(state.robots) if r.carrying == victim_id), None)
            status = person_status(state, victim_id)
            if self.editor is not None:
                status = "Sin ubicar" if self.editor.positions[victim_id] is None else "Ubicada · borrador"
            color = GREEN if delivered else CYAN if carrier else GOLD
            self.card((532, y, 294, 64 if count <= 2 else 48), INSET, 9)
            pygame.draw.circle(self.canvas, color, (550, y + 21), 4)
            self.text(f"Persona {victim_id + 1}", (563, y + (9 if count <= 2 else 4)), 15, bold=True)
            self.text(status, (550, y + (35 if count <= 2 else 25)), 13, color)
        if count > 3:
            self.text(f"+ {count - 3} personas en el mapa", (532, 425), 11, MUTED)
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
        for i, robot in enumerate(self.display_state.robots):
            x, y = 28 + i * 420, 728
            color = ROBOT_COLORS[i]
            self.card((x, y, 404, 102))
            pygame.draw.circle(self.canvas, color, (x + 22, y + 24), 5)
            self.text(f"Robot {i + 1}", (x + 36, y + 11), 18, bold=True)
            status = ("Fuera de servicio" if robot.integrity == 0 else
                      "En traslado" if robot.carrying is not None else
                      "En base" if robot.position == self.display_scenario.base else "Buscando")
            if self.view!="analysis" and self.playback and self.playback.episode.decisions and robot.integrity>0:
                decisions=[d for d in self.playback.episode.decisions if d["step"]<=self.display_state.steps]
                target=decisions[-1]["assignments"].get(i) if decisions else None
                pending=set(range(self.display_scenario.victim_count))-set(self.display_state.rescued)-{
                    r.carrying for r in self.display_state.robots if r.carrying is not None}
                if robot.carrying is not None:status="Volviendo a base"
                elif target is not None and target in pending:status=f"Hacia persona {target+1}"
                elif self.display_state.outcome=="running":
                    status="Esperando en base" if robot.position==self.display_scenario.base else "Volviendo a base"
            self.text(status, (x + 133, y + 16), 12, MUTED)
            self.text(f"{robot.integrity}%", (x + 334, y + 10), 21, color, bold=True)
            pygame.draw.rect(self.canvas, INSET, (x + 20, y + 47, 364, 6), border_radius=3)
            if robot.integrity:
                pygame.draw.rect(self.canvas, color if robot.integrity > 30 else RED,
                                 (x + 20, y + 47, round(364 * robot.integrity / 100), 6), border_radius=3)
            temperature = self.display_scenario.temperature_at(robot.position)
            cargo = f"Persona {robot.carrying + 1}" if robot.carrying is not None else "Sin carga"
            self.text(f"{temperature:g} °C     ·     Daño {robot.damage}     ·     {cargo}",
                      (x + 20, y + 69), 13, MUTED)

    def _controls(self):
        if self.library_open:
            draw_library(self)
        elif self.models_open:
            draw_models(self)
        elif self.editor is not None:
            draw_editor_controls(self)
        elif self.view == "analysis" and self.history_visible:
            from .history_view import draw_history
            draw_history(self)
        elif self.view == "analysis" and self.comparison_for_display and self.comparison_visible:
            from .comparison_view import draw_comparison
            draw_comparison(self)
        elif self.view == "preparation":
            draw_preparation(self)
        elif self.view == "execution":
            draw_execution(self)
        else:
            draw_analysis(self)

    def _dropdown(self):
        self.dropdown_rows = []
        is_scenario = self.dropdown == "scenario"
        entry=self.selected_model()
        choices = ([(i,scenario_label(s)) for i,(_,s) in enumerate(self.options)
                    if not self.neural_focus or not entry or
                    (s.width,s.height,s.victim_count)==entry.dimensions] if is_scenario
                   else [(i,s[1]) for i,s in enumerate(STRATEGIES)])
        selected = self.scenario_index if is_scenario else self.strategy_index
        y = 240 if is_scenario else 337
        height = 50 if is_scenario else 92
        self.card((894, y, 340, height * len(choices) + 12), (24, 39, 57), 10)
        for local,(index,label) in enumerate(choices):
            rect = pygame.Rect(900, y + 6 + height * local, 328, height)
            self.dropdown_rows.append((index, rect))
            if index == selected or rect.collidepoint(self.mouse):
                pygame.draw.rect(self.canvas, (38, 61, 79), rect, border_radius=6)
            self.text(label[:39], (rect.x + 10, rect.y + 6), 14, CYAN if index == selected else TEXT)
            if is_scenario:
                scenario = self.options[index][1]
                self.text(f"{scenario.width} × {scenario.height} · {scenario.victim_count} personas",
                          (rect.x + 10, rect.y + 27), 12, MUTED)
            else:
                self.wrap(STRATEGIES[index][2], rect.x + 10, rect.y + 30, 305, 12)


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
            viewport = Viewport((width, height), SIZE)
            offset = viewport.offset
            logical = viewport.logical
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
            scaled = pygame.transform.smoothscale(canvas, viewport.size)
            window.blit(scaled, offset)
            pygame.display.flip()
    finally:
        app.close()
        pygame.quit()
