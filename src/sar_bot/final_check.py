"""Comprobación previa a la evaluación final reservada (SARB-021).

Antes de abrir la partición de prueba se comprueba que los modelos congelados
cumplen el protocolo de ``docs/PARTICIONES_V2.md``:

- hay al menos tres semillas de entrenamiento distintas y modelos distintos;
- cada modelo tiene el perfil del manifiesto (ancho, alto y personas);
- ninguna etapa de entrenamiento usó casos de validación o de prueba;
- el checkpoint se eligió solo con casos de validación;
- los escenarios usados al entrenar no cambiaron desde entonces;
- la prueba no se evaluó antes con esos modelos.

La comprobación lee metadatos y archivos; no carga pesos ni ejecuta misiones.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from sar_bot.core import Scenario

MIN_SEEDS = 3


def _digests(path: Path) -> set[str]:
    """Hashes aceptados para un archivo de texto, con finales de línea LF o CRLF."""
    raw = path.read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    return {sha256(raw).hexdigest(), sha256(lf).hexdigest(),
            sha256(lf.replace(b"\n", b"\r\n")).hexdigest()}


def _scenario_ids(paths, root: Path) -> dict[str, str]:
    return {path: Scenario.load(root / path).scenario_id for path in paths}


def check_final_models(manifest_path: str | Path, model_paths, root: str | Path, *,
                       min_seeds: int = MIN_SEEDS) -> list[str]:
    """Problemas que impiden abrir la prueba con estos modelos; vacío si todo cumple."""
    root = Path(root)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    partition_ids = {name: set(_scenario_ids(manifest[name], root).values())
                     for name in ("training", "validation", "test")}
    reserved = partition_ids["validation"] | partition_ids["test"]
    profile = manifest["profile"]
    problems = []
    model_paths = [Path(p) for p in model_paths]
    if len(model_paths) < min_seeds:
        problems.append(f"Se necesitan al menos {min_seeds} modelos congelados (uno por semilla); "
                        f"se indicaron {len(model_paths)}")
    seeds, hashes = {}, {}
    for model in model_paths:
        label = model.parent.name
        if not model.is_file():
            problems.append(f"{label}: no existe {model.name}")
            continue
        digest = sha256(model.read_bytes()).hexdigest()
        if digest in hashes:
            problems.append(f"{label}: es el mismo archivo que {hashes[digest]}")
        hashes[digest] = label
        metadata_path = model.parent / "metadata.json"
        if not metadata_path.is_file():
            problems.append(f"{label}: falta metadata.json")
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        config = metadata.get("config", {})
        seed = config.get("seed")
        if type(seed) is not int:
            problems.append(f"{label}: no registra una semilla de entrenamiento entera")
        elif seed in seeds:
            problems.append(f"{label}: repite la semilla {seed} de {seeds[seed]}")
        else:
            seeds[seed] = label
        observed = metadata.get("observation_profile") or {}
        if (observed.get("width"), observed.get("height"), observed.get("victims")) != (
                profile["width"], profile["height"], profile["victims"]):
            problems.append(f"{label}: perfil {observed.get('width')}×{observed.get('height')} "
                            f"con {observed.get('victims')} personas; el manifiesto es "
                            f"{profile['width']}×{profile['height']} con {profile['victims']}")
            continue
        trained = [p for stage in config.get("stages", []) for p in stage.get("scenarios", [])]
        if not trained:
            problems.append(f"{label}: no registra escenarios de entrenamiento")
        for path, scenario_id in _scenario_ids(sorted(set(trained)), root).items():
            if scenario_id in reserved:
                problems.append(f"{label}: entrenó con {path}, que es de validación o prueba")
        selection = config.get("evaluation_scenarios", [])
        if not selection:
            problems.append(f"{label}: no registra los escenarios con que eligió el checkpoint")
        for path, scenario_id in _scenario_ids(sorted(set(selection)), root).items():
            if scenario_id in partition_ids["test"]:
                problems.append(f"{label}: eligió el checkpoint con {path}, que es de prueba")
            elif scenario_id not in partition_ids["validation"]:
                problems.append(f"{label}: eligió el checkpoint con {path}, que no es de validación")
        for path, digest in sorted(metadata.get("scenario_hashes", {}).items()):
            if not (root / path).is_file():
                problems.append(f"{label}: falta {path}, usado al entrenar")
            elif digest not in _digests(root / path):
                problems.append(f"{label}: {path} cambió después del entrenamiento")
        if metadata.get("training_method") == "imitation pretraining plus DQN reinforcement":
            demonstration = metadata.get("demonstrations", {})
            trace_path = model.parent / "demonstrations.jsonl"
            if demonstration.get("partition") != "training" or not trace_path.is_file():
                problems.append(f"{label}: faltan demostraciones exclusivas de entrenamiento")
            elif demonstration.get("sha256") not in _digests(trace_path):
                problems.append(f"{label}: las demostraciones cambiaron")
            else:
                traces = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line]
                if (len(traces) != demonstration.get("cases") or any(
                        t.get("scenario_id") not in partition_ids["training"] or t.get("outcome") != "success"
                        for t in traces)):
                    problems.append(f"{label}: demostraciones fuera de entrenamiento o incompletas")
            try:
                with ZipFile(model) as archive:
                    steps = json.loads(archive.read("data"))["num_timesteps"]
                minimum = config["pretraining"]["minimum_rl_steps"]
                if steps < minimum:
                    problems.append(f"{label}: el checkpoint no tiene el refinamiento RL minimo")
            except (OSError, ValueError, KeyError, BadZipFile):
                problems.append(f"{label}: no se verifica el refinamiento por refuerzo")
        for name in ("test.csv", "test.metadata.json"):
            if (model.parent / name).exists():
                problems.append(f"{label}: ya existe {name}; la prueba no puede abrirse dos veces")
    return problems
