"""Estudio de escala, reparto de rescates y dificultad (SARB-031).

Lee CSV conservados de ``scripts/evaluate_experiment.py`` (reproduciendo sus
trazas), calcula rasgos de cada caso a partir de su escenario y genera tablas
deterministas. No ejecuta misiones: las cifras salen siempre de archivos
versionados, y ``check_study`` regenera las tablas para detectar ediciones.

Rasgos de un caso (antes de la misión):

- ``distance``: distancia Manhattan media de las personas a la base, dividida
  por ``ancho + alto − 2``;
- ``spread``: distancia Manhattan media entre pares de personas, con la misma
  normalización;
- ``hot``: personas cuya celda inicial produce daño (40 °C o más);
- ``difficulty``: familia del generador (``classify_difficulty``).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
import json
from pathlib import Path
from statistics import median

from sar_bot.core import Scenario
from sar_bot.core.generation import classify_difficulty
from sar_bot.core.simulation import damage_rate
from sar_bot.experiment import read_results, verify_results
from sar_bot.partitions import file_sha256
from sar_bot.report import (
    BUILDING_NAMES,
    DIFFICULTY_NAMES,
    PARTITION_NAMES,
    Series,
    _content_sha256,
    _dec,
    _relative,
    _signed,
    _table,
)

STUDY_SCHEMA = 1
TABLES_FILE = "tablas.md"
SOURCES_FILE = "fuentes.json"
REFERENCES = ("shortest", "thermal")
INTEGER_COLUMNS = ("victims_total", "rescued", "steps", "max_steps", "damage_total",
                   "deliveries_robot_1", "deliveries_robot_2", "wait_actions", "blocked_moves",
                   "planning_failures", "replans", "expanded_states", "width", "height")
BUILDING_NAMES = {**BUILDING_NAMES, "building10": "Edificio de 10 × 10"}
STRATEGY_ORDER = ("dqn", "shortest", "thermal", "random")


@dataclass(frozen=True)
class Features:
    distance: float
    spread: float
    hot: int
    difficulty: str


def case_features(scenario: Scenario) -> Features:
    scale = max(1, scenario.width + scenario.height - 2)
    victims = scenario.victims
    distance = sum(abs(x - scenario.base[0]) + abs(y - scenario.base[1])
                   for x, y in victims) / (len(victims) * scale)
    pairs = list(combinations(victims, 2))
    spread = (sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in pairs) / (len(pairs) * scale)
              if pairs else 0.0)
    hot = sum(damage_rate(scenario.temperature_at(p)) > 0 for p in victims)
    difficulty = (classify_difficulty(scenario, victims).value
                  if scenario.victim_count == 3 else "")
    return Features(distance, spread, hot, difficulty)


def _typed(row: dict) -> dict:
    result = dict(row)
    for column in INTEGER_COLUMNS:
        result[column] = int(row[column])
    result["success"] = row["success"] == "True"
    result["compute_seconds"] = float(row["compute_seconds"])
    result["random_seed"] = int(row["random_seed"]) if row["random_seed"] else None
    result["training_seed"] = int(row["training_seed"]) if row["training_seed"] else None
    result["series"] = (row["strategy"], row["model_label"])
    return result


@dataclass
class Dataset:
    path: str
    rows: list
    features: dict
    hashes: dict
    replayed: bool

    @property
    def profile(self) -> tuple[int, int, int]:
        row = self.rows[0]
        return (row["width"], row["height"], row["victims_total"])

    @property
    def partition(self) -> str:
        return self.rows[0]["partition"]

    @property
    def source(self) -> str:
        return self.rows[0]["manifest_id"] or "escenarios fijos"

    @property
    def label(self) -> str:
        width, height, victims = self.profile
        partition = PARTITION_NAMES.get(self.partition, self.partition).lower()
        return f"{width} × {height} · {partition} · {self.source}"

    @property
    def cases(self) -> int:
        return len({row["configuration_id"] for row in self.rows})

    def series(self) -> list[Series]:
        found = {}
        for row in self.rows:
            found.setdefault(row["series"], Series(row["strategy"], row["model_label"],
                                                   row["training_seed"]))
        return sorted(found.values(), key=lambda s: (STRATEGY_ORDER.index(s.strategy),
                                                     s.training_seed or 0, s.model_label))

    def feature(self, row) -> Features:
        return self.features[row["scenario_path"]]


def load_dataset(csv_path: str | Path, root: str | Path, *, replay: bool = True) -> Dataset:
    root = Path(root)
    csv_path = Path(csv_path)
    absolute = csv_path if csv_path.is_absolute() else root / csv_path
    metadata = json.loads(absolute.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    if replay:
        problems = verify_results(absolute, root)
    else:
        problems = ([] if file_sha256(absolute) == metadata.get("csv_sha256")
                    else ["El CSV cambió después de escribirse"])
    if problems:
        raise ValueError(f"{absolute.name} no está íntegro: " + "; ".join(problems[:3]))
    rows = [_typed(row) for row in read_results(absolute)]
    if not rows:
        raise ValueError(f"{absolute.name} no tiene episodios")
    features = {}
    for row in rows:
        path = row["scenario_path"]
        if path not in features:
            features[path] = case_features(Scenario.load(root / path))
        if row["difficulty"] and row["difficulty"] != features[path].difficulty:
            raise ValueError(f"{path}: la familia del CSV no coincide con la del generador")
    hashes = {"csv": file_sha256(absolute),
              "traces": file_sha256(absolute.with_suffix(".traces.jsonl")),
              "metadata": file_sha256(absolute.with_suffix(".metadata.json"))}
    return Dataset(_relative(absolute, root), rows, features, hashes, replay)


# ------------------------------------------------------------------ cálculos


def _mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def _median(values):
    values = list(values)
    return median(values) if values else None


def _of(rows, series) -> list:
    return [row for row in rows if row["series"] == series]


def _success_cells(rows) -> list[str]:
    winners = [row for row in rows if row["success"]]
    return [f"{len(winners)}/{len(rows)}",
            f"{sum(r['rescued'] for r in rows)}/{sum(r['victims_total'] for r in rows)}",
            _dec(_mean(r["steps"] for r in winners)),
            _dec(_mean(r["damage_total"] for r in winners))]


def _paired(rows):
    """Casos en que la ruta corta y la térmica tuvieron éxito, emparejados."""
    by_case = defaultdict(dict)
    for row in rows:
        if row["strategy"] in REFERENCES:
            by_case[row["configuration_id"]][row["strategy"]] = row
    return [(d["shortest"], d["thermal"]) for d in by_case.values()
            if len(d) == 2 and d["shortest"]["success"] and d["thermal"]["success"]]


def _split(row) -> str:
    first, second = sorted((row["deliveries_robot_1"], row["deliveries_robot_2"]), reverse=True)
    return f"{first}–{second}"


def _tertiles(values) -> tuple[float, float]:
    ordered = sorted(values)
    n = len(ordered)
    return ordered[n // 3], ordered[(2 * n) // 3]


def _bin(value, cuts) -> int:
    return 0 if value < cuts[0] else 1 if value < cuts[1] else 2


def _ms(value) -> str:
    return "—" if value is None else _dec(value * 1000)


def _md(headers, rows, text_columns) -> list[str]:
    """Tabla Markdown con las columnas de texto a la izquierda y las numéricas a la derecha."""
    align = ["---" if i in text_columns else "---:" for i in range(len(headers))]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(align) + "|"]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines + [""]


# -------------------------------------------------------------------- tablas


def _sources_table(datasets) -> list[str]:
    rows = []
    for d in datasets:
        width, height, victims = d.profile
        strategies = ", ".join(s.name for s in d.series())
        rows.append([d.label, f"{width} × {height}, {victims} personas",
                     str(d.cases), str(len(d.rows)), strategies, f"`{d.path}`",
                     f"`{d.hashes['csv'][:16]}…`"])
    return _md(["Conjunto", "Perfil", "Casos", "Episodios", "Estrategias", "CSV",
                "SHA-256 (LF)"], rows, {0, 1, 4, 5, 6})


def _scale_table(datasets) -> list[str]:
    rows = []
    for d in datasets:
        distance = _mean(f.distance for f in d.features.values())
        for s in d.series():
            members = _of(d.rows, s.key)
            reference = s.strategy in REFERENCES
            rows.append([d.label, s.name + (f" · {len(members) // d.cases} semillas"
                                            if s.strategy == "random" else ""),
                         _dec(distance, 2), _dec(_median(r["max_steps"] for r in members), 0)]
                        + _success_cells(members)
                        + [_dec(_median(r["expanded_states"] for r in members), 0)
                           if reference else "—",
                           _ms(_median(r["compute_seconds"] for r in members))])
    return _table(["Conjunto", "Estrategia", "Distancia media", "Límite de pasos", "Éxitos",
                   "Personas entregadas", "Pasos medios (éxitos)", "Daño medio (éxitos)",
                   "Estados expandidos (mediana)", "Cómputo por episodio (mediana, ms)"], rows,
                  numeric_from=2)


def _pooled(datasets):
    """Episodios de tres personas agrupados por perfil y edificio etiquetado."""
    pools = defaultdict(list)
    for d in datasets:
        if d.profile[2] != 3:
            continue
        for row in d.rows:
            if row["building"]:
                pools[(d.profile, row["building"])].append((row, d.feature(row)))
    return pools


def _pool_label(profile, building) -> str:
    name = BUILDING_NAMES.get(building, building)
    return f"{profile[0]} × {profile[1]} · {name} ({building})"


def _difficulty_table(datasets) -> list[str]:
    rows = []
    for (profile, building), items in sorted(_pooled(datasets).items(),
                                             key=lambda kv: (kv[0][0], kv[0][1])):
        for family in DIFFICULTY_NAMES:
            members = [(r, f) for r, f in items if f.difficulty == family]
            if not members:
                continue
            cases = {r["configuration_id"]: f for r, f in members}
            line = [_pool_label(profile, building), DIFFICULTY_NAMES[family], str(len(cases)),
                    _dec(_mean(f.distance for f in cases.values()), 2),
                    _dec(_mean(f.spread for f in cases.values()), 2),
                    _dec(_mean(f.hot for f in cases.values()), 1)]
            plain = [r for r, _ in members]
            for strategy in REFERENCES:
                chosen = [r for r in plain if r["strategy"] == strategy]
                winners = [r for r in chosen if r["success"]]
                line += [f"{len(winners)}/{len(chosen)}",
                         _dec(_mean(r["steps"] for r in winners)),
                         _dec(_mean(r["damage_total"] for r in winners))]
            pairs = _paired(plain)
            line += [str(len(pairs)),
                     _signed(_mean(t["steps"] - s["steps"] for s, t in pairs)),
                     _signed(_mean(t["damage_total"] - s["damage_total"] for s, t in pairs))]
            rows.append(line)
    return _table(["Edificio", "Familia", "Casos", "Distancia", "Separación",
                   "Personas en zona de daño (media)", "Corta: éxitos", "Corta: pasos",
                   "Corta: daño", "Térmica: éxitos", "Térmica: pasos", "Térmica: daño",
                   "Emparejados", "Δ pasos (térmica − corta)", "Δ daño (térmica − corta)"],
                  rows, numeric_from=2)


def _profile_pools(datasets):
    pools = defaultdict(list)
    for d in datasets:
        if d.profile[2] == 3 and any(row["building"] for row in d.rows):
            pools[d.profile].extend((row, d.feature(row)) for row in d.rows)
    return pools


def _separation_table(datasets) -> list[str]:
    rows = []
    names = ("baja", "media", "alta")
    for profile, items in sorted(_profile_pools(datasets).items()):
        spreads = {r["configuration_id"]: f.spread for r, f in items}
        cuts = _tertiles(spreads.values())
        for index, name in enumerate(names):
            low = "" if index == 0 else f"≥ {_dec(cuts[index - 1], 2)}"
            high = "" if index == 2 else f"< {_dec(cuts[index], 2)}"
            members = [r for r, f in items if _bin(f.spread, cuts) == index]
            cases = len({r["configuration_id"] for r in members})
            for strategy in REFERENCES:
                chosen = [r for r in members if r["strategy"] == strategy]
                winners = [r for r in chosen if r["success"]]
                splits = Counter(_split(r) for r in winners)
                rows.append([f"{profile[0]} × {profile[1]}",
                             f"{name} ({' y '.join(x for x in (low, high) if x)})", str(cases),
                             "Ruta corta" if strategy == "shortest" else "Ruta térmica"]
                            + _success_cells(chosen)
                            + [_dec(_mean(r["wait_actions"] for r in chosen)),
                               " · ".join(f"{k}: {v}" for k, v in sorted(splits.items(),
                                                                          reverse=True)) or "—"])
    return _md(["Perfil", "Separación entre personas", "Casos", "Estrategia", "Éxitos",
                "Personas entregadas", "Pasos medios (éxitos)", "Daño medio (éxitos)",
                "Esperas por episodio", "Reparto de entregas en éxitos"], rows, {0, 1, 3, 9})


def _exposure_table(datasets) -> list[str]:
    rows = []
    for profile, items in sorted(_profile_pools(datasets).items()):
        for hot in sorted({f.hot for _, f in items}):
            members = [r for r, f in items if f.hot == hot]
            cases = len({r["configuration_id"] for r in members})
            shortest = [r for r in members if r["strategy"] == "shortest"]
            thermal = [r for r in members if r["strategy"] == "thermal"]
            pairs = _paired(members)
            rows.append([f"{profile[0]} × {profile[1]}", str(hot), str(cases),
                         f"{sum(r['success'] for r in shortest)}/{len(shortest)}",
                         str(sum(r["outcome"] == "destroyed" for r in shortest)),
                         f"{sum(r['success'] for r in thermal)}/{len(thermal)}",
                         str(sum(r["outcome"] == "destroyed" for r in thermal)),
                         str(len(pairs)),
                         _dec(_mean(s["damage_total"] for s, _ in pairs)),
                         _dec(_mean(t["damage_total"] for _, t in pairs)),
                         _signed(_mean(t["steps"] - s["steps"] for s, t in pairs))])
    return _table(["Perfil", "Personas en zona de daño", "Casos", "Corta: éxitos",
                   "Corta: destruidos", "Térmica: éxitos", "Térmica: destruidos",
                   "Emparejados", "Daño corta (emparejados)", "Daño térmica (emparejados)",
                   "Pasos extra de la térmica"], rows, numeric_from=1)


def _work_table(datasets) -> list[str]:
    rows = []
    for d in datasets:
        for s in d.series():
            members = _of(d.rows, s.key)
            winners = [r for r in members if r["success"]]
            splits = Counter(_split(r) for r in winners)
            second = sum(max(r["deliveries_robot_1"], r["deliveries_robot_2"]) >= 2
                         for r in winners)
            rows.append([d.label, s.name, f"{len(winners)}/{len(members)}",
                         " · ".join(f"{k}: {v}" for k, v in sorted(splits.items(),
                                                                    reverse=True)) or "—",
                         f"{second}/{len(winners)}",
                         _dec(_mean(r["wait_actions"] for r in members)),
                         _dec(_mean(r["blocked_moves"] for r in members)),
                         str(sum(r["planning_failures"] for r in members)),
                         _dec(_mean(r["replans"] for r in members))])
    return _md(["Conjunto", "Estrategia", "Éxitos", "Reparto de entregas en éxitos",
                "Éxitos con segundo viaje", "Esperas por episodio", "Bloqueos por episodio",
                "Fallos de planificación", "Replanificaciones por episodio"], rows, {0, 1, 3})


def _compute_table(datasets) -> list[str]:
    rows = []
    for d in datasets:
        by_family = defaultdict(list)
        for row in d.rows:
            if row["strategy"] in REFERENCES:
                by_family[(d.feature(row).difficulty, row["strategy"])].append(row)
        for family in list(DIFFICULTY_NAMES) + [""]:
            for strategy in REFERENCES:
                members = by_family.get((family, strategy))
                if not members:
                    continue
                expanded = [r["expanded_states"] for r in members]
                seconds = [r["compute_seconds"] for r in members]
                rows.append([d.label, DIFFICULTY_NAMES.get(family, "sin familia"),
                             "Ruta corta" if strategy == "shortest" else "Ruta térmica",
                             str(len(members)), _dec(_median(r["steps"] for r in members), 0),
                             _dec(_median(expanded), 0), str(max(expanded)),
                             _ms(_median(seconds)), _ms(max(seconds))])
    return _table(["Conjunto", "Familia", "Referencia", "Episodios", "Pasos simulados (mediana)",
                   "Estados expandidos (mediana)", "Estados expandidos (máximo)",
                   "Cómputo (mediana, ms)", "Cómputo (máximo, ms)"], rows, numeric_from=3)


def study_command(results, output_dir: str, replay: bool) -> str:
    parts = ["uv run python scripts/scale_study.py analyze --results " + " ".join(results),
             f"--output-dir {output_dir}"]
    if not replay:
        parts.append("--skip-replay")
    return " ".join(parts)


def tables_markdown(datasets, command: str) -> str:
    replayed = all(d.replayed for d in datasets)
    lines = [
        "# Estudio de escala, reparto de rescates y dificultad",
        "",
        "Archivo generado por `scripts/scale_study.py` (SARB-031). No se edita a mano: "
        "`check` lo regenera desde los CSV y detecta cualquier diferencia.",
        "",
        "Trazas reproducidas antes de generar: " + ("sí." if replayed else "no (`--skip-replay`)."),
        "",
        "```powershell",
        command,
        "```",
        "",
        "Rasgos de cada caso, calculados del escenario antes de la misión: **distancia** media "
        "de las personas a la base y **separación** media entre pares de personas, ambas "
        "divididas por `ancho + alto − 2`; **personas en zona de daño**, las que empiezan en una "
        "celda de 40 °C o más. Pasos y daño se promedian solo entre misiones exitosas; las "
        "proporciones llevan su denominador.",
        "",
        "## 1. Conjuntos analizados",
        "",
    ]
    lines += _sources_table(datasets)
    lines += ["## 2. Escala: resultados por perfil", "",
              "Cada fila es un conjunto evaluado por separado; los perfiles no se mezclan. Los "
              "estados expandidos y el cómputo solo aplican a las referencias que planifican. "
              "El cómputo se mide en la máquina que evaluó y no es tiempo simulado.", ""]
    lines += _scale_table(datasets)
    lines += ["## 3. Dificultad por edificio y familia", "",
              "Referencias deterministas en los casos de tres personas, juntando los conjuntos de "
              "un mismo edificio (por ejemplo, entrenamiento y validación). Las diferencias "
              "emparejadas usan solo los casos que ambas referencias resolvieron.", ""]
    lines += _difficulty_table(datasets)
    lines += ["## 4. Separación entre personas", "",
              "Los casos de cada perfil se dividen en terciles de separación. El reparto indica "
              "cuántas personas entregó cada robot (mayor–menor). Cada robot lleva una persona a "
              "la vez, así que con tres personas todo éxito incluye al menos un segundo viaje.",
              ""]
    lines += _separation_table(datasets)
    lines += ["## 5. Exposición térmica inicial", "",
              "Casos según cuántas personas empiezan en zona de daño. Las columnas emparejadas "
              "comparan la ruta corta y la térmica en los mismos casos resueltos por ambas.", ""]
    lines += _exposure_table(datasets)
    lines += ["## 6. Reparto de trabajo observado", "",
              "Entregas por robot, esperas y bloqueos salen de las trazas reproducidas. Describen "
              "lo que ocurrió; no prueban que una estrategia coopere mejor ni explican intenciones "
              "del agente. «Segundo viaje» cuenta los éxitos en que un robot entregó a dos o más "
              "personas: con dos personas distingue un reparto 1–1 de uno 2–0, y con tres es "
              "obligatorio porque cada robot lleva una persona a la vez.", ""]
    lines += _work_table(datasets)
    lines += ["## 7. Cómputo de las referencias", "",
              "Estados expandidos y segundos de cómputo por episodio, separados del tiempo "
              "simulado (pasos) y de la reproducción visual. Los segundos dependen de la máquina.",
              ""]
    lines += _compute_table(datasets)
    lines += ["## 8. Límites", ""]
    profiles = sorted({d.profile for d in datasets})
    lines += [
        f"- Perfiles analizados: {', '.join(f'{w} × {h} con {v} personas' for w, h, v in profiles)}."
        " Los perfiles difieren también en cantidad de personas y límite de pasos, así que la "
        "escala no se aísla de esos factores.",
        "- Los casos generados entraron porque una referencia los resolvió al certificarlos: el "
        "éxito de las referencias está favorecido por construcción.",
        "- Las familias y los terciles son agrupaciones descriptivas con pocos casos por celda; "
        "no son pruebas de significancia.",
        "- La referencia aleatoria repite la misma secuencia de acciones por semilla en todos "
        "los casos.",
    ]
    if any(row["strategy"] == "dqn" for d in datasets for row in d.rows):
        lines.append("- Las filas DQN son modelos de desarrollo de su propio perfil. No son los "
                     "modelos finales (SARB-019) y ningún checkpoint se evalúa en otro perfil.")
    return "\n".join(lines) + "\n"


def build_study(root: str | Path, results, *, output_dir: str,
                replay: bool = True) -> dict[str, bytes]:
    root = Path(root)
    datasets = [load_dataset(path, root, replay=replay) for path in results]
    datasets.sort(key=lambda d: (d.profile, d.partition, d.source))
    command = study_command([d.path for d in datasets], output_dir, replay)
    text = tables_markdown(datasets, command)
    files = {TABLES_FILE: text.encode("utf-8")}
    sources = {
        "schema_version": STUDY_SCHEMA, "generator": "sar_bot.study",
        "results": [{"path": d.path, **{f"{k}_sha256": v for k, v in d.hashes.items()},
                     "replayed": d.replayed} for d in datasets],
        "output_dir": output_dir, "command": command,
        "outputs": {name: _content_sha256(data) for name, data in files.items()},
    }
    files[SOURCES_FILE] = (json.dumps(sources, indent=2, ensure_ascii=False) + "\n").encode()
    return files


def check_study(output_dir: str | Path, root: str | Path) -> list[str]:
    root, output_dir = Path(root), Path(output_dir)
    try:
        sources = json.loads((output_dir / SOURCES_FILE).read_text(encoding="utf-8"))
        files = build_study(root, [r["path"] for r in sources["results"]],
                            output_dir=sources["output_dir"],
                            replay=all(r["replayed"] for r in sources["results"]))
    except (OSError, ValueError, KeyError) as error:
        return [f"No se pudo regenerar: {error}"]
    problems = []
    for name, data in sorted(files.items()):
        path = output_dir / name
        if not path.is_file():
            problems.append(f"Falta {name}")
        elif _content_sha256(path.read_bytes()) != _content_sha256(data):
            problems.append(f"{name} no coincide con lo que producen las fuentes")
    return problems
