"""Particiones experimentales congeladas (SARB-009).

Construye conjuntos de entrenamiento, validación y prueba a partir del
generador certificado de V2 y verifica que el manifiesto resultante siga
intacto: hashes, identificadores, perfil, cuotas, testigos y separación.

Las particiones son por perfil (dimensiones y cantidad de personas). Un
manifiesto nunca mezcla edificios de tamaños distintos.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import random

from sar_bot.core import (
    Difficulty,
    Scenario,
    ViabilityCertificate,
    generate_configurations,
    replay_certificate,
)

PARTITIONS = ("training", "validation", "test")
MANIFEST_SCHEMA = 1


def file_sha256(path: str | Path) -> str:
    """Hash del contenido con finales de línea normalizados.

    Git puede convertir LF a CRLF en Windows; normalizar evita que el mismo
    archivo tenga hashes distintos según el sistema que lo descargó.
    """
    return sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def canonical_sha256(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8")).hexdigest()


def content_sha256(manifest: dict) -> str:
    """Firma de todo el manifiesto salvo el propio campo de firma."""
    return canonical_sha256({k: v for k, v in manifest.items() if k != "content_sha256"})


def _write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _same_building(template: Scenario, scenario: Scenario) -> bool:
    return (scenario.width, scenario.height, scenario.base, scenario.walls,
            scenario.temperatures, scenario.max_steps) == (
        template.width, template.height, template.base, template.walls,
        template.temperatures, template.max_steps)


def excluded_scenarios(config: dict, root: Path) -> dict[str, str]:
    """Configuraciones de desarrollo que no pueden entrar en ninguna partición.

    Incluye las posiciones de ejemplo de cada plantilla y los ejemplos de
    familias publicados por persona 2. Devuelve ``scenario_id -> origen``.
    """
    excluded = {}
    templates = {}
    for building in config["buildings"]:
        template = Scenario.load(root / building["template"])
        templates[building["template"]] = template
        excluded[template.scenario_id] = f"{building['template']}#victims"
    for source in config.get("excluded_sources", []):
        data = json.loads((root / source).read_text(encoding="utf-8"))
        for item in data.get("buildings", []):
            template = templates.get(item["template"]) or Scenario.load(root / item["template"])
            for family, positions in item.get("examples", {}).items():
                scenario = template.with_victims(tuple(tuple(p) for p in positions))
                excluded[scenario.scenario_id] = f"{source}#{item['template']}#{family}"
    return excluded


def legacy_scenario_ids(config: dict, root: Path) -> set[str]:
    ids = set()
    for manifest in config.get("legacy_manifests", []):
        data = json.loads((root / manifest).read_text(encoding="utf-8"))
        for partition in PARTITIONS:
            for path in data.get(partition, []):
                ids.add(Scenario.load(root / path).scenario_id)
    return ids


def _validate_config(config: dict):
    if config.get("schema_version") != 1:
        raise ValueError("Versión de configuración de particiones no compatible")
    if not config.get("buildings"):
        raise ValueError("Se requiere al menos un edificio")
    keys = [building["key"] for building in config["buildings"]]
    if len(keys) != len(set(keys)):
        raise ValueError("Las claves de edificio deben ser únicas")
    difficulties = {d.value for d in Difficulty}
    for building in config["buildings"]:
        quotas = building["quotas"]
        if set(quotas) != set(PARTITIONS):
            raise ValueError(f"{building['key']}: se requieren cuotas para {PARTITIONS}")
        for partition, values in quotas.items():
            if not set(values) <= difficulties or any(
                    type(v) is not int or v < 0 for v in values.values()):
                raise ValueError(f"{building['key']}/{partition}: cuotas inválidas")
    test_total = sum(sum(b["quotas"]["test"].values()) for b in config["buildings"])
    if test_total < config.get("min_test_total", 0):
        raise ValueError("Las cuotas de prueba no alcanzan el mínimo declarado")


@dataclass(frozen=True)
class PartitionBuild:
    manifest: dict
    scenarios: dict[str, Scenario]
    witnesses: list[dict]


def build_partitions(config: dict, root: str | Path) -> PartitionBuild:
    """Genera, filtra, asigna y describe las particiones sin escribir archivos."""
    root = Path(root)
    _validate_config(config)
    profile = config["profile"]
    excluded = excluded_scenarios(config, root)
    legacy = legacy_scenario_ids(config, root)
    order = tuple(Difficulty)
    entries, witnesses, scenarios = [], [], {}
    generation_records, diagnostics = [], []
    seen = set()

    for building in config["buildings"]:
        template = Scenario.load(root / building["template"])
        if (template.width, template.height, template.victim_count) != (
                profile["width"], profile["height"], profile["victims"]):
            raise ValueError(f"{building['key']}: la plantilla no pertenece al perfil declarado")
        quotas = building["quotas"]
        needed = {d: sum(quotas[p].get(d.value, 0) for p in PARTITIONS) for d in order}
        surplus = building.get("surplus_per_difficulty", 0)
        # El generador alterna familias, así que pedir múltiplos completos
        # garantiza el mismo margen para cada dificultad.
        requested = len(order) * (max(needed.values()) + surplus)
        summary = generate_configurations(
            template, seed=building["generation_seed"], requested=requested,
            max_attempts=building["max_attempts"], difficulties=order,
            action_budget=building.get("action_budget"))
        by_difficulty = {d: [] for d in order}
        skipped = Counter()
        for index, item in enumerate(summary.accepted):
            scenario_id = item.scenario.scenario_id
            if scenario_id in excluded:
                skipped["development_example"] += 1
            elif scenario_id in legacy:
                skipped["legacy_partition"] += 1
            elif scenario_id in seen:
                skipped["duplicate_other_building"] += 1
            else:
                by_difficulty[item.difficulty].append((index, item))
        for difficulty in order:
            if len(by_difficulty[difficulty]) < needed[difficulty]:
                raise ValueError(
                    f"{building['key']}/{difficulty.value}: solo {len(by_difficulty[difficulty])} "
                    f"configuraciones certificadas para {needed[difficulty]} requeridas; "
                    "acordar y registrar una reducción antes de entrenar")

        rng = random.Random(building["split_seed"])
        unused = 0
        for difficulty in order:
            pool = by_difficulty[difficulty]
            unused += len(pool) - needed[difficulty]
            selected = pool[:needed[difficulty]]
            rng.shuffle(selected)
            cursor = 0
            # Prueba primero: su composición queda fijada antes que el resto.
            for partition in ("test", "validation", "training"):
                count = quotas[partition].get(difficulty.value, 0)
                for index, item in selected[cursor:cursor + count]:
                    seen.add(item.scenario.scenario_id)
                    entries.append((partition, building, difficulty, index, item))
                cursor += count

        generation_records.append({
            "building": building["key"],
            "template": building["template"],
            "template_sha256": file_sha256(root / building["template"]),
            "generation_seed": building["generation_seed"],
            "split_seed": building["split_seed"],
            "requested": requested,
            "max_attempts": building["max_attempts"],
            "attempts": summary.attempts,
            "certified": summary.accepted_count,
            "not_certified": len(summary.not_certified),
            "structural_invalid": summary.structural_invalid,
            "duplicates": summary.duplicates,
            "skipped": dict(sorted(skipped.items())),
            "certified_unused": unused,
            "action_budget": building.get("action_budget"),
        })
        diagnostics.extend({
            "building": building["key"],
            "difficulty": item.difficulty.value,
            "victims": [list(p) for p in item.scenario.victims],
            "scenario_id": item.scenario.scenario_id,
            "viability": item.viability.status.value,
        } for item in summary.not_certified)

    scenario_dir = config["scenario_dir"].rstrip("/")
    manifest_entries = []
    counters = Counter()
    for partition, building, difficulty, index, item in sorted(
            entries, key=lambda e: (PARTITIONS.index(e[0]), e[1]["key"],
                                    order.index(e[2]), e[3])):
        counters[(partition, building["key"])] += 1
        number = counters[(partition, building["key"])]
        name = f"{building['key']}_{partition}_{number:02d}_{difficulty.value}"
        path = f"{scenario_dir}/{partition}/{name}.json"
        scenario = item.scenario.with_victims(item.scenario.victims, name=name)
        certificate = item.viability.certificate
        scenarios[path] = scenario
        manifest_entries.append({
            "path": path,
            "partition": partition,
            "building": building["key"],
            "difficulty": difficulty.value,
            "generation_index": index,
            "victims": [list(p) for p in scenario.victims],
            "scenario_id": scenario.scenario_id,
            "configuration_id": scenario.configuration_id,
            "sha256": None,
            "witness": {
                "strategy": certificate.strategy,
                "steps": certificate.steps,
                "damage_total": certificate.damage_total,
            },
        })
        witnesses.append({
            "configuration_id": scenario.configuration_id,
            "scenario_id": scenario.scenario_id,
            "strategy": certificate.strategy,
            "steps": certificate.steps,
            "rescued": certificate.rescued,
            "damage_total": certificate.damage_total,
            "final_integrities": list(certificate.final_integrities),
            "outcome": certificate.outcome,
            "actions": list(certificate.actions),
        })

    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "manifest_id": config["manifest_id"],
        "frozen_on": config["frozen_on"],
        "profile": profile,
        "config": config,
        "rules": [
            "La prueba no se usa para entrenar, elegir checkpoints, ajustar recompensas ni decidir qué semilla mostrar.",
            "La validación es la única partición para seleccionar checkpoints o configuraciones.",
            "Solo se aceptan configuraciones con certificado positivo de una referencia; no representan todas las posiciones transitables.",
            "Los ejemplos de desarrollo y las particiones históricas quedan excluidos.",
        ],
        **{partition: [e["path"] for e in manifest_entries if e["partition"] == partition]
           for partition in PARTITIONS},
        "entries": manifest_entries,
        "generation": generation_records,
        "excluded_scenario_ids": dict(sorted(excluded.items())),
        "diagnostic_not_certified": diagnostics,
        "witnesses_file": config["output_witnesses"],
        "witnesses_sha256": None,
        "content_sha256": None,
    }
    return PartitionBuild(manifest, scenarios, witnesses)


def _scenario_text(scenario: Scenario) -> str:
    return json.dumps(scenario.to_dict(), indent=2, ensure_ascii=False) + "\n"


def write_partitions(build: PartitionBuild, root: str | Path) -> Path:
    """Escribe escenarios, testigos y manifiesto; nunca sobrescribe."""
    root = Path(root)
    manifest = json.loads(json.dumps(build.manifest))
    targets = [root / path for path in build.scenarios] + [
        root / manifest["witnesses_file"], root / manifest["config"]["output_manifest"]]
    existing = [str(path) for path in targets if path.exists()]
    if existing:
        raise FileExistsError(
            "Las particiones congeladas ya existen; crear un manifest_id nuevo en vez de "
            f"sobrescribir: {existing[:3]}")
    for entry in manifest["entries"]:
        path = root / entry["path"]
        _write_text(path, _scenario_text(build.scenarios[entry["path"]]))
        entry["sha256"] = file_sha256(path)
    witnesses_path = root / manifest["witnesses_file"]
    _write_text(witnesses_path, "".join(
        json.dumps(w, separators=(",", ":")) + "\n" for w in build.witnesses))
    manifest["witnesses_sha256"] = file_sha256(witnesses_path)
    manifest["content_sha256"] = content_sha256(manifest)
    manifest_path = root / manifest["config"]["output_manifest"]
    _write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest_path


def verify_manifest(manifest_path: str | Path, root: str | Path, *,
                    replay_witnesses: bool = True) -> list[str]:
    """Devuelve la lista de problemas; vacía significa manifiesto íntegro."""
    root = Path(root)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    problems = []
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        return ["Versión de manifiesto no compatible"]
    if manifest.get("content_sha256") != content_sha256(manifest):
        problems.append("content_sha256 no coincide: el manifiesto fue modificado")
    config = manifest["config"]
    profile = manifest["profile"]
    entries = manifest["entries"]

    for partition in PARTITIONS:
        listed = manifest.get(partition, [])
        expected = [e["path"] for e in entries if e["partition"] == partition]
        if listed != expected:
            problems.append(f"La lista '{partition}' no coincide con sus entradas")

    paths = [e["path"] for e in entries]
    for label, values in (("path", paths),
                          ("scenario_id", [e["scenario_id"] for e in entries]),
                          ("configuration_id", [e["configuration_id"] for e in entries])):
        repeated = [value for value, count in Counter(values).items() if count > 1]
        if repeated:
            problems.append(f"{label} repetido entre particiones: {repeated[:3]}")

    excluded = set(manifest.get("excluded_scenario_ids", {}))
    legacy = legacy_scenario_ids(config, root)
    for entry in entries:
        if entry["scenario_id"] in excluded:
            problems.append(f"{entry['path']}: usa un ejemplo de desarrollo excluido")
        if entry["scenario_id"] in legacy:
            problems.append(f"{entry['path']}: repite una partición histórica")

    templates = {b["key"]: Scenario.load(root / b["template"]) for b in config["buildings"]}
    template_hashes = {r["building"]: r["template_sha256"] for r in manifest["generation"]}
    for building in config["buildings"]:
        if file_sha256(root / building["template"]) != template_hashes.get(building["key"]):
            problems.append(f"La plantilla de {building['key']} cambió después de congelar")

    loaded = {}
    for entry in entries:
        path = root / entry["path"]
        if not path.exists():
            problems.append(f"{entry['path']}: falta el archivo")
            continue
        if file_sha256(path) != entry["sha256"]:
            problems.append(f"{entry['path']}: hash distinto al congelado")
        try:
            scenario = Scenario.load(path)
        except ValueError as error:
            problems.append(f"{entry['path']}: {error}")
            continue
        loaded[entry["configuration_id"]] = scenario
        if (scenario.width, scenario.height, scenario.victim_count) != (
                profile["width"], profile["height"], profile["victims"]):
            problems.append(f"{entry['path']}: perfil distinto al del manifiesto")
        if (scenario.scenario_id, scenario.configuration_id) != (
                entry["scenario_id"], entry["configuration_id"]):
            problems.append(f"{entry['path']}: identificadores distintos a los registrados")
        if [list(p) for p in scenario.victims] != entry["victims"]:
            problems.append(f"{entry['path']}: posiciones distintas a las registradas")
        template = templates.get(entry["building"])
        if template is None or not _same_building(template, scenario):
            problems.append(f"{entry['path']}: no conserva la geometría y el calor de su plantilla")

    observed = Counter((e["building"], e["partition"], e["difficulty"]) for e in entries)
    declared = {(b["key"], p, d.value): b["quotas"][p].get(d.value, 0)
                for b in config["buildings"] for p in PARTITIONS for d in Difficulty}
    for key in sorted(set(observed) | set(declared)):
        quota, actual = declared.get(key, 0), observed.get(key, 0)
        if actual != quota:
            problems.append(f"{'/'.join(key)}: {actual} configuraciones para cuota {quota}")
    if len(manifest["test"]) < config.get("min_test_total", 0):
        problems.append("La prueba tiene menos configuraciones que el mínimo declarado")

    witnesses_path = root / manifest["witnesses_file"]
    if not witnesses_path.exists():
        problems.append("Falta el archivo de testigos")
    elif file_sha256(witnesses_path) != manifest["witnesses_sha256"]:
        problems.append("El archivo de testigos cambió después de congelar")
    elif replay_witnesses:
        witnesses = [json.loads(line) for line in
                     witnesses_path.read_text(encoding="utf-8").splitlines() if line]
        by_configuration = {w["configuration_id"]: w for w in witnesses}
        for entry in entries:
            witness = by_configuration.get(entry["configuration_id"])
            scenario = loaded.get(entry["configuration_id"])
            if witness is None:
                problems.append(f"{entry['path']}: sin testigo de viabilidad")
                continue
            if scenario is None:
                continue
            try:
                certificate = ViabilityCertificate(
                    strategy=witness["strategy"], scenario_id=witness["scenario_id"],
                    configuration_id=witness["configuration_id"], steps=witness["steps"],
                    rescued=witness["rescued"], damage_total=witness["damage_total"],
                    final_integrities=tuple(witness["final_integrities"]),
                    actions=tuple(witness["actions"]), outcome=witness["outcome"])
                replay_certificate(scenario, certificate)
            except ValueError as error:
                problems.append(f"{entry['path']}: testigo inválido ({error})")
    return problems


def check_training_configs(manifest_path: str | Path, config_paths) -> list[str]:
    """Impide que un entrenamiento use validación o prueba de este manifiesto.

    Las etapas solo pueden usar entrenamiento. Los escenarios de evaluación
    durante el entrenamiento (selección de checkpoints) no pueden usar prueba.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    held_out = set(manifest["validation"]) | set(manifest["test"])
    test = set(manifest["test"])
    problems = []
    for path in config_paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        stages = {s for stage in data.get("stages", []) for s in stage.get("scenarios", [])}
        evaluation = set(data.get("evaluation_scenarios", []))
        if stages & held_out:
            problems.append(f"{Path(path).name}: entrena con validación o prueba")
        if evaluation & test:
            problems.append(f"{Path(path).name}: selecciona checkpoints con prueba")
    return problems


