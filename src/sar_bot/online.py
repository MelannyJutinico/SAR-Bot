"""Aprendizaje entre misiones y checkpoints recuperables de sesiones locales.

Solo carga pesos y memoria creados localmente por SAR-Bot. La generación actual
se publica después de escribir y verificar modelo, replay, RNG y metadatos.
"""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import pickle
import random
import re
import shutil
from uuid import uuid4

import numpy as np
import torch
from stable_baselines3 import DQN
from stable_baselines3.common.logger import Logger

from sar_bot.core import RescueSimulation, Scenario
from sar_bot.env import RescueEnv, RewardConfig
from sar_bot.learning import observation_mode_for_model, evaluate_model, model_score


def guarded_update(model, scenarios, rewards, *, gradient_steps, batch_size):
    """Compara sobre controles de entrenamiento; nunca usa prueba ni garantiza generalización."""
    policy = deepcopy(model.policy.state_dict())
    optimizer = deepcopy(model.policy.optimizer.state_dict())
    updates = model._n_updates
    attempted = 0
    try:
        before = model_score(evaluate_model(model, scenarios, rewards))
        model.train(gradient_steps=gradient_steps, batch_size=batch_size)
        attempted = model._n_updates - updates
        after = model_score(evaluate_model(model, scenarios, rewards))
        accepted = (*after[:2], round(after[2], 6)) >= (*before[:2], round(before[2], 6))
        audit = {"accepted": accepted, "before": list(before), "after": list(after),
                 "control_ids": [s.scenario_id for s in scenarios],
                 "reason": "no_regression_on_controls" if accepted else "regression_on_controls"}
    except Exception as error:
        attempted = model._n_updates - updates
        accepted = False
        audit = {"accepted": False, "reason": "control_or_update_error", "error": str(error)[:180],
                 "control_ids": [s.scenario_id for s in scenarios]}
    if not accepted:
        model.policy.load_state_dict(policy)
        model.policy.optimizer.load_state_dict(optimizer)
        model._n_updates = updates
    return {**audit, "attempted_updates": attempted}


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, data):
    path = Path(path)
    temporary = path.with_name("." + path.name + "-" + uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def session_lock(directory):
    """El sistema operativo libera el bloqueo incluso si termina el proceso."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".writer.lock").open("a+b") as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError("La sesion esta en uso; espera a que termine su operacion") from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@dataclass(frozen=True)
class SessionSettings:
    capacity: int = 4096
    learning_rate: float = 0.00005
    exploration: float = 0.1
    max_updates: int = 64

    def __post_init__(self):
        if type(self.capacity) is not int or self.capacity < 8:
            raise ValueError("La memoria debe permitir al menos ocho experiencias")
        if type(self.max_updates) is not int or not 1 <= self.max_updates <= 256:
            raise ValueError("Presupuesto de actualizaciones invalido")
        if not math.isfinite(self.learning_rate) or not 0 < self.learning_rate <= 0.01:
            raise ValueError("Tasa de aprendizaje invalida")
        if not math.isfinite(self.exploration) or not 0 <= self.exploration <= 1:
            raise ValueError("Exploracion invalida")


@dataclass(frozen=True)
class FixedExploration:
    value: float

    def __call__(self, progress):
        return self.value


@dataclass(frozen=True)
class SessionSnapshot:
    model_path: Path
    metadata: dict
    generation: str | None = None
    recovered: bool = False


class LearningSession:
    """Una sesión por perfil/modelo base. Los archivos base nunca se modifican."""

    def __init__(self, directory, base_model, *, settings=None, protected_ids=(), control_scenarios=()):
        self.directory = Path(directory).resolve()
        self.base_model = Path(base_model).resolve()
        self.settings = settings or SessionSettings()
        self.protected_ids = frozenset(protected_ids)
        self.control_scenarios = tuple(control_scenarios)
        if any(s.scenario_id in self.protected_ids for s in self.control_scenarios):
            raise ValueError("Una prueba reservada no puede ser control de aprendizaje")
        self.base_hash = digest(self.base_model)
        data = json.loads((self.base_model.parent / "metadata.json").read_text(encoding="utf-8"))
        self.rewards = RewardConfig(**data.get("rewards", {}))
        self.masked = bool(data.get("config", {}).get("mask_invalid_actions", False))

    @classmethod
    def for_project(cls, root, base_model, scenario, *, settings=None):
        root, base_model = Path(root), Path(base_model)
        protected = set()
        controls = {}
        for path in (root / "configs/partitions").glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            protected.update(e["scenario_id"] for e in data.get("entries", []) if e["partition"] == "test")
            for entry in data.get("entries", []):
                if entry["partition"] != "training":
                    continue
                key = (entry.get("building"), entry.get("difficulty"))
                if key in controls:
                    continue
                source = (root / entry["path"]).resolve()
                if not source.is_relative_to(root.resolve()):
                    raise ValueError("Control de aprendizaje fuera del proyecto")
                candidate = Scenario.load(source)
                if candidate.scenario_id != entry["scenario_id"]:
                    raise ValueError("Control de aprendizaje alterado")
                if (candidate.width, candidate.height, candidate.victim_count) == (
                        scenario.width, scenario.height, scenario.victim_count):
                    controls[key] = candidate
        name = f"{scenario.width}x{scenario.height}-{scenario.victim_count}-{digest(base_model)[:12]}"
        metadata=json.loads(base_model.with_name("metadata.json").read_text(encoding="utf-8"))
        if metadata.get("controller")=="neural_assignment":
            from .assignment_learning import AssignmentLearningSession
            return AssignmentLearningSession(root / "outputs/learning_sessions" / name,base_model,
                settings=settings,protected_ids=protected,
                control_scenarios=tuple(controls.values())[:6] or (scenario,))
        return cls(root / "outputs/learning_sessions" / name, base_model,
                   settings=settings, protected_ids=protected,
                   control_scenarios=tuple(controls.values())[:6] or (scenario,))

    def _initial(self):
        return SessionSnapshot(self.base_model, {
            "schema_version": 1, "base_sha256": self.base_hash,
            "settings": asdict(self.settings), "rewards": asdict(self.rewards),
            "masked": self.masked, "missions": 0, "transitions": 0,
            "updates": 0, "processed_ids": [], "buffer_size": 0,
            "model_sha256": self.base_hash, "profile": None,
        })

    def _read_pointer(self, path):
        pointer = json.loads(path.read_text(encoding="utf-8"))
        generation = pointer["generation"]
        if not isinstance(generation, str) or not re.fullmatch(r"g-[0-9a-f]{32}", generation):
            raise ValueError("Generacion de sesion invalida")
        folder = self.directory / generation
        if folder.resolve().parent != self.directory or folder.is_symlink():
            raise ValueError("Generacion fuera de la sesion")
        if digest(folder / "metadata.json") != pointer["metadata_sha256"]:
            raise ValueError("Metadatos de sesion alterados")
        meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        if (meta["schema_version"] != 1 or meta["base_sha256"] != self.base_hash
                or meta["settings"] != asdict(self.settings) or meta["rewards"] != asdict(self.rewards)
                or meta["masked"] != self.masked):
            raise ValueError("La sesion no coincide con el modelo y configuracion")
        for name, expected in meta["file_hashes"].items():
            if name not in ("model.zip", "replay.pkl", "rng.pkl") or digest(folder / name) != expected:
                raise ValueError("Checkpoint de sesion incompleto o alterado")
        if set(meta["file_hashes"]) != {"model.zip", "replay.pkl", "rng.pkl"}:
            raise ValueError("Faltan archivos del checkpoint")
        return SessionSnapshot(folder / "model.zip", meta, generation)

    def _snapshot(self):
        failures = []
        for name in ("current.json", "previous.json"):
            pointer = self.directory / name
            if pointer.exists():
                try:
                    snapshot = self._read_pointer(pointer)
                    return SessionSnapshot(snapshot.model_path, snapshot.metadata, snapshot.generation, bool(failures))
                except (OSError, ValueError, KeyError, TypeError) as error:
                    failures.append(str(error))
        if failures:
            raise ValueError("No hay checkpoint recuperable: " + failures[0])
        return self._initial()

    def snapshot(self):
        with session_lock(self.directory):
            return self._snapshot()

    def _model(self, snapshot, scenario, *, replay=False):
        torch.set_num_threads(1)
        if self.masked:
            from sar_bot.agents.masked_dqn import MaskedDQN
            algorithm = MaskedDQN
        else:
            algorithm = DQN
        model = algorithm.load(snapshot.model_path, device="cpu", buffer_size=self.settings.capacity,
                               learning_rate=self.settings.learning_rate, learning_starts=0)
        mode = observation_mode_for_model(model, scenario)
        env = RescueEnv([scenario], self.rewards, observation_mode=mode)
        if snapshot.metadata["profile"] not in (None, env.profile):
            raise ValueError("Perfil de la sesion incompatible con esta mision")
        model.set_env(env)
        # DQN.load sin env no crea memoria; enlazarla conserva el optimizador cargado.
        if model.replay_buffer is None:
            from stable_baselines3.common.buffers import ReplayBuffer
            model.replay_buffer = ReplayBuffer(self.settings.capacity, env.observation_space,
                                              env.action_space, device="cpu", n_envs=1,
                                              handle_timeout_termination=True)
        model.sar_bot_profile = env.profile
        model.set_logger(Logger(folder=None, output_formats=[]))
        model.exploration_schedule = FixedExploration(self.settings.exploration)
        model.exploration_rate = self.settings.exploration
        if replay and snapshot.generation:
            model.load_replay_buffer(snapshot.model_path.parent / "replay.pkl")
            with (snapshot.model_path.parent / "rng.pkl").open("rb") as stream:
                rng = pickle.load(stream)
            random.setstate(rng["python"])
            np.random.set_state(rng["numpy"])
            torch.set_rng_state(rng["torch"])
        return model, env

    def _check_scenario(self, scenario):
        if scenario.scenario_id in self.protected_ids:
            raise ValueError("Esta ubicacion pertenece a prueba reservada; usa Evaluar o cambia las posiciones")

    def prepare_episode(self, scenario, seed=0, cancel_event=None):
        from sar_bot.ui.playback import Episode
        from concurrent.futures import CancelledError
        self._check_scenario(scenario)
        with session_lock(self.directory):
            snapshot = self._snapshot()
            model, env = self._model(snapshot, scenario)
            rng = np.random.default_rng((int(seed) + snapshot.metadata["missions"]) % 2**32)
            observation, _ = env.reset(seed=seed)
            states, actions = [env.simulation.state], []
            try:
                while env.simulation.state.outcome == "running":
                    if cancel_event is not None and cancel_event.is_set():
                        raise CancelledError()
                    if rng.random() < self.settings.exploration:
                        if self.masked:
                            from sar_bot.agents.masked_dqn import joint_action_mask
                            mask = joint_action_mask(torch.as_tensor(observation), env.profile)[0].numpy()
                            action = int(rng.choice(np.flatnonzero(mask)))
                        else:
                            action = int(rng.integers(25))
                    else:
                        action = int(model.predict(observation, deterministic=True)[0])
                    observation, _, _, _, _ = env.step(action)
                    actions.append(action)
                    states.append(env.simulation.state)
                import sys
                engine = digest(sys.modules[RescueSimulation.__module__].__file__)
                return Episode(scenario, tuple(states), tuple(actions),
                               snapshot.metadata["model_sha256"], engine, uuid4().hex)
            finally:
                env.close()

    def _save(self, model, metadata, previous):
        generation = "g-" + uuid4().hex
        folder = self.directory / generation
        folder.mkdir()
        try:
            model.save(folder / "model.zip")
            model.save_replay_buffer(folder / "replay.pkl")
            for name in ("model.zip", "replay.pkl"):
                with (folder / name).open("r+b") as stream:
                    stream.flush()
                    os.fsync(stream.fileno())
            with (folder / "rng.pkl").open("xb") as stream:
                pickle.dump({"python": random.getstate(), "numpy": np.random.get_state(),
                             "torch": torch.get_rng_state()}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            metadata["file_hashes"] = {name: digest(folder / name)
                                      for name in ("model.zip", "replay.pkl", "rng.pkl")}
            metadata["model_sha256"] = metadata["file_hashes"]["model.zip"]
            atomic_json(folder / "metadata.json", metadata)
            pointer = {"generation": generation, "metadata_sha256": digest(folder / "metadata.json")}
            # Comprobar el conjunto escrito antes de cambiar la generación pública.
            temporary_pointer = self.directory / (".verify-" + uuid4().hex + ".json")
            try:
                atomic_json(temporary_pointer, pointer)
                self._read_pointer(temporary_pointer)
            finally:
                temporary_pointer.unlink(missing_ok=True)
            if previous.generation:
                atomic_json(self.directory / "previous.json", {
                    "generation": previous.generation,
                    "metadata_sha256": digest(previous.model_path.parent / "metadata.json")})
            atomic_json(self.directory / "current.json", pointer)
            self._prune({generation, previous.generation})
            return SessionSnapshot(folder / "model.zip", metadata, generation)
        except Exception:
            # Una generación no publicada se ignora; el checkpoint anterior sigue vigente.
            raise

    def _prune(self, protected):
        folders = sorted((p for p in self.directory.glob("g-*")
                          if re.fullmatch(r"g-[0-9a-f]{32}", p.name)),
                         key=lambda p: p.stat().st_mtime, reverse=True)
        keep = protected | {p.name for p in folders[:3]}
        for folder in folders:
            if folder.name not in keep:
                resolved = folder.resolve()
                # Solo generaciones propias, dentro del directorio explícito de sesión.
                if resolved.parent != self.directory or folder.is_symlink():
                    raise ValueError("No se elimina una generacion fuera de la sesion")
                try:
                    shutil.rmtree(resolved)
                except OSError:
                    # Un archivo retenido por otro programa no invalida el guardado.
                    pass

    def learn_episode(self, episode):
        self._check_scenario(episode.scenario)
        if not episode.learning_id or not re.fullmatch(r"[0-9a-f]{32}", episode.learning_id):
            raise ValueError("Solo las misiones nuevas del modo Aprender generan entrenamiento")
        if (len(episode.states) != len(episode.actions) + 1 or not episode.actions
                or episode.states[0] != RescueSimulation(episode.scenario).state
                or episode.states[-1].outcome == "running"):
            raise ValueError("La mision debe estar completa y comenzar en el estado real inicial")
        with session_lock(self.directory):
            previous = self._snapshot()
            if episode.learning_id in previous.metadata["processed_ids"]:
                return {**previous.metadata, "duplicate": True, "recovered": previous.recovered}
            model, env = self._model(previous, episode.scenario, replay=True)
            try:
                observation, _ = env.reset()
                before_updates = model._n_updates
                for index, action in enumerate(episode.actions):
                    next_observation, reward, terminated, truncated, _ = env.step(action)
                    if env.simulation.state != episode.states[index + 1]:
                        raise ValueError("La experiencia no coincide con el motor")
                    model.replay_buffer.add(observation[None, :], next_observation[None, :],
                                            np.array([action]), np.array([reward]),
                                            np.array([terminated or truncated]),
                                            [{"TimeLimit.truncated": truncated and not terminated}])
                    model.num_timesteps += 1
                    model._on_step()
                    observation = next_observation
                size = model.replay_buffer.size()
                guard = None
                if size >= 8:
                    steps = min(self.settings.max_updates, max(1, len(episode.actions)//4))
                    if self.control_scenarios:
                        controls = {s.scenario_id:s for s in (*self.control_scenarios, episode.scenario)}
                        guard = guarded_update(model, tuple(controls.values()), self.rewards,
                                               gradient_steps=steps, batch_size=min(64, size))
                    else:
                        model.train(gradient_steps=steps, batch_size=min(64, size))
                metadata = {**previous.metadata, "profile": env.profile,
                            "missions": previous.metadata["missions"] + 1,
                            "transitions": previous.metadata["transitions"] + len(episode.actions),
                            "updates": previous.metadata["updates"] + model._n_updates - before_updates,
                            "model_timesteps": model.num_timesteps, "buffer_size": size,
                            "processed_ids": [*previous.metadata["processed_ids"], episode.learning_id],
                            "last_mission": {"scenario_id": episode.scenario_id,
                                             "policy_sha256": episode.checkpoint_sha256,
                                             "outcome": episode.states[-1].outcome,
                                             "rescued": len(episode.states[-1].rescued)}}
                if guard:
                    metadata.update(last_guard=guard,
                                    attempted_updates=previous.metadata.get("attempted_updates", previous.metadata["updates"])
                                        + guard["attempted_updates"],
                                    rejected_updates=previous.metadata.get("rejected_updates", 0)
                                        + (0 if guard["accepted"] else guard["attempted_updates"]),
                                    guard_rejections=previous.metadata.get("guard_rejections", 0)
                                        + int(not guard["accepted"]))
                saved = self._save(model, metadata, previous)
                return {**saved.metadata, "duplicate": False, "recovered": previous.recovered}
            finally:
                env.close()
