"""Conjuntos de desarrollo con posiciones variables (SARB-031).

Un conjunto de desarrollo usa el mismo generador certificado que las
particiones (SARB-009), pero no es una partición experimental: sirve para
estudiar escala y dificultad con las referencias y para sondear modelos de
desarrollo. No se usa para entrenar, elegir checkpoints ni afirmar
generalización. Los archivos se escriben una sola vez y su registro guarda
hashes que se comprueban antes de evaluar.
"""

from __future__ import annotations

import json
from pathlib import Path

from sar_bot.core import Scenario
from sar_bot.core.generation import generate_configurations
from sar_bot.partitions import (
    _same_building,
    _scenario_text,
    _write_text,
    content_sha256,
    file_sha256,
)

DEVELOPMENT_SCHEMA = 1
DEVELOPMENT_PURPOSE = "development_study_not_experimental_partition"


def build_development_set(*, template_path: str, root: str | Path, set_id: str,
                          building: str, seed: int, requested: int, max_attempts: int,
                          scenario_dir: str, created_on: str) -> tuple[dict, dict]:
    """Genera el registro y los escenarios en memoria; no escribe nada."""
    root = Path(root)
    template = Scenario.load(root / template_path)
    excluded = {template.scenario_id}
    summary = generate_configurations(template, seed=seed, requested=requested + len(excluded),
                                      max_attempts=max_attempts)
    usable = [(index, item) for index, item in enumerate(summary.accepted)
              if item.scenario.scenario_id not in excluded]
    if len(usable) < requested:
        raise ValueError(f"Solo se certificaron {len(usable)} de {requested} casos; "
                         "aumentar max_attempts")
    scenarios, entries = {}, []
    for number, (index, item) in enumerate(usable[:requested], 1):
        name = f"{building}_dev_{number:02d}_{item.difficulty.value}"
        path = f"{scenario_dir.rstrip('/')}/{name}.json"
        scenario = item.scenario.with_victims(item.scenario.victims, name=name)
        certificate = item.viability.certificate
        scenarios[path] = scenario
        entries.append({
            "path": path, "building": building, "difficulty": item.difficulty.value,
            "generation_index": index, "victims": [list(p) for p in scenario.victims],
            "scenario_id": scenario.scenario_id, "configuration_id": scenario.configuration_id,
            "sha256": None,
            "witness": {"strategy": certificate.strategy, "steps": certificate.steps,
                        "damage_total": certificate.damage_total},
        })
    record = {
        "schema_version": DEVELOPMENT_SCHEMA,
        "set_id": set_id,
        "purpose": DEVELOPMENT_PURPOSE,
        "created_on": created_on,
        "profile": {"width": template.width, "height": template.height,
                    "victims": template.victim_count},
        "template": {"path": template_path, "sha256": file_sha256(root / template_path)},
        "building": building,
        "generation": {"seed": seed, "requested": requested, "max_attempts": max_attempts,
                       "attempts": summary.attempts, "certified": summary.accepted_count,
                       "not_certified": len(summary.not_certified),
                       "duplicates": summary.duplicates,
                       "structural_invalid": summary.structural_invalid},
        "excluded_scenario_ids": sorted(excluded),
        "entries": entries,
        "notes": [
            "Conjunto de desarrollo: no se usa para entrenar, elegir checkpoints ni afirmar "
            "generalización.",
            "Los casos entraron porque una referencia los resolvió al certificarlos.",
            "Se excluye la configuración de la plantilla.",
        ],
    }
    return record, scenarios


def write_development_set(record: dict, scenarios: dict, record_path: str | Path,
                          root: str | Path) -> Path:
    """Escribe escenarios y registro; nunca sobrescribe archivos existentes."""
    root = Path(root)
    record = json.loads(json.dumps(record))
    record_path = Path(record_path)
    record_path = record_path if record_path.is_absolute() else root / record_path
    targets = [root / path for path in scenarios] + [record_path]
    existing = [str(path) for path in targets if path.exists()]
    if existing:
        raise FileExistsError("El conjunto ya existe; usar otro set_id en vez de sobrescribir: "
                              f"{existing[:3]}")
    for entry in record["entries"]:
        path = root / entry["path"]
        _write_text(path, _scenario_text(scenarios[entry["path"]]))
        entry["sha256"] = file_sha256(path)
    record["content_sha256"] = content_sha256(record)
    _write_text(record_path, json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record_path


def verify_development_set(record_path: str | Path, root: str | Path) -> list[str]:
    """Comprueba hashes, identidades y que cada caso conserve el edificio de la plantilla."""
    root = Path(root)
    problems = []
    record = json.loads(Path(record_path).read_text(encoding="utf-8"))
    if record.get("purpose") != DEVELOPMENT_PURPOSE:
        return ["El archivo no es un conjunto de desarrollo"]
    if record.get("content_sha256") != content_sha256(record):
        problems.append("El registro cambió después de escribirse")
    template_path = root / record["template"]["path"]
    if file_sha256(template_path) != record["template"]["sha256"]:
        problems.append("La plantilla cambió")
    template = Scenario.load(template_path)
    seen = set()
    for entry in record["entries"]:
        path = root / entry["path"]
        if not path.is_file():
            problems.append(f"Falta {entry['path']}")
            continue
        if file_sha256(path) != entry["sha256"]:
            problems.append(f"{entry['path']}: hash distinto")
        scenario = Scenario.load(path)
        if (scenario.scenario_id, scenario.configuration_id) != (entry["scenario_id"],
                                                                 entry["configuration_id"]):
            problems.append(f"{entry['path']}: identidad distinta del registro")
        if [list(p) for p in scenario.victims] != entry["victims"]:
            problems.append(f"{entry['path']}: posiciones distintas del registro")
        if not _same_building(template, scenario):
            problems.append(f"{entry['path']}: no conserva el edificio de la plantilla")
        if scenario.scenario_id in seen:
            problems.append(f"{entry['path']}: caso repetido")
        if scenario.scenario_id in record["excluded_scenario_ids"]:
            problems.append(f"{entry['path']}: usa una configuración excluida")
        seen.add(scenario.scenario_id)
    return problems