def distribution(manifest: dict, root: str | Path) -> list[dict]:
    """Resumen por partición y edificio derivado del manifiesto congelado."""
    root = Path(root)
    templates = {b["key"]: Scenario.load(root / b["template"])
                 for b in manifest["config"]["buildings"]}
    rows = []
    for partition in PARTITIONS:
        for building in manifest["config"]["buildings"]:
            key = building["key"]
            group = [e for e in manifest["entries"]
                     if (e["partition"], e["building"]) == (partition, key)]
            if not group:
                continue
            template = templates[key]
            maximum = template.width + template.height - 2
            distances, hot = [], []
            for entry in group:
                victims = [tuple(p) for p in entry["victims"]]
                distances.append(sum(abs(x - template.base[0]) + abs(y - template.base[1])
                                     for x, y in victims) / (len(victims) * maximum))
                hot.append(sum(template.temperature_at(p) >= 40 for p in victims))
            difficulty = Counter(e["difficulty"] for e in group)
            strategy = Counter(e["witness"]["strategy"] for e in group)
            rows.append({
                "partition": partition, "building": key, "count": len(group),
                **{d.value: difficulty.get(d.value, 0) for d in Difficulty},
                "mean_distance_ratio": round(sum(distances) / len(group), 3),
                "victims_in_heat": sum(hot),
                "witness_thermal": strategy.get("thermal", 0),
                "witness_shortest": strategy.get("shortest", 0),
                "mean_witness_steps": round(sum(e["witness"]["steps"] for e in group) / len(group), 1),
                "mean_witness_damage": round(
                    sum(e["witness"]["damage_total"] for e in group) / len(group), 1),
            })
    return rows
