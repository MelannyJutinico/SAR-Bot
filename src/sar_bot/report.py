"""Tablas y figuras del informe generadas desde archivos conservados (SARB-022).

Ninguna cifra se transcribe a mano. Las tablas y figuras salen de:

- un CSV de ``scripts/evaluate_experiment.py``, comprobado contra sus metadatos
  y, por defecto, reproduciendo cada traza en un motor nuevo;
- los registros ``evaluations.jsonl`` y ``metadata.json`` de cada entrenamiento.

Las figuras son SVG escritos sin dependencias externas. Su contenido depende
solo de las entradas: regenerarlas produce los mismos bytes, y ``check_report``
lo usa para detectar figuras o tablas editadas a mano.

Reglas de lectura que el código aplica:

- toda proporción va con su denominador (``17/20``); el símbolo ``%`` solo
  aparece en las marcas del eje;
- pasos y daño se promedian solo entre misiones exitosas;
- las comparaciones entre estrategias usan casos emparejados;
- no se dibujan intervalos de confianza: los episodios sobre los mismos casos
  no son muestras independientes. Se informan conteos y variación entre semillas.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

from sar_bot.core import Scenario
from sar_bot.experiment import COLUMNS, read_results, verify_results
from sar_bot.partitions import file_sha256

REPORT_SCHEMA = 1
SOURCES_FILE = "fuentes.json"
TABLES_FILE = "tablas.md"
OUTCOMES_FIGURE = "exito_y_rescates.svg"
SUCCESS_METRICS_FIGURE = "pasos_y_danio_exitos.svg"
TRADEOFF_FIGURE = "duracion_vs_danio.svg"
TRAINING_FIGURE = "curvas_entrenamiento.svg"

# Paleta categórica validada: las tres primeras posiciones superan las pruebas de
# daltonismo en todos los pares. El color sigue a la estrategia en todas las
# figuras. La aleatoria es la referencia sin información y va en gris neutro.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
COLORS = {"dqn": "#2a78d6", "shortest": "#eb6834", "thermal": "#1baf7a", "random": "#898781"}
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"

STRATEGY_ORDER = ("dqn", "shortest", "thermal", "random")
STRATEGY_NAMES = {"dqn": "DQN", "shortest": "Ruta corta", "thermal": "Ruta térmica",
                  "random": "Aleatoria"}
PARTITION_NAMES = {"training": "Entrenamiento", "validation": "Validación",
                   "test": "Prueba final", "development": "Desarrollo"}
BUILDING_NAMES = {"hub": "Centro de coordinación", "detour": "Desvío térmico"}
DIFFICULTY_NAMES = {"easy": "Fácil", "intermediate": "Intermedio", "demanding": "Exigente"}
REFERENCE_PAIR = ("shortest", "thermal")
MAX_SCENARIO_GROUPS = 6


# --------------------------------------------------------------------------- datos


@dataclass(frozen=True)
class Episode:
    episode_id: str
    partition: str
    manifest_id: str
    scenario: str
    building: str
    difficulty: str
    configuration_id: str
    width: int
    height: int
    strategy: str
    model_label: str
    model_sha256: str
    training_seed: int | None
    random_seed: int | None
    victims: int
    rescued: int
    success: bool
    outcome: str
    steps: int
    damage: int

    @property
    def series_key(self) -> tuple[str, str]:
        return (self.strategy, self.model_label)


def _optional_int(text: str) -> int | None:
    return int(text) if text not in ("", None) else None


def parse_rows(rows) -> list[Episode]:
    """Convierte las filas de texto del CSV en episodios tipados."""
    return [Episode(
        episode_id=row["episode_id"], partition=row["partition"], manifest_id=row["manifest_id"],
        scenario=Path(row["scenario_path"]).stem, building=row["building"],
        difficulty=row["difficulty"], configuration_id=row["configuration_id"],
        width=int(row["width"]), height=int(row["height"]), strategy=row["strategy"],
        model_label=row["model_label"], model_sha256=row["model_sha256"],
        training_seed=_optional_int(row["training_seed"]),
        random_seed=_optional_int(row["random_seed"]), victims=int(row["victims_total"]),
        rescued=int(row["rescued"]), success=row["success"] == "True", outcome=row["outcome"],
        steps=int(row["steps"]), damage=int(row["damage_total"]),
    ) for row in rows]


def load_results(csv_path: str | Path, root: str | Path, *, replay: bool = True):
    """Episodios y metadatos de un CSV íntegro; con ``replay`` reproduce sus trazas."""
    csv_path = Path(csv_path)
    metadata = json.loads(csv_path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    if replay:
        problems = verify_results(csv_path, root)
    else:
        problems = []
        if file_sha256(csv_path) != metadata.get("csv_sha256"):
            problems.append("El CSV cambió después de escribirse")
        rows = read_results(csv_path)
        if rows and tuple(rows[0].keys()) != COLUMNS:
            problems.append("Las columnas no coinciden con el diccionario")
    if problems:
        raise ValueError(f"{csv_path.name} no está íntegro: " + "; ".join(problems[:3]))
    episodes = parse_rows(read_results(csv_path))
    if not episodes:
        raise ValueError(f"{csv_path.name} no tiene episodios")
    return episodes, metadata


@dataclass(frozen=True)
class Series:
    strategy: str
    model_label: str = ""
    training_seed: int | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.strategy, self.model_label)

    @property
    def name(self) -> str:
        if self.strategy == "dqn":
            seed = "" if self.training_seed is None else f" · semilla {self.training_seed}"
            return f"DQN {self.model_label}{seed}"
        return STRATEGY_NAMES.get(self.strategy, self.strategy)

    @property
    def color(self) -> str:
        return COLORS.get(self.strategy, MUTED)

    @property
    def slug(self) -> str:
        return f"{self.strategy}:{self.model_label}" if self.model_label else self.strategy


def series_of(episodes) -> list[Series]:
    """Series en orden fijo: modelos DQN por semilla, ruta corta, térmica y aleatoria."""
    found = {}
    for e in episodes:
        found.setdefault(e.series_key, Series(e.strategy, e.model_label, e.training_seed))
    order = {s: i for i, s in enumerate(STRATEGY_ORDER)}
    return sorted(found.values(), key=lambda s: (order.get(s.strategy, len(order)),
                                                 s.training_seed is None, s.training_seed or 0,
                                                 s.model_label))


def _ordered_keys(episodes, attribute: str) -> list[str]:
    """Edificios y familias en su orden conocido; el resto en orden de aparición."""
    known = {"building": list(BUILDING_NAMES), "difficulty": list(DIFFICULTY_NAMES)}.get(attribute, [])
    keys = list(dict.fromkeys(getattr(e, attribute) for e in episodes))
    return sorted(keys, key=lambda k: (known.index(k) if k in known else len(known),
                                       keys.index(k)))


def groups_of(episodes) -> list[tuple[str, str, list[Episode]]]:
    """Todos los casos y, si hay varios, cada edificio (o escenario en desarrollo)."""
    groups = [("all", "Todos los casos", list(episodes))]
    if any(e.building for e in episodes):
        attribute, names = "building", BUILDING_NAMES
    else:
        attribute, names = "scenario", {}
    keys = _ordered_keys(episodes, attribute)
    if len(keys) < 2 or (attribute == "scenario" and len(keys) > MAX_SCENARIO_GROUPS):
        return groups
    for key in keys:
        name = f"{names[key]} ({key})" if key in names else key
        groups.append((key, name, [e for e in episodes if getattr(e, attribute) == key]))
    return groups


def _mean(values) -> float | None:
    return sum(values) / len(values) if values else None


@dataclass(frozen=True)
class Outcome:
    episodes: int
    configurations: int
    successes: int
    rescued: int
    victims: int
    destroyed: int
    time_limit: int
    steps: tuple[int, ...]
    damage: tuple[int, ...]

    @property
    def mean_steps(self) -> float | None:
        return _mean(self.steps)

    @property
    def mean_damage(self) -> float | None:
        return _mean(self.damage)


def outcome(episodes) -> Outcome:
    """Conteos con denominador; pasos y daño solo de las misiones exitosas."""
    successes = [e for e in episodes if e.success]
    return Outcome(
        episodes=len(episodes), configurations=len({e.configuration_id for e in episodes}),
        successes=len(successes), rescued=sum(e.rescued for e in episodes),
        victims=sum(e.victims for e in episodes),
        destroyed=sum(e.outcome == "destroyed" for e in episodes),
        time_limit=sum(e.outcome == "time_limit" for e in episodes),
        steps=tuple(e.steps for e in successes), damage=tuple(e.damage for e in successes))


def single_episode_series(episodes) -> list[Series]:
    """Series con un solo episodio por caso: se pueden emparejar caso a caso."""
    result = []
    for s in series_of(episodes):
        counts = Counter(e.configuration_id for e in episodes if e.series_key == s.key)
        if counts and max(counts.values()) == 1:
            result.append(s)
    return result


@dataclass(frozen=True)
class Pairing:
    a: Series
    b: Series
    shared: int
    both: tuple[tuple[Episode, Episode], ...]
    only_a: int
    only_b: int
    neither: int

    def mean(self, side: str, metric: str) -> float | None:
        index = 0 if side == "a" else 1
        return _mean([getattr(pair[index], metric) for pair in self.both])

    def difference(self, metric: str) -> float | None:
        a, b = self.mean("a", metric), self.mean("b", metric)
        return None if a is None else b - a

    def b_lower(self, metric: str) -> tuple[int, int, int]:
        """Casos emparejados en que B queda por debajo, igual o por encima de A."""
        values = [(getattr(pb, metric), getattr(pa, metric)) for pa, pb in self.both]
        return (sum(b < a for b, a in values), sum(b == a for b, a in values),
                sum(b > a for b, a in values))


def pairing(episodes, a: Series, b: Series) -> Pairing:
    """Compara A y B solo sobre los casos que ambas evaluaron."""
    first = {e.configuration_id: e for e in episodes if e.series_key == a.key}
    second = {e.configuration_id: e for e in episodes if e.series_key == b.key}
    shared = [c for c in first if c in second]
    both = tuple((first[c], second[c]) for c in shared if first[c].success and second[c].success)
    return Pairing(
        a=a, b=b, shared=len(shared), both=both,
        only_a=sum(first[c].success and not second[c].success for c in shared),
        only_b=sum(second[c].success and not first[c].success for c in shared),
        neither=sum(not first[c].success and not second[c].success for c in shared))


def reference_pair(episodes) -> tuple[Series, Series] | None:
    candidates = {s.strategy: s for s in single_episode_series(episodes)
                  if s.strategy in REFERENCE_PAIR}
    if all(name in candidates for name in REFERENCE_PAIR):
        return candidates[REFERENCE_PAIR[0]], candidates[REFERENCE_PAIR[1]]
    return None


# ------------------------------------------------------------- entrenamiento


@dataclass(frozen=True)
class TrainingPoint:
    steps: int
    stage: str
    rescued: int
    victims: int
    successes: int
    scenarios: int


@dataclass(frozen=True)
class TrainingLog:
    label: str
    path: str
    seed: int | None
    points: tuple[TrainingPoint, ...]
    stages: tuple[tuple[str, int, int], ...]
    evaluation_scenarios: tuple[str, ...]
    overlap_with_training: int
    selected: int
    files: dict

    @property
    def selected_point(self) -> TrainingPoint:
        return self.points[self.selected]


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def load_training_log(directory: str | Path, root: str | Path) -> TrainingLog:
    """Curva de evaluación periódica de un entrenamiento y el checkpoint que eligió."""
    root = Path(root)
    directory = Path(directory)
    folder = directory if directory.is_absolute() else root / directory
    evaluations = folder / "evaluations.jsonl"
    metadata_path = folder / "metadata.json"
    records = [json.loads(line) for line in evaluations.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    if not records:
        raise ValueError(f"{evaluations} no tiene evaluaciones")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    config = metadata.get("config", {})
    stages, start = [], 0
    for stage in config.get("stages", []):
        stages.append((stage["name"], start, start + int(stage["steps"])))
        start += int(stage["steps"])
    trained = {path for stage in config.get("stages", []) for path in stage.get("scenarios", [])}
    evaluation = tuple(config.get("evaluation_scenarios", ()))
    victims_by_name = {}
    if any("victims_total" not in r for record in records for r in record["results"]):
        # Registros antiguos sin victims_total: se toma del escenario evaluado.
        for path in evaluation:
            scenario = Scenario.load(root / path)
            victims_by_name[scenario.name] = scenario.victim_count
    points = []
    for record in records:
        results = record["results"]
        points.append(TrainingPoint(
            steps=int(record["steps"]), stage=record["stage"],
            rescued=sum(int(r["rescued"]) for r in results),
            victims=sum(int(r.get("victims_total", victims_by_name.get(r["scenario"], 0)))
                        for r in results),
            successes=sum(bool(r["success"]) for r in results), scenarios=len(results)))
    # El entrenamiento guarda el primer registro con la mejor puntuación.
    selected = max(range(len(records)), key=lambda i: (tuple(records[i]["score"]), -i))
    files = {"evaluations.jsonl": file_sha256(evaluations), "metadata.json": file_sha256(metadata_path)}
    model = folder / "model.zip"
    if model.is_file():
        files["model.zip"] = sha256(model.read_bytes()).hexdigest()
    seed = config.get("seed", metadata.get("seed"))
    return TrainingLog(
        label=folder.name, path=_relative(folder, root),
        seed=seed if type(seed) is int else None, points=tuple(points), stages=tuple(stages),
        evaluation_scenarios=evaluation,
        overlap_with_training=sum(path in trained for path in evaluation),
        selected=selected, files=files)


# ------------------------------------------------------------------- formato


def _dec(value, digits: int = 1) -> str:
    """Número con coma decimal; raya si no hay datos."""
    if value is None:
        return "—"
    return f"{value:.{digits}f}".replace(".", ",")


def _signed(value) -> str:
    if value is None:
        return "—"
    text = _dec(value)
    return text if text.startswith("-") else "+" + text


def _short(value: float) -> str:
    text = _dec(value)
    return text[:-2] if text.endswith(",0") else text


def _thousands(value: int) -> str:
    return _short(value / 1000) + " mil"


def _nice_ticks(maximum: float, target: int = 5, *, integer: bool = False) -> list[float]:
    if maximum <= 0:
        return [0, 1]
    raw = maximum / target
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    if integer:
        step = max(1, math.ceil(step))
    count = math.ceil(maximum / step - 1e-9)
    return [round(i * step, 10) for i in range(count + 1)]


def _tick_label(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else _dec(value)


def _text_width(text: str, size: float) -> float:
    return len(text) * size * 0.56


def _wrap(text: str, width: float, size: float) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and _text_width(candidate, size) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    return lines + [current] if current else lines


def _context(episodes) -> str:
    first = episodes[0]
    parts = [PARTITION_NAMES.get(first.partition, first.partition)]
    if first.manifest_id:
        parts.append(f"manifiesto {first.manifest_id}")
    parts.append(f"perfil {first.width} × {first.height} con {first.victims} personas")
    parts.append(f"{len({e.configuration_id for e in episodes})} casos distintos")
    parts.append(f"{len(episodes)} episodios")
    return " · ".join(parts)


def _per_case(episodes, s: Series) -> int:
    counts = Counter(e.configuration_id for e in episodes if e.series_key == s.key)
    return max(counts.values()) if counts else 0


def _row_label(episodes, s: Series) -> str:
    per_case = _per_case(episodes, s)
    return f"{s.name} · {per_case} semillas" if s.strategy == "random" and per_case > 1 else s.name


# ----------------------------------------------------------------------- SVG


def _number(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


class _Canvas:
    """SVG mínimo y determinista: los elementos se escriben en orden de dibujo."""

    def __init__(self, width: float):
        self.width = width
        self.items: list[str] = []

    @staticmethod
    def _attribute(value) -> str:
        if isinstance(value, (int, float)):
            return _number(value)
        return escape(str(value), {'"': "&quot;"})

    def element(self, tag: str, attributes: dict, *, text: str | None = None,
                title: str | None = None) -> None:
        attrs = "".join(f' {key}="{self._attribute(value)}"'
                        for key, value in attributes.items() if value is not None)
        inner = (f"<title>{escape(title)}</title>" if title else "") + (escape(text) if text else "")
        self.items.append(f"<{tag}{attrs}>{inner}</{tag}>" if inner else f"<{tag}{attrs}/>")

    def text(self, x, y, value: str, *, size=12, fill=INK, anchor=None, weight=None,
             cls=None, data: dict | None = None) -> None:
        attributes = {"x": x, "y": y, "font-size": size, "fill": fill, "text-anchor": anchor,
                      "font-weight": weight, "class": cls}
        attributes.update(data or {})
        self.element("text", attributes, text=value)

    def line(self, x1, y1, x2, y2, *, stroke=GRID, width=1, cls=None, data=None, title=None,
             opacity=None) -> None:
        attributes = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "stroke": stroke,
                      "stroke-width": width, "stroke-linecap": "round", "class": cls,
                      "stroke-opacity": opacity}
        attributes.update(data or {})
        self.element("line", attributes, title=title)

    def dot(self, cx, cy, color, *, r=4, cls=None, data=None, title=None) -> None:
        attributes = {"cx": cx, "cy": cy, "r": r, "fill": color, "stroke": SURFACE,
                      "stroke-width": 2, "class": cls}
        attributes.update(data or {})
        self.element("circle", attributes, title=title)

    def header(self, title: str, lines, *, x=24, y=30) -> float:
        self.text(x, y, title, size=16, weight=600)
        y += 22
        for line in lines:
            for part in _wrap(line, self.width - 2 * x, 12):
                self.text(x, y, part, size=12, fill=INK_2)
                y += 17
        return y + 6

    def render(self, height: float, title: str, description: str) -> str:
        width, height = _number(self.width), _number(math.ceil(height))
        head = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="titulo descripcion" '
            f'font-family="{FONT}">',
            f'<title id="titulo">{escape(title)}</title>',
            f'<desc id="descripcion">{escape(description)}</desc>',
            f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
        ]
        return "\n".join(head + self.items + ["</svg>"]) + "\n"


def _bar_path(x0: float, cy: float, length: float, thickness: float = 12) -> str | None:
    """Barra horizontal: recta en la base y extremo de datos redondeado (4 px)."""
    if length <= 0:
        return None
    r = min(4.0, length, thickness / 2)
    top = cy - thickness / 2
    n = _number
    return (f"M{n(x0)},{n(top)}h{n(length - r)}a{n(r)},{n(r)} 0 0 1 {n(r)},{n(r)}"
            f"v{n(thickness - 2 * r)}a{n(r)},{n(r)} 0 0 1 {n(-r)},{n(r)}h{n(-(length - r))}z")


def _value_axis(canvas: _Canvas, x0, width, ticks, top, bottom, title, fmt) -> None:
    span = ticks[-1] or 1
    for tick in ticks:
        x = x0 + width * tick / span
        canvas.line(x, top, x, bottom, stroke=AXIS if tick == 0 else GRID)
        canvas.text(x, bottom + 15, fmt(tick), size=11, fill=MUTED, anchor="middle", cls="tick")
    canvas.text(x0 + width / 2, bottom + 32, title, size=11, fill=INK_2, anchor="middle",
                cls="axis-title")


def _swatch(canvas: _Canvas, x, cy, color) -> None:
    canvas.element("rect", {"x": x, "y": cy - 5, "width": 10, "height": 10, "rx": 2,
                            "fill": color})


def _row_layout(groups, series, top, row_height):
    """Filas de grupo y de serie con su posición vertical."""
    rows, y = [], top
    for index, (key, name, group) in enumerate(groups):
        if index:
            y += 8
        rows.append(("group", key, name, None, None, y + row_height / 2))
        y += row_height
        for s in series:
            members = [e for e in group if e.series_key == s.key]
            if members:
                rows.append(("series", key, name, s, members, y + row_height / 2))
                y += row_height
    return rows, y


def figure_outcomes(episodes) -> str:
    """Éxito y personas entregadas por estrategia, con denominadores en cada barra."""
    series, groups = series_of(episodes), groups_of(episodes)
    cases = len({e.configuration_id for e in episodes})
    canvas = _Canvas(920)
    y = canvas.header("Éxito y personas entregadas por estrategia", [
        _context(episodes),
        "Cada barra lleva su conteo: éxitos/episodios y personas entregadas/personas totales. "
        f"Todas las estrategias resuelven los mismos {cases} casos (datos emparejados); en una "
        f"estrategia determinista cada caso vale {_short(100 / cases)} puntos de su tasa.",
    ])
    panel_width = 240
    panels = ((300, "success", "Misiones exitosas", "% de episodios"),
              (620, "rescued", "Personas entregadas", "% de personas"))
    for x0, _, name, _ in panels:
        canvas.text(x0, y + 10, name, size=12, weight=600)
    rows, bottom = _row_layout(groups, series, y + 20, 24)
    top = y + 20
    for x0, _, _, title in panels:
        _value_axis(canvas, x0, panel_width, [0, 0.25, 0.5, 0.75, 1], top, bottom + 4, title,
                    lambda t: f"{round(t * 100)} %")
    for kind, key, name, s, members, cy in rows:
        if kind == "group":
            canvas.text(24, cy + 4, name, size=12, weight=600)
            continue
        canvas.text(52, cy + 4, _row_label(members, s), size=12)
        _swatch(canvas, 36, cy, s.color)
        result = outcome(members)
        for x0, metric, _, _ in panels:
            k, n = ((result.successes, result.episodes) if metric == "success"
                    else (result.rescued, result.victims))
            length = panel_width * k / n if n else 0
            data = {"data-group": key, "data-series": s.slug, "data-metric": metric,
                    "data-k": k, "data-n": n}
            path = _bar_path(x0, cy, length)
            if path:
                canvas.element("path", {"d": path, "fill": s.color, "class": "bar", **data},
                               title=f"{name} · {s.name}: {k}/{n}")
            canvas.text(x0 + length + 6, cy + 4, f"{k}/{n}", size=11, fill=INK_2,
                        cls="bar-label", data=data)
    description = "; ".join(
        f"{name}, {s.name}: {outcome(m).successes}/{outcome(m).episodes} éxitos, "
        f"{outcome(m).rescued}/{outcome(m).victims} personas"
        for kind, _, name, s, m, _ in rows if kind == "series")
    return canvas.render(bottom + 56, "Éxito y personas entregadas por estrategia", description)


def _swarm_offsets(xs, spacing=6.0, step=6.0, limit=12.0):
    """Desplazamientos verticales para que los puntos con el mismo valor no se oculten."""
    used = defaultdict(int)
    offsets = []
    pattern = [0.0]
    k = 1
    while k * step <= limit:
        pattern += [-k * step, k * step]
        k += 1
    for x in xs:
        bucket = round(x / spacing)
        offsets.append(pattern[used[bucket] % len(pattern)])
        used[bucket] += 1
    return offsets


def figure_success_metrics(episodes) -> str:
    """Pasos y daño de cada misión exitosa, con la media y el tamaño de muestra."""
    series, groups = series_of(episodes), groups_of(episodes)
    canvas = _Canvas(920)
    y = canvas.header("Pasos y daño entre misiones exitosas", [
        _context(episodes),
        "Cada punto es una misión exitosa y la línea negra su media. La cifra junto a cada "
        "estrategia es éxitos/episodios: los fracasos no aportan puntos ni entran en la media, "
        "así que un fracaso temprano con poco daño no mejora el resultado.",
    ])
    successes = [e for e in episodes if e.success]
    steps_ticks = _nice_ticks(max((e.steps for e in successes), default=0))
    damage_ticks = _nice_ticks(max((e.damage for e in successes), default=0))
    panel_width = 210
    panels = ((340, "steps", "Pasos hasta terminar", "Pasos simulados", steps_ticks, "pasos"),
              (650, "damage", "Daño térmico total", "Puntos de daño (ambos robots)",
               damage_ticks, "de daño"))
    for x0, _, name, _, _, _ in panels:
        canvas.text(x0, y + 10, name, size=12, weight=600)
        canvas.text(x0 + panel_width + 10, y + 10, "media", size=11, fill=MUTED)
    canvas.text(318, y + 10, "éxitos", size=11, fill=MUTED, anchor="end")
    top = y + 20
    rows, bottom = _row_layout(groups, series, top, 32)
    for x0, _, _, title, ticks, _ in panels:
        _value_axis(canvas, x0, panel_width, ticks, top, bottom + 4, title, _tick_label)
    for kind, key, name, s, members, cy in rows:
        if kind == "group":
            canvas.text(24, cy + 4, name, size=12, weight=600)
            continue
        result = outcome(members)
        _swatch(canvas, 36, cy, s.color)
        canvas.text(52, cy + 4, _row_label(members, s), size=12)
        canvas.text(318, cy + 4, f"{result.successes}/{result.episodes}", size=11, fill=INK_2,
                    anchor="end", cls="count",
                    data={"data-group": key, "data-series": s.slug,
                          "data-k": result.successes, "data-n": result.episodes})
        for x0, metric, _, _, ticks, unit in panels:
            winners = sorted((e for e in members if e.success),
                             key=lambda e: (getattr(e, metric), e.episode_id))
            if not winners:
                canvas.text(x0 + 6, cy + 4, "sin éxitos", size=11, fill=MUTED)
                continue
            xs = [x0 + panel_width * getattr(e, metric) / ticks[-1] for e in winners]
            for e, x, offset in zip(winners, xs, _swarm_offsets(xs)):
                canvas.dot(x, cy + offset, s.color, cls="dot",
                           data={"data-group": key, "data-series": s.slug,
                                 "data-metric": metric, "data-value": getattr(e, metric)},
                           title=f"{e.scenario} · {s.name}: {getattr(e, metric)} {unit}")
            mean = _mean([getattr(e, metric) for e in winners])
            x = x0 + panel_width * mean / ticks[-1]
            canvas.line(x, cy - 13, x, cy + 13, stroke=INK, width=2, cls="mean",
                        data={"data-group": key, "data-series": s.slug, "data-metric": metric,
                              "data-value": round(mean, 4), "data-n": len(winners)},
                        title=f"{name} · {s.name}: media {_dec(mean)} {unit} "
                              f"en {len(winners)} éxitos")
            canvas.text(x0 + panel_width + 10, cy + 4, _dec(mean), size=11, fill=INK_2)
    return canvas.render(bottom + 56, "Pasos y daño entre misiones exitosas",
                         "Distribución de pasos y daño de las misiones exitosas por estrategia, "
                         "con medias y tamaños de muestra.")


def _legend(canvas: _Canvas, items, x0, y, right) -> float:
    """Leyenda en una fila (o varias si no cabe). Devuelve la siguiente altura libre."""
    x = x0
    for kind, color, label in items:
        width = 18 + _text_width(label, 11) + 18
        if x > x0 and x + width > right:
            x, y = x0, y + 18
        if kind == "dot":
            canvas.dot(x + 5, y - 4, color)
        else:
            canvas.line(x, y - 4, x + 12, y - 4, stroke=color, width=1.5, opacity=0.8)
        canvas.text(x + 18, y, label, size=11, fill=INK_2)
        x += width
    return y + 14


def figure_tradeoff(episodes) -> str:
    """Duración frente a daño de las misiones exitosas; une cada caso entre referencias."""
    series, groups = series_of(episodes), groups_of(episodes)
    panels = groups[1:] if len(groups) > 1 else groups
    columns = 1 if len(panels) == 1 else 2
    panel_width = 560 if columns == 1 else 414
    width = 48 + columns * panel_width + (columns - 1) * 24
    canvas = _Canvas(width)
    pair = reference_pair(episodes)
    pair_text = (f"La línea gris une el mismo caso resuelto por {pair[0].name.lower()} y por "
                 f"{pair[1].name.lower()}: muestra cuántos pasos cuesta reducir el daño. En los "
                 "casos idénticos (mismos pasos y daño) los dos puntos se superponen."
                 if pair else "No hay dos referencias deterministas para emparejar casos.")
    y = canvas.header("Duración frente a daño en misiones exitosas",
                      [_context(episodes), pair_text])
    successes = [e for e in episodes if e.success]
    present = {s.strategy for s in series if any(e.series_key == s.key for e in successes)}
    items = []
    for strategy in STRATEGY_ORDER:
        if strategy in present:
            models = [s for s in series if s.strategy == strategy]
            label = STRATEGY_NAMES[strategy]
            if strategy == "dqn":
                label += f" ({len(models)} modelo{'s' if len(models) > 1 else ''})"
            items.append(("dot", COLORS[strategy], label))
    if pair:
        items.append(("line", MUTED, f"Mismo caso: {pair[0].name.lower()} → "
                                      f"{pair[1].name.lower()}"))
    y = _legend(canvas, items, 24, y + 4, width - 24) + 6
    x_ticks = _nice_ticks(max((e.steps for e in successes), default=0))
    y_ticks = _nice_ticks(max((e.damage for e in successes), default=0))
    plot_height = 220 if columns == 2 else 260
    panel_height = 68 + plot_height + 44
    draw_order = {s: i for i, s in enumerate(("random", "dqn", "shortest", "thermal"))}
    for index, (key, name, group) in enumerate(panels):
        column, row = index % columns, index // columns
        px = 24 + column * (panel_width + 24)
        py = y + row * (panel_height + 16)
        left, right = px + 40, px + panel_width - 8
        top, bottom = py + 68, py + 68 + plot_height
        canvas.text(px, py + 12, name, size=12, weight=600)
        if pair:
            stats = pairing(group, *pair)
            same = sum(a.steps == b.steps and a.damage == b.damage for a, b in stats.both)
            canvas.text(px, py + 28, f"{len(stats.both)} de {stats.shared} casos con éxito en "
                                     f"ambas · {same} idénticos", size=11, fill=INK_2)
            if stats.both:
                canvas.text(px, py + 43,
                            f"Medias: {_dec(stats.mean('a', 'steps'))} → "
                            f"{_dec(stats.mean('b', 'steps'))} pasos · "
                            f"{_dec(stats.mean('a', 'damage'))} → "
                            f"{_dec(stats.mean('b', 'damage'))} de daño", size=11, fill=INK_2)
        else:
            count = sum(e.success for e in group)
            canvas.text(px, py + 28, f"{count}/{len(group)} episodios con éxito", size=11,
                        fill=INK_2)

        def sx(value):
            return left + (right - left) * value / x_ticks[-1]

        def sy(value):
            return bottom - (bottom - top) * value / y_ticks[-1]

        for tick in x_ticks:
            canvas.line(sx(tick), top, sx(tick), bottom, stroke=AXIS if tick == 0 else GRID)
            canvas.text(sx(tick), bottom + 15, _tick_label(tick), size=11, fill=MUTED,
                        anchor="middle", cls="tick")
        for tick in y_ticks:
            canvas.line(left, sy(tick), right, sy(tick), stroke=AXIS if tick == 0 else GRID)
            canvas.text(left - 6, sy(tick) + 4, _tick_label(tick), size=11, fill=MUTED,
                        anchor="end", cls="tick")
        canvas.text(left, top - 6, "Daño térmico total", size=11, fill=INK_2)
        canvas.text((left + right) / 2, bottom + 32, "Pasos hasta terminar", size=11,
                    fill=INK_2, anchor="middle")
        if pair:
            for a, b in pairing(group, *pair).both:
                canvas.line(sx(a.steps), sy(a.damage), sx(b.steps), sy(b.damage), stroke=MUTED,
                            width=1.5, opacity=0.8, cls="pair",
                            data={"data-group": key, "data-configuration": a.configuration_id},
                            title=f"{a.scenario}: {a.steps} → {b.steps} pasos, "
                                  f"{a.damage} → {b.damage} de daño")
        winners = sorted((e for e in group if e.success),
                         key=lambda e: (draw_order.get(e.strategy, 0), e.episode_id))
        for e in winners:
            s = next(item for item in series if item.key == e.series_key)
            canvas.dot(sx(e.steps), sy(e.damage), s.color, cls="point",
                       data={"data-group": key, "data-series": s.slug,
                             "data-steps": e.steps, "data-damage": e.damage},
                       title=f"{e.scenario} · {s.name}: {e.steps} pasos, {e.damage} de daño")
    rows = math.ceil(len(panels) / columns)
    height = y + rows * panel_height + (rows - 1) * 16 + 12
    return canvas.render(height, "Duración frente a daño en misiones exitosas",
                         "Pasos y daño de cada misión exitosa; las líneas unen el mismo caso "
                         "entre las dos referencias deterministas.")


def figure_training(logs) -> str:
    """Personas entregadas en cada evaluación periódica del entrenamiento, por semilla."""
    columns = 1 if len(logs) == 1 else 2
    panel_width = 560 if columns == 1 else 414
    width = 48 + columns * panel_width + (columns - 1) * 24
    canvas = _Canvas(width)
    y = canvas.header("Curvas de entrenamiento por semilla", [
        "Personas entregadas en cada evaluación periódica (suma de los escenarios de "
        "evaluación). El círculo marca el checkpoint que guardó el entrenamiento: el primero "
        "con más misiones completas, después más personas y después más retorno.",
    ])
    x_max = max(max(p.steps for p in log.points) for log in logs)
    x_max = max(x_max, max((log.stages[-1][2] for log in logs if log.stages), default=0))
    x_ticks = _nice_ticks(x_max / 1000)
    victims = max(max(p.victims for p in log.points) for log in logs)
    y_ticks = _nice_ticks(victims, integer=True)
    plot_height = 170
    panel_height = 98 + plot_height + 44
    blue = COLORS["dqn"]
    for index, log in enumerate(logs):
        column, row = index % columns, index // columns
        px = 24 + column * (panel_width + 24)
        py = y + row * (panel_height + 16)
        left, right = px + 32, px + panel_width - 8
        top, bottom = py + 100, py + 100 + plot_height
        best = log.selected_point
        seed = "sin semilla registrada" if log.seed is None else f"semilla {log.seed}"
        canvas.text(px, py + 12, f"{log.label} · {seed}", size=12, weight=600)
        canvas.text(px, py + 28, f"Elegido: {_thousands(best.steps)} pasos, "
                                 f"{best.rescued}/{best.victims} personas, "
                                 f"{best.successes}/{best.scenarios} misiones completas",
                    size=11, fill=INK_2)
        evaluated = len(log.evaluation_scenarios) or log.points[0].scenarios
        overlap = (f"{log.overlap_with_training} también usados para entrenar"
                   if log.overlap_with_training else "ninguno usado para entrenar")
        canvas.text(px, py + 43, f"Evaluación: {evaluated} escenarios, {overlap}", size=11,
                    fill=INK_2)
        stages = " · ".join(f"{i} {name}" for i, (name, _, _) in enumerate(log.stages, 1))
        if stages:
            canvas.text(px, py + 58, f"Etapas: {stages}", size=11, fill=MUTED)

        def sx(steps):
            return left + (right - left) * (steps / 1000) / x_ticks[-1]

        def sy(value):
            return bottom - (bottom - top) * value / y_ticks[-1]

        for tick in y_ticks:
            canvas.line(left, sy(tick), right, sy(tick), stroke=AXIS if tick == 0 else GRID)
            canvas.text(left - 6, sy(tick) + 4, _tick_label(tick), size=11, fill=MUTED,
                        anchor="end", cls="tick")
        for tick in x_ticks:
            canvas.text(sx(tick * 1000), bottom + 15, _tick_label(tick), size=11, fill=MUTED,
                        anchor="middle", cls="tick")
        for number, (_, start, _) in enumerate(log.stages, 1):
            canvas.line(sx(start), top, sx(start), bottom, stroke=AXIS)
            canvas.text(sx(start) + 3, top - 4, str(number), size=10, fill=MUTED)
        canvas.text(left, top - 20, f"Personas entregadas (de {best.victims})", size=11,
                    fill=INK_2)
        canvas.text((left + right) / 2, bottom + 32, "Pasos de entrenamiento (miles)",
                    size=11, fill=INK_2, anchor="middle")
        coordinates = [(sx(p.steps), sy(p.rescued)) for p in log.points]
        path = "M" + "L".join(f"{_number(x)},{_number(yy)}" for x, yy in coordinates)
        canvas.element("path", {"d": path, "fill": "none", "stroke": blue, "stroke-width": 2,
                                "stroke-linejoin": "round", "stroke-linecap": "round",
                                "class": "curve", "data-log": log.label,
                                "data-points": len(log.points)})
        for point, (x, yy) in zip(log.points, coordinates):
            canvas.element("circle", {"cx": x, "cy": yy, "r": 8, "fill": "transparent",
                                      "class": "hit"},
                           title=f"{_thousands(point.steps)} pasos ({point.stage}): "
                                 f"{point.rescued}/{point.victims} personas, "
                                 f"{point.successes}/{point.scenarios} misiones completas")
        x, yy = coordinates[log.selected]
        canvas.element("circle", {"cx": x, "cy": yy, "r": 6, "fill": SURFACE, "stroke": INK,
                                  "stroke-width": 2, "class": "checkpoint", "data-log": log.label,
                                  "data-steps": best.steps, "data-rescued": best.rescued},
                       title=f"Checkpoint elegido: {_thousands(best.steps)} pasos, "
                             f"{best.rescued}/{best.victims} personas")
    rows = math.ceil(len(logs) / columns)
    height = y + rows * panel_height + (rows - 1) * 16 + 12
    return canvas.render(height, "Curvas de entrenamiento por semilla",
                         "Personas entregadas en las evaluaciones periódicas de cada "
                         "entrenamiento y checkpoint elegido.")


# -------------------------------------------------------------------- tablas


def _table(headers, rows, numeric_from: int = 1) -> list[str]:
    align = ["---" if i < numeric_from else "---:" for i in range(len(headers))]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(align) + "|"]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines + [""]


OUTCOME_HEADERS = ["Episodios", "Casos", "Éxitos", "Personas entregadas", "Destruidos",
                   "Límite de pasos", "Pasos medios (éxitos)", "Daño medio (éxitos)"]


def _outcome_cells(result: Outcome) -> list[str]:
    return [str(result.episodes), str(result.configurations),
            f"{result.successes}/{result.episodes}", f"{result.rescued}/{result.victims}",
            str(result.destroyed), str(result.time_limit), _dec(result.mean_steps),
            _dec(result.mean_damage)]


def _grouped_rows(episodes, series, attribute, names):
    rows = []
    for key in _ordered_keys(episodes, attribute):
        for s in series:
            members = [e for e in episodes if getattr(e, attribute) == key and e.series_key == s.key]
            if members:
                rows.append([names.get(key, key), _row_label(members, s)]
                            + _outcome_cells(outcome(members)))
    return rows


def tables_markdown(episodes, metadata: dict, sources: dict, command: str) -> str:
    series = series_of(episodes)
    cases = len({e.configuration_id for e in episodes})
    first = episodes[0]
    lines = [
        "# Tablas generadas desde los resultados conservados",
        "",
        "Archivo generado por `scripts/report_figures.py` (SARB-022). No se edita a mano: "
        "para cambiarlo se regenera, y `--check` detecta cualquier diferencia con lo que "
        "producen las fuentes.",
        "",
        f"**Datos:** {_context(episodes)}.",
        "",
        "## Fuentes",
        "",
    ]
    results = sources["results"]
    source_rows = [[f"`{results['path']}`", f"`{results['sha256']}`"],
                   [f"`{results['traces']}`", f"`{results['traces_sha256']}`"]]
    for log in sources.get("training", []):
        for name, digest in log["files"].items():
            source_rows.append([f"`{log['path']}/{name}`", f"`{digest}`"])
    lines += _table(["Archivo", "SHA-256 (LF)"], source_rows, numeric_from=2)
    lines += [
        "Trazas reproducidas en un motor nuevo antes de generar: "
        + ("sí." if results["replayed"] else "no (se usó `--skip-replay`; solo se comprobó el "
           "hash del CSV)."),
        f"Recompensa del retorno: `{metadata.get('reward_config_sha256', 'sin registrar')}`.",
        "",
        "Para regenerar:",
        "",
        "```powershell",
        command,
        "```",
        "",
        "## 1. Resultado por estrategia",
        "",
    ]
    lines += _table(["Estrategia"] + OUTCOME_HEADERS,
                    [[_row_label([e for e in episodes if e.series_key == s.key], s)]
                     + _outcome_cells(outcome([e for e in episodes if e.series_key == s.key]))
                     for s in series])
    if any(e.building for e in episodes):
        lines += ["## 2. Por edificio", ""]
        lines += _table(["Edificio", "Estrategia"] + OUTCOME_HEADERS,
                        _grouped_rows(episodes, series, "building",
                                      {k: f"{v} ({k})" for k, v in BUILDING_NAMES.items()}),
                        numeric_from=2)
    else:
        lines += ["## 2. Por escenario", ""]
        lines += _table(["Escenario", "Estrategia"] + OUTCOME_HEADERS,
                        _grouped_rows(episodes, series, "scenario", {}), numeric_from=2)
    if any(e.difficulty for e in episodes):
        lines += ["## 3. Por familia de dificultad", "",
                  "Las familias describen distancia y exposición inicial al generar los casos; "
                  "no predicen el desempeño de DQN.", ""]
        lines += _table(["Familia", "Estrategia"] + OUTCOME_HEADERS,
                        _grouped_rows(episodes, series, "difficulty", DIFFICULTY_NAMES),
                        numeric_from=2)
    else:
        lines += ["## 3. Por familia de dificultad", "",
                  "Los escenarios de esta evaluación no tienen familia registrada.", ""]
    lines += ["## 4. Comparaciones emparejadas", "",
              "Solo series con un episodio por caso. Pasos y daño se comparan sobre los casos en "
              "que ambas tuvieron éxito; las diferencias son B − A. Las columnas «B por debajo» "
              "cuentan los casos emparejados en que B usó menos pasos o recibió menos daño "
              "(menos / igual / más).", ""]
    paired_rows = []
    single = single_episode_series(episodes)
    for i, a in enumerate(single):
        for b in single[i + 1:]:
            p = pairing(episodes, a, b)
            paired_rows.append([
                a.name, b.name, str(p.shared), str(len(p.both)), str(p.only_a), str(p.only_b),
                str(p.neither), _dec(p.mean("a", "steps")), _dec(p.mean("b", "steps")),
                _signed(p.difference("steps")), "/".join(map(str, p.b_lower("steps"))),
                _dec(p.mean("a", "damage")), _dec(p.mean("b", "damage")),
                _signed(p.difference("damage")), "/".join(map(str, p.b_lower("damage")))])
    if paired_rows:
        lines += _table(["A", "B", "Casos compartidos", "Éxito en ambas", "Solo A", "Solo B",
                         "Ninguna", "Pasos A", "Pasos B", "Δ pasos", "B por debajo en pasos",
                         "Daño A", "Daño B", "Δ daño", "B por debajo en daño"], paired_rows,
                        numeric_from=2)
    else:
        lines += ["No hay dos series con un episodio por caso.", ""]
    lines += ["## 5. Variación entre semillas", ""]
    models = [s for s in series if s.strategy == "dqn"]
    if models:
        lines += ["### DQN por semilla de entrenamiento", ""]
        lines += _table(["Modelo", "Semilla"] + OUTCOME_HEADERS, [
            [s.model_label, "—" if s.training_seed is None else str(s.training_seed)]
            + _outcome_cells(outcome([e for e in episodes if e.series_key == s.key]))
            for s in models], numeric_from=2)
        counts = [outcome([e for e in episodes if e.series_key == s.key]) for s in models]
        if len(models) > 1:
            solved = Counter(sum(e.success for e in episodes
                                 if e.strategy == "dqn" and e.configuration_id == c)
                             for c in {e.configuration_id for e in episodes})
            lines += [
                "Éxitos por semilla: " + ", ".join(f"{c.successes}/{c.episodes}" for c in counts)
                + f" (mínimo {min(c.successes for c in counts)}, máximo "
                f"{max(c.successes for c in counts)}). Con {len(models)} semillas se informan "
                "todas y su rango; no se calcula un intervalo de confianza.",
                "",
                "Casos según cuántas semillas los resuelven: "
                + ", ".join(f"{k} de {len(models)}: {solved.get(k, 0)}"
                            for k in range(len(models), -1, -1)) + ".",
                "",
            ]
    random_rows = []
    for seed in sorted({e.random_seed for e in episodes if e.strategy == "random"
                        and e.random_seed is not None}):
        result = outcome([e for e in episodes if e.strategy == "random" and e.random_seed == seed])
        random_rows.append([str(seed), f"{result.successes}/{result.episodes}",
                            f"{result.rescued}/{result.victims}", str(result.destroyed),
                            str(result.time_limit)])
    if random_rows:
        lines += ["### Aleatoria por semilla de acciones", ""]
        lines += _table(["Semilla", "Éxitos", "Personas entregadas", "Destruidos",
                         "Límite de pasos"], random_rows)
    if not models and not random_rows:
        lines += ["No hay series con varias semillas.", ""]
    lines += [
        "## 6. Límites de lectura",
        "",
        f"- Hay {cases} casos distintos. En una estrategia determinista cada caso vale "
        f"{_short(100 / cases)} puntos de su tasa de éxito: diferencias de uno o dos casos no "
        "son una tendencia.",
        "- Estrategias, semillas DQN y semillas aleatorias se evalúan sobre los mismos casos. "
        "Los episodios están emparejados y no son muestras independientes; por eso se informan "
        "conteos, casos emparejados y variación entre semillas, sin intervalos de confianza que "
        "supongan independencia.",
        "- Pasos y daño se promedian solo entre misiones exitosas. Un fracaso temprano con poco "
        "daño no es un mejor resultado.",
    ]
    if first.manifest_id:
        lines.append(f"- Los casos de `{first.manifest_id}` entraron porque una referencia los "
                     "resolvió al certificarlos: la tasa de éxito de las referencias está "
                     "favorecida por construcción (`docs/PARTICIONES_V2.md`).")
    if first.partition != "test":
        lines.append(f"- Partición «{PARTITION_NAMES.get(first.partition, first.partition)}»: "
                     "no es la evaluación final reservada (SARB-021).")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ informe


def _content_sha256(data: bytes) -> str:
    return sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def report_command(results: str | None, training, output_dir: str, replay: bool) -> str:
    parts = ["uv run python scripts/report_figures.py"]
    if results:
        parts.append(f"--results {results}")
    parts += [f"--training {path}" for path in training]
    parts.append(f"--output-dir {output_dir}")
    if not replay:
        parts.append("--skip-replay")
    return " ".join(parts)


def build_report(root: str | Path, *, results: str | Path | None = None, training=(),
                 output_dir: str = "results/figuras", replay: bool = True) -> dict[str, bytes]:
    """Genera en memoria las tablas, las figuras y el registro de fuentes."""
    root = Path(root)
    if results is None and not training:
        raise ValueError("Indicar un CSV de resultados, registros de entrenamiento o ambos")
    files: dict[str, str] = {}
    sources: dict = {"schema_version": REPORT_SCHEMA, "generator": "sar_bot.report"}
    logs = [load_training_log(path, root) for path in training]
    results_rel = None
    if results is not None:
        results = Path(results)
        absolute = results if results.is_absolute() else root / results
        results_rel = _relative(absolute, root)
        episodes, metadata = load_results(absolute, root, replay=replay)
        models = {e.model_sha256 for e in episodes if e.strategy == "dqn"}
        for log in logs:
            if not models:
                raise ValueError("El CSV no tiene filas DQN: las curvas de entrenamiento se "
                                 "generan por separado")
            if log.files.get("model.zip") not in models:
                raise ValueError(f"{log.path}: su model.zip no es ninguno de los modelos del CSV")
        sources["results"] = {
            "path": results_rel, "sha256": file_sha256(absolute),
            "metadata_sha256": file_sha256(absolute.with_suffix(".metadata.json")),
            "traces": _relative(absolute.with_suffix(".traces.jsonl"), root),
            "traces_sha256": file_sha256(absolute.with_suffix(".traces.jsonl")),
            "replayed": replay,
        }
    sources["training"] = [{"path": log.path, "label": log.label, "seed": log.seed,
                            "files": log.files} for log in logs]
    command = report_command(results_rel, [log.path for log in logs], output_dir, replay)
    sources["output_dir"] = output_dir
    sources["command"] = command
    if results is not None:
        files[TABLES_FILE] = tables_markdown(episodes, metadata, sources, command)
        files[OUTCOMES_FIGURE] = figure_outcomes(episodes)
        files[SUCCESS_METRICS_FIGURE] = figure_success_metrics(episodes)
        files[TRADEOFF_FIGURE] = figure_tradeoff(episodes)
    if logs:
        files[TRAINING_FIGURE] = figure_training(logs)
    encoded = {name: text.encode("utf-8") for name, text in files.items()}
    sources["outputs"] = {name: _content_sha256(data) for name, data in sorted(encoded.items())}
    encoded[SOURCES_FILE] = (json.dumps(sources, indent=2, ensure_ascii=False) + "\n").encode()
    return encoded


def write_report(files: dict[str, bytes], output_dir: str | Path) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, data in sorted(files.items()):
        path = output_dir / name
        path.write_bytes(data)
        written.append(path)
    return written


def check_report(output_dir: str | Path, root: str | Path) -> list[str]:
    """Regenera desde las fuentes registradas y compara con lo guardado."""
    root, output_dir = Path(root), Path(output_dir)
    try:
        sources = json.loads((output_dir / SOURCES_FILE).read_text(encoding="utf-8"))
        results = sources.get("results")
        files = build_report(
            root, results=results["path"] if results else None,
            training=[log["path"] for log in sources.get("training", [])],
            output_dir=sources["output_dir"],
            replay=results["replayed"] if results else True)
    except (OSError, ValueError, KeyError) as error:
        return [f"No se pudo regenerar: {error}"]
    problems = []
    for name, data in sorted(files.items()):
        path = output_dir / name
        if not path.is_file():
            problems.append(f"Falta {name}")
        elif _content_sha256(path.read_bytes()) != _content_sha256(data):
            problems.append(f"{name} no coincide con lo que producen las fuentes")
    for name in sorted(sources.get("outputs", {})):
        if name not in files:
            problems.append(f"{name} figura en {SOURCES_FILE} pero ya no se genera")
    return problems
