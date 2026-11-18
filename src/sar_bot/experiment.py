"""Comparación unificada de DQN y referencias con métricas trazables (SARB-020).

Cada episodio parte de un ``RescueEnv`` y una política nuevos sobre el mismo
``Scenario`` congelado. Las métricas se calculan exclusivamente a partir de la
secuencia de estados del motor, y la secuencia de acciones se conserva para
poder reproducir y comprobar cada fila sin volver a entrenar.

Semillas que no deben confundirse:

- ``generation_seed``: generó las posiciones del escenario (manifiesto de particiones).
- ``training_seed``: semilla del entrenamiento del modelo DQN (metadatos del modelo).
- ``random_seed``: semilla de acciones de la referencia aleatoria.
"""

from __future__ import annotations

from collections import defaultdict
import csv
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

from sar_bot.core import MissionState, RescueSimulation, Scenario
from sar_bot.partitions import canonical_sha256, file_sha256, verify_manifest

STRATEGIES = ("dqn", "shortest", "thermal", "random")
DETERMINISTIC = ("shortest", "thermal")
WAIT = 4
RESULTS_SCHEMA = 1

COLUMNS = (
    "episode_id", "partition", "manifest_id", "scenario_path", "scenario_name",
    "building", "difficulty", "scenario_id", "configuration_id", "scenario_sha256",
    "width", "height", "generation_seed",
    "strategy", "model_label", "model_sha256", "training_seed", "random_seed",
    "thermal_damage_weight",
    "victims_total", "rescued", "success", "outcome", "steps", "max_steps",
    "damage_robot_1", "damage_robot_2", "damage_total",
    "integrity_robot_1", "integrity_robot_2",
    "deliveries_robot_1", "deliveries_robot_2", "wait_actions", "blocked_moves",
    "planning_failures", "replans", "expanded_states",
    "return", "reward_config_sha256", "actions_sha256", "compute_seconds",
)
# Columnas que dependen del motor; deben coincidir al reproducir la traza.
TRACE_COLUMNS = (
    "victims_total", "rescued", "success", "outcome", "steps", "max_steps",
    "damage_robot_1", "damage_robot_2", "damage_total",
    "integrity_robot_1", "integrity_robot_2",
    "deliveries_robot_1", "deliveries_robot_2", "wait_actions", "blocked_moves",
)
# Única columna que varía entre ejecuciones idénticas.
NONDETERMINISTIC_COLUMNS = ("compute_seconds",)


@dataclass(frozen=True)
class EvaluationCase:
    scenario: Scenario
    partition: str
    scenario_path: str = ""
    scenario_sha256: str = ""
    manifest_id: str = ""
    building: str = ""
    difficulty: str = ""
    generation_seed: int | None = None


@dataclass(frozen=True)
class LoadedModel:
    label: str
    path: str
    sha256: str
    training_seed: int | None
    reward_config: dict | None
    model: object


def cases_from_manifest(manifest_path: str | Path, split: str, root: str | Path, *,
                        allow_test: bool = False) -> list[EvaluationCase]:
    """Casos de una partición congelada; la prueba exige confirmación explícita."""
    root = Path(root)
    if split == "test" and not allow_test:
        raise PermissionError("La prueba final solo se abre con modelos congelados (SARB-021)")
    problems = verify_manifest(manifest_path, root, replay_witnesses=False)
    if problems:
        raise ValueError("El manifiesto no está íntegro: " + "; ".join(problems[:3]))
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    seeds = {g["building"]: g["generation_seed"] for g in manifest["generation"]}
    return [EvaluationCase(
        scenario=Scenario.load(root / e["path"]), partition=split, scenario_path=e["path"],
        scenario_sha256=e["sha256"], manifest_id=manifest["manifest_id"],
        building=e["building"], difficulty=e["difficulty"],
        generation_seed=seeds.get(e["building"]),
    ) for e in manifest["entries"] if e["partition"] == split]


def cases_from_paths(paths, root: str | Path, partition: str = "development") -> list[EvaluationCase]:
    if partition == "test":
        raise ValueError("Una lista libre de escenarios no puede declararse como prueba")
    root = Path(root)
    cases = []
    for path in paths:
        path = Path(path)
        absolute = path if path.is_absolute() else root / path
        try:
            label = absolute.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            label = absolute.as_posix()
        cases.append(EvaluationCase(Scenario.load(absolute), partition, label,
                                    file_sha256(absolute)))
    return cases


