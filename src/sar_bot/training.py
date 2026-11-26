"""Configuración del entrenamiento independiente de librerías de aprendizaje."""

from dataclasses import dataclass
from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path


def resolve_training_config(config, root, pilot_steps=None):
    """Expande el currículo desde un manifiesto y rechaza fuga física de datos.

    Conserva las rutas explícitas en la configuración efectiva para que el
    evaluador final y los artefactos existentes puedan verificar procedencia.
    No evalúa ni incorpora experiencias de la partición de prueba.
    """
    from sar_bot.core import Scenario
    from sar_bot.partitions import verify_manifest

    effective = deepcopy(config)
    root = Path(root)
    partition = None
    if pilot_steps is not None:
        if type(pilot_steps) is not int or pilot_steps < 1:
            raise ValueError("Los pasos del piloto deben ser un entero positivo")
        effective["pilot_steps_per_stage"] = pilot_steps
    if effective.get("partition_manifest"):
        path = root / effective["partition_manifest"]
        problems = verify_manifest(path, root, replay_witnesses=False)
        if problems:
            raise ValueError("Manifiesto inválido: " + "; ".join(problems[:5]))
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for stage in effective["stages"]:
            selector = stage.pop("training_filter", {})
            if selector and "scenarios" in stage:
                raise ValueError("Usar training_filter o scenarios, no ambos")
            if "scenarios" not in stage:
                difficulties = selector.get("difficulties", ["easy", "intermediate", "demanding"])
                if not difficulties or set(difficulties) - {"easy", "intermediate", "demanding"}:
                    raise ValueError("Familias de dificultad inválidas")
                limit = selector.get("limit_per_building")
                if limit is not None and (type(limit) is not int or limit < 1):
                    raise ValueError("limit_per_building debe ser un entero positivo")
                counts, paths = {}, []
                for entry in manifest["entries"]:
                    if entry["partition"] != "training" or entry["difficulty"] not in difficulties:
                        continue
                    building = entry["building"]
                    if limit is None or counts.get(building, 0) < limit:
                        paths.append(entry["path"])
                        counts[building] = counts.get(building, 0) + 1
                stage["scenarios"] = paths
            if not stage["scenarios"]:
                raise ValueError("El currículo contiene una etapa sin escenarios")
        effective.setdefault("evaluation_scenarios", manifest["validation"])
        # Se compara identidad física: renombrar/copiar un JSON no evita el control.
        allowed_train = {entry["scenario_id"] for entry in manifest["entries"]
                         if entry["partition"] == "training"}
        allowed_validation = {entry["scenario_id"] for entry in manifest["entries"]
                              if entry["partition"] == "validation"}
        for stage in effective["stages"]:
            if any(Scenario.load(root / p).scenario_id not in allowed_train for p in stage["scenarios"]):
                raise ValueError("Una etapa contiene casos ajenos a entrenamiento")
        if not effective["evaluation_scenarios"] or any(
                Scenario.load(root / p).scenario_id not in allowed_validation
                for p in effective["evaluation_scenarios"]):
            raise ValueError("La selección de checkpoints requiere casos de validación")
        partition = {"path": effective["partition_manifest"],
                     "manifest_id": manifest["manifest_id"],
                     "sha256": sha256(path.read_bytes()).hexdigest(),
                     "selection_split": "validation", "test_evaluated": False}
    for stage in effective["stages"]:
        if pilot_steps is not None:
            stage["steps"] = pilot_steps
    return effective, partition


@dataclass(frozen=True)
class StageExploration:
    """Traduce el progreso acumulado de SB3 a exploración local de una etapa.

    Con reset_num_timesteps=False, el progreso de SB3 incluye pasos anteriores.
    Cada nueva etapa puede necesitar explorar otra vez en lugar de continuar al 5%.
    """

    start_step: int
    steps: int
    initial: float = 0.6
    final: float = 0.05
    fraction: float = 0.8

    def __post_init__(self):
        if self.start_step < 0 or self.steps < 1:
            raise ValueError("El inicio debe ser no negativo y la duración positiva")
        if not all(isfinite(v) for v in (self.initial, self.final, self.fraction)):
            raise ValueError("Los parámetros de exploración deben ser finitos")
        if not 0 <= self.final <= self.initial <= 1 or not 0 < self.fraction <= 1:
            raise ValueError("Se requiere 0 <= final <= inicial <= 1 y 0 < fracción <= 1")

    def __call__(self, progress_remaining: float) -> float:
        cumulative_step = (self.start_step + self.steps) * (1 - progress_remaining)
        local_step = max(0.0, cumulative_step - self.start_step)
        progress = min(1.0, local_step / (self.steps * self.fraction))
        return self.initial + (self.final - self.initial) * progress
