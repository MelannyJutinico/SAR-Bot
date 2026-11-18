"""Trazas locales versionadas. No importa politicas, aprendizaje ni Pygame."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys
from uuid import uuid4
from sar_bot.core import RescueSimulation, Scenario
from .playback import Episode
from .local_files import atomic_text
from .resources import MAX_FILE_BYTES, MAX_EPISODE_STATES, check_ui_limits

MAX_STATES = MAX_EPISODE_STATES
MAX_BYTES = MAX_FILE_BYTES


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def engine_hash():
    return sha256(Path(sys.modules[RescueSimulation.__module__].__file__).read_bytes()).hexdigest()


def state_data(state):
    return {"robots": [{"position": list(r.position), "integrity": r.integrity,
                        "carrying": r.carrying, "damage": r.damage} for r in state.robots],
            "rescued": sorted(state.rescued), "steps": state.steps, "outcome": state.outcome}


@dataclass(frozen=True)
class TraceEvent:
    step: int
    kind: str
    robot: int | None = None
    value: int | str | None = None


def derive_events(episode):
    events = [TraceEvent(0, "inicio")]
    for before, after in zip(episode.states, episode.states[1:]):
        for i, (old, new) in enumerate(zip(before.robots, after.robots), 1):
            if old.position != new.position:
                events.append(TraceEvent(after.steps, "movimiento", i, str(new.position)))
            if new.carrying is not None and old.carrying != new.carrying:
                events.append(TraceEvent(after.steps, "recogida", i, new.carrying))
            if new.damage > old.damage:
                events.append(TraceEvent(after.steps, "dano", i, new.damage - old.damage))
            if old.integrity > 0 and new.integrity == 0:
                events.append(TraceEvent(after.steps, "destruccion", i))
        for victim in sorted(after.rescued - before.rescued):
            carrier = next((i for i,r in enumerate(before.robots,1) if r.carrying == victim), None)
            events.append(TraceEvent(after.steps, "entrega", carrier, victim))
        if before.outcome == "running" and after.outcome != "running":
            if after.outcome == "success":
                events.append(TraceEvent(after.steps, "rescate_completado"))
            events.append(TraceEvent(after.steps, "finalizacion", value=after.outcome))
    return tuple(events)


@dataclass(frozen=True)
class TraceRecord:
    record_id: str
    episode: Episode
    strategy: str
    model: str | None
    seed: int
    events: tuple[TraceEvent, ...]
    python_version: str

    @property
    def metrics(self):
        state = self.episode.states[-1]
        return {"outcome": state.outcome, "rescued": len(state.rescued), "steps": state.steps,
                "damage_total": sum(r.damage for r in state.robots),
                "damage_by_robot": [r.damage for r in state.robots]}

    def payload(self):
        from dataclasses import asdict
        return {"format": "sar-bot-ui-trace", "version": 1, "record_id": self.record_id,
                "scenario": self.episode.scenario.to_dict(), "strategy": self.strategy,
                "model": self.model, "seed": self.seed,
                "checkpoint_sha256": self.episode.checkpoint_sha256,
                "engine_sha256": self.episode.engine_sha256,
                "versions": {"python": self.python_version, "scenario_schema": 2, "trace_schema": 1},
                "actions": list(self.episode.actions), "states": [state_data(s) for s in self.episode.states],
                "metrics": self.metrics, "events": [asdict(e) for e in self.events]}


def make_record(episode, strategy, model, seed):
    if not 2 <= len(episode.states) <= MAX_STATES or len(episode.actions) + 1 != len(episode.states):
        raise ValueError("La traza debe estar completa y tener como maximo 5000 estados")
    if episode.states[-1].outcome == "running":
        raise ValueError("La mision no esta finalizada")
    if strategy not in ("dqn", "shortest", "thermal", "random") or type(seed) is not int:
        raise ValueError("Metadatos de estrategia o semilla invalidos")
    # No atribuir un hash actual a una ejecucion que no lo registro.
    return TraceRecord(uuid4().hex, episode, strategy, str(model) if model else None,
                       seed, derive_events(episode), platform.python_version())


def export_trace(record, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    data = record.payload()
    data["trace_sha256"] = sha256(canonical(data).encode()).hexdigest()
    path = directory / ("trace-" + uuid4().hex + ".json")
    text = canonical(data)
    if len(text.encode()) > MAX_BYTES:
        raise ValueError("Traza demasiado grande para el formato local")
    def validate(temporary):
        written = json.loads(temporary.read_text(encoding="utf-8"))
        if canonical(written) != text:
            raise ValueError("La escritura de la traza no coincide con sus datos")
    with atomic_text(path, validate) as stream:
        stream.write(text)
    return path


def load_trace(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("La traza supera 16 MiB")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("La traza supera 16 MiB")
    data = json.loads(raw)
    if data.get("format") != "sar-bot-ui-trace" or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("Formato o version de traza incompatible")
    signature = data.pop("trace_sha256", None)
    if signature != sha256(canonical(data).encode()).hexdigest():
        raise ValueError("El hash de la traza no coincide")
    if data["engine_sha256"] != engine_hash():
        raise ValueError("La traza requiere otra version del motor")
    if not 2 <= len(data["states"]) <= MAX_STATES or len(data["actions"]) + 1 != len(data["states"]):
        raise ValueError("Longitud de traza invalida")
    if any(type(data["scenario"][key]) is not int or not 1 <= data["scenario"][key] <= 24 for key in ("width", "height")):
        raise ValueError("Dimensiones incompatibles con la interfaz")
    if data["versions"].get("trace_schema") != 1 or data["versions"].get("scenario_schema") != 2:
        raise ValueError("Versiones de contrato incompatibles")
    check_ui_limits(data["scenario"])
    scenario = Scenario.from_dict(data["scenario"])
    simulation = RescueSimulation(scenario)
    states = [simulation.state]
    for action in data["actions"]:
        if simulation.state.outcome != "running":
            raise ValueError("Hay acciones despues de finalizar")
        states.append(simulation.step(action))
    if canonical([state_data(s) for s in states]) != canonical(data["states"]):
        raise ValueError("Los estados no corresponden a las acciones del motor")
    model_hash = data["checkpoint_sha256"]
    if model_hash is not None and (not isinstance(model_hash,str) or len(model_hash) != 64 or any(c not in "0123456789abcdef" for c in model_hash)):
        raise ValueError("Hash del checkpoint invalido")
    episode = Episode(scenario, tuple(states), tuple(data["actions"]), model_hash, data["engine_sha256"])
    candidate = make_record(episode, data["strategy"], data["model"], data["seed"])
    from dataclasses import replace, asdict
    if candidate.metrics != data["metrics"] or canonical([asdict(e) for e in candidate.events]) != canonical(data["events"]):
        raise ValueError("Eventos o metricas incompatibles con la traza")
    return replace(candidate, record_id=str(data["record_id"]), python_version=data["versions"]["python"])


class History:
    """20 registros / 10000 estados; expulsar primero el mas antiguo, sin borrar archivos."""
    def __init__(self):
        self.records = []
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.pending = []
        self.io = None
        self.token = 0
        self.closed = False
        self.message = ""

    def add(self, record):
        if any(r.record_id == record.record_id for r in self.records):
            return
        self.records.append(record)
        while len(self.records) > 20 or sum(len(r.episode.states) for r in self.records) > 10000:
            self.records.pop(0)

    def record(self, episode, strategy, model, seed):
        if self.closed:
            return
        if len(self.pending) >= 16 or len(episode.states) > MAX_STATES:
            self.message = "Limite del historial: exporta las misiones antes de continuar."
            return
        self.pending.append(self.executor.submit(make_record, episode, strategy, model, seed))

    def invalidate_io(self):
        self.token += 1
        if self.io:
            self.io[0].cancel()
        self.io = None

    def start_io(self, operation, argument, directory):
        self.invalidate_io()
        self.message = "Procesando traza en segundo plano..."
        if operation == "export":
            fn, args = export_trace, (argument, directory)
        elif operation == "list":
            fn, args = list_traces, (directory,)
        else:
            if Path(argument).name != argument or Path(argument).suffix != ".json":
                raise ValueError("Selecciona un JSON del directorio de trazas")
            fn, args = load_trace, (Path(directory) / argument,)
        self.io = (self.executor.submit(fn, *args), self.token, operation)

    def poll(self):
        if self.closed:
            return None
        for future in tuple(self.pending):
            if future.done():
                self.pending.remove(future)
                try: self.add(future.result())
                except Exception as error: self.message = "No se registro la traza: " + str(error)
        if not self.io or not self.io[0].done():
            return None
        future, token, operation = self.io
        self.io = None
        if token != self.token:
            return None
        try:
            result = future.result()
            if operation == "load": self.add(result)
            self.message = "Traza cargada." if operation == "load" else "Operacion completada."
            return operation, result
        except Exception as error:
            self.message = "Traza no disponible o invalida: " + str(error)[:140]
            return None

    def close(self):
        self.closed = True
        self.invalidate_io()
        for future in self.pending: future.cancel()
        self.executor.shutdown(wait=False, cancel_futures=True)


def list_traces(directory):
    directory = Path(directory)
    return tuple(sorted(p.name for p in directory.glob("trace-*.json"))) if directory.exists() else ()