def load_model(path: str | Path, label: str | None = None,
               metadata_path: str | Path | None = None) -> LoadedModel:
    from stable_baselines3 import DQN
    import torch

    torch.set_num_threads(1)
    path = Path(path)
    metadata_path = Path(metadata_path) if metadata_path else path.parent / "metadata.json"
    metadata = (json.loads(metadata_path.read_text(encoding="utf-8"))
                if metadata_path.exists() else {})
    seed = metadata.get("config", {}).get("seed", metadata.get("seed"))
    digest = sha256(path.read_bytes()).hexdigest()
    model = DQN.load(path, device="cpu")
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("El modelo cambió durante la carga")
    return LoadedModel(label or path.parent.name, path.as_posix(), digest,
                       seed if type(seed) is int else None, metadata.get("rewards"), model)


def _robot_moved(before, after) -> bool:
    return before.position != after.position


def metrics_from_trace(scenario: Scenario, states: list[MissionState],
                       actions: list[int]) -> dict:
    """Métricas derivadas solo de estados consecutivos del motor."""
    if len(states) != len(actions) + 1:
        raise ValueError("La traza requiere un estado más que acciones")
    final = states[-1]
    deliveries = [0, 0]
    waits = blocked = 0
    for action, before, after in zip(actions, states, states[1:]):
        for index, robot_action in enumerate((action // 5, action % 5)):
            robot_before, robot_after = before.robots[index], after.robots[index]
            if robot_action == WAIT:
                waits += 1
            elif robot_before.integrity > 0 and not _robot_moved(robot_before, robot_after):
                blocked += 1
            carried = robot_before.carrying
            if (carried is not None and robot_after.carrying is None
                    and carried in after.rescued and carried not in before.rescued):
                deliveries[index] += 1
    return {
        "victims_total": scenario.victim_count,
        "rescued": len(final.rescued),
        "success": final.outcome == "success",
        "outcome": final.outcome,
        "steps": final.steps,
        "max_steps": scenario.max_steps,
        "damage_robot_1": final.robots[0].damage,
        "damage_robot_2": final.robots[1].damage,
        "damage_total": sum(robot.damage for robot in final.robots),
        "integrity_robot_1": final.robots[0].integrity,
        "integrity_robot_2": final.robots[1].integrity,
        "deliveries_robot_1": deliveries[0],
        "deliveries_robot_2": deliveries[1],
        "wait_actions": waits,
        "blocked_moves": blocked,
    }


def replay_actions(scenario: Scenario, actions) -> list[MissionState]:
    simulation = RescueSimulation(scenario)
    states = [simulation.state]
    for action in actions:
        if simulation.state.outcome != "running":
            raise ValueError("La traza contiene acciones después de finalizar")
        states.append(simulation.step(int(action)))
    return states


def actions_sha256(actions) -> str:
    return sha256(",".join(str(int(a)) for a in actions).encode()).hexdigest()


def episode_id(case: EvaluationCase, strategy: str, model: LoadedModel | None,
               random_seed: int | None, thermal_damage_weight: float) -> str:
    return canonical_sha256({
        "configuration_id": case.scenario.configuration_id, "strategy": strategy,
        "model": model.sha256 if model else None, "random_seed": random_seed,
        "thermal_damage_weight": thermal_damage_weight if strategy == "thermal" else None,
    })[:16]


def run_episode(case: EvaluationCase, strategy: str, *, model: LoadedModel | None = None,
                random_seed: int | None = None, rewards=None,
                thermal_damage_weight: float = 2.0) -> tuple[dict, list[int]]:
    """Un episodio limpio: entorno, simulación y política nuevos."""
    from sar_bot.agents import create_policy
    from sar_bot.env import RescueEnv, RewardConfig
    from sar_bot.learning import observation_mode_for_model

    if strategy not in STRATEGIES:
        raise ValueError(f"Estrategia desconocida: {strategy}")
    if (strategy == "dqn") != (model is not None):
        raise ValueError("Solo la estrategia DQN recibe un modelo")
    if (strategy == "random") != (random_seed is not None):
        raise ValueError("Solo la referencia aleatoria recibe semilla de acciones")
    rewards = rewards or RewardConfig()
    mode = observation_mode_for_model(model.model, case.scenario) if model else "full"
    env = RescueEnv([case.scenario], rewards, observation_mode=mode)
    env.reset(seed=0, options={"scenario_index": 0})
    simulation = env.simulation
    if simulation.scenario.configuration_id != case.scenario.configuration_id:
        raise ValueError("El entorno no recibió la configuración congelada")
    policy = None if model else create_policy(
        simulation, strategy, seed=random_seed if random_seed is not None else 0,
        thermal_damage_weight=thermal_damage_weight)
    states, actions = [simulation.state], []
    episode_return = 0.0
    planning_failures = 0
    started = perf_counter()
    while simulation.state.outcome == "running":
        if model:
            action, _ = model.model.predict(env.observation(), deterministic=True)
            action = int(action)
        else:
            action = int(policy.act(simulation.state))
            planning_failures += int(not getattr(policy, "last_plan_found", True))
        _, reward, _, _, _ = env.step(action)
        episode_return += reward
        actions.append(action)
        states.append(simulation.state)
    elapsed = perf_counter() - started
    env.close()

    scenario = case.scenario
    row = {
        "episode_id": episode_id(case, strategy, model, random_seed, thermal_damage_weight),
        "partition": case.partition,
        "manifest_id": case.manifest_id,
        "scenario_path": case.scenario_path,
        "scenario_name": scenario.name,
        "building": case.building,
        "difficulty": case.difficulty,
        "scenario_id": scenario.scenario_id,
        "configuration_id": scenario.configuration_id,
        "scenario_sha256": case.scenario_sha256,
        "width": scenario.width,
        "height": scenario.height,
        "generation_seed": case.generation_seed,
        "strategy": strategy,
        "model_label": model.label if model else "",
        "model_sha256": model.sha256 if model else "",
        "training_seed": model.training_seed if model else None,
        "random_seed": random_seed,
        "thermal_damage_weight": thermal_damage_weight if strategy == "thermal" else None,
        **metrics_from_trace(scenario, states, actions),
        "planning_failures": planning_failures,
        "replans": getattr(policy, "replans", 0) if policy else 0,
        "expanded_states": getattr(policy, "total_expanded", 0) if policy else 0,
        "return": round(episode_return, 6),
        "reward_config_sha256": canonical_sha256(vars(rewards)),
        "actions_sha256": actions_sha256(actions),
        "compute_seconds": round(elapsed, 4),
    }
    return row, actions


def evaluate_cases(cases, *, models=(), strategies=STRATEGIES, random_seeds=(0, 1, 2, 3, 4),
                   rewards=None, thermal_damage_weight: float = 2.0):
    """Ejecuta todas las estrategias sobre los mismos casos de un único perfil."""
    cases = list(cases)
    if not cases:
        raise ValueError("Se requiere al menos un caso")
    profiles = {(c.scenario.width, c.scenario.height, c.scenario.victim_count) for c in cases}
    if len(profiles) != 1:
        raise ValueError("No se mezclan perfiles distintos en una misma evaluación")
    unknown = set(strategies) - set(STRATEGIES)
    if unknown:
        raise ValueError(f"Estrategias desconocidas: {sorted(unknown)}")
    if "dqn" in strategies and not models:
        raise ValueError("La estrategia DQN requiere al menos un modelo")
    if "random" in strategies and not random_seeds:
        raise ValueError("La referencia aleatoria requiere semillas de acciones")
    if len({m.sha256 for m in models}) != len(models):
        raise ValueError("Hay modelos repetidos")
    if "dqn" in strategies:
        from sar_bot.learning import observation_mode_for_model
        for model in models:
            observation_mode_for_model(model.model, cases[0].scenario)

    rows, traces = [], []
    for case in cases:
        for strategy in strategies:
            if strategy == "dqn":
                runs = [{"model": model} for model in models]
            elif strategy == "random":
                runs = [{"random_seed": seed} for seed in random_seeds]
            else:
                runs = [{}]
            for run in runs:
                row, actions = run_episode(case, strategy, rewards=rewards,
                                           thermal_damage_weight=thermal_damage_weight, **run)
                rows.append(row)
                traces.append({"episode_id": row["episode_id"],
                               "configuration_id": row["configuration_id"],
                               "strategy": strategy, "actions": actions})
    ids = [row["episode_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Episodios repetidos en la evaluación")
    return rows, traces


def _cell(value) -> str:
    return "" if value is None else str(value)


def write_results(rows, traces, output: str | Path, metadata: dict) -> dict:
    """CSV con columnas fijas, trazas JSONL y metadatos con sus hashes."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    traces_path = output.with_suffix(".traces.jsonl")
    metadata_path = output.with_suffix(".metadata.json")
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow([_cell(row[column]) for column in COLUMNS])
    with traces_path.open("w", encoding="utf-8", newline="\n") as stream:
        for trace in traces:
            stream.write(json.dumps(trace, separators=(",", ":")) + "\n")
    metadata = {
        "schema_version": RESULTS_SCHEMA,
        **metadata,
        "columns": list(COLUMNS),
        "episodes": len(rows),
        "configurations": len({row["configuration_id"] for row in rows}),
        "csv": output.name,
        "csv_sha256": file_sha256(output),
        "traces": traces_path.name,
        "traces_sha256": file_sha256(traces_path),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8", newline="\n")
    return metadata


def read_results(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def verify_results(csv_path: str | Path, root: str | Path) -> list[str]:
    """Reproduce cada traza en un motor nuevo y compara las métricas del CSV."""
    csv_path, root = Path(csv_path), Path(root)
    problems = []
    metadata_path = csv_path.with_suffix(".metadata.json")
    traces_path = csv_path.with_suffix(".traces.jsonl")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if file_sha256(csv_path) != metadata["csv_sha256"]:
        problems.append("El CSV cambió después de escribirse")
    if file_sha256(traces_path) != metadata["traces_sha256"]:
        problems.append("Las trazas cambiaron después de escribirse")
    rows = read_results(csv_path)
    if rows and tuple(rows[0].keys()) != COLUMNS:
        problems.append("Las columnas no coinciden con el diccionario")
    traces = {}
    for line in traces_path.read_text(encoding="utf-8").splitlines():
        if line:
            trace = json.loads(line)
            traces[trace["episode_id"]] = trace
    scenarios = {}
    for row in rows:
        trace = traces.get(row["episode_id"])
        if trace is None:
            problems.append(f"{row['episode_id']}: sin traza")
            continue
        if actions_sha256(trace["actions"]) != row["actions_sha256"]:
            problems.append(f"{row['episode_id']}: hash de acciones distinto")
        key = row["scenario_path"]
        if key not in scenarios:
            scenarios[key] = Scenario.load(root / key)
        scenario = scenarios[key]
        if scenario.configuration_id != row["configuration_id"]:
            problems.append(f"{row['episode_id']}: el escenario no corresponde a la fila")
            continue
        try:
            states = replay_actions(scenario, trace["actions"])
        except ValueError as error:
            problems.append(f"{row['episode_id']}: {error}")
            continue
        replayed = metrics_from_trace(scenario, states, trace["actions"])
        for column in TRACE_COLUMNS:
            if _cell(replayed[column]) != row[column]:
                problems.append(f"{row['episode_id']}: {column}={row[column]} pero la traza da "
                                f"{replayed[column]}")
    return problems


def _number(row, column) -> float:
    value = row[column]
    return float(value) if isinstance(value, str) else value


def _success(row) -> bool:
    value = row["success"]
    return value == "True" if isinstance(value, str) else bool(value)


def summarize(rows, keys=("strategy", "model_label")) -> list[dict]:
    """Agregado con denominadores explícitos; daño y pasos solo entre éxitos."""
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in keys)].append(row)
    summary = []
    for key, group in sorted(groups.items(), key=lambda item: tuple(map(str, item[0]))):
        successes = [row for row in group if _success(row)]
        summary.append({
            **dict(zip(keys, key)),
            "episodes": len(group),
            "configurations": len({row["configuration_id"] for row in group}),
            "successes": len(successes),
            "rescued": int(sum(_number(row, "rescued") for row in group)),
            "victims": int(sum(_number(row, "victims_total") for row in group)),
            "mean_steps_success": (round(sum(_number(r, "steps") for r in successes)
                                         / len(successes), 1) if successes else None),
            "mean_damage_success": (round(sum(_number(r, "damage_total") for r in successes)
                                          / len(successes), 1) if successes else None),
            "destroyed": sum(1 for row in group if row["outcome"] == "destroyed"),
            "time_limit": sum(1 for row in group if row["outcome"] == "time_limit"),
        })
    return summary
