"""Entrena DQN por etapas y registra evaluaciones de desarrollo, no prueba final."""

import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import torch
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.monitor import Monitor

from sar_bot.core import Scenario
from sar_bot.env import RescueEnv, RewardConfig
from sar_bot.learning import evaluate_model, model_score


class DevelopmentEvaluation(BaseCallback):
    def __init__(self, scenarios, rewards, interval, run_dir):
        super().__init__()
        self.scenarios, self.rewards = scenarios, rewards
        self.interval, self.run_dir = interval, run_dir
        self.best_score = None
        self.stage = "untrained"
        self.started = time.monotonic()

    def evaluate(self):
        results = evaluate_model(self.model, self.scenarios, self.rewards)
        score = model_score(results)
        record = {"steps": self.model.num_timesteps, "stage": self.stage,
                  "elapsed_seconds": round(time.monotonic() - self.started, 2),
                  "results": results, "score": score}
        with (self.run_dir / "evaluations.jsonl").open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        if self.best_score is None or score > self.best_score:
            self.best_score = score
            self.model.save(self.run_dir / "best_model")
        status = "; ".join(f"{r['scenario']}: {r['rescued']}/2, {r['outcome']}, "
                           f"pasos={r['steps']}, daño={r['damage_total']}" for r in results)
        print(f"[{self.stage} | {self.model.num_timesteps} pasos] {status}", flush=True)
        return results

    def _on_step(self):
        if self.num_timesteps % self.interval == 0:
            self.evaluate()
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/dqn_initial.json")
    parser.add_argument("--run-dir", type=Path, default=ROOT / "outputs/dqn-initial")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.run_dir.exists() and any(args.run_dir.iterdir()):
        parser.error("run-dir debe estar vacío para no sobrescribir otro experimento")
    rewards = RewardConfig(**config["rewards"])
    if config["dqn"]["gamma"] != rewards.gamma:
        parser.error("El descuento de DQN y del potencial deben coincidir")
    if config["evaluation_interval"] < 1 or any(s["steps"] < 1 for s in config["stages"]):
        parser.error("Intervalos y pasos deben ser positivos")
    scenarios_by_stage = [[Scenario.load(ROOT / p) for p in stage["scenarios"]]
                          for stage in config["stages"]]
    evaluation = [Scenario.load(ROOT / p) for p in config["evaluation_scenarios"]]
    # Validar dimensiones antes de crear archivos o comenzar un entrenamiento.
    check_env(RescueEnv([s for stage in scenarios_by_stage for s in stage] + evaluation, rewards))
    args.run_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(config["torch_threads"])
    paths = sorted({p for stage in config["stages"] for p in stage["scenarios"]}
                   | set(config["evaluation_scenarios"]))
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=False).stdout.strip()
    metadata = {"config": config, "rewards": asdict(rewards), "git_revision": revision,
                "python": sys.version, "packages": {
                    name: importlib.metadata.version(name)
                    for name in ("torch", "gymnasium", "stable-baselines3", "numpy")},
                "scenario_hashes": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
                "evaluation_scope": "development scenarios also used in training; not held-out test"}
    (args.run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    # Copias de escenarios para conservar exactamente las entradas del experimento.
    for path in paths:
        target = args.run_dir / "inputs" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / path).read_bytes())
    callback = DevelopmentEvaluation(evaluation, rewards, config["evaluation_interval"], args.run_dir)
    model = None
    try:
        for stage, scenarios in zip(config["stages"], scenarios_by_stage):
            env = Monitor(RescueEnv(scenarios, rewards), str(args.run_dir / f"{stage['name']}.monitor.csv"))
            env.reset(seed=config["seed"])
            if model is None:
                model = DQN("MlpPolicy", env, seed=config["seed"], device="cpu", verbose=0,
                            **config["dqn"])
                callback.init_callback(model)
                callback.evaluate()
            else:
                model.get_env().close()
                model.set_env(env)
            callback.stage = stage["name"]
            model.learn(total_timesteps=stage["steps"], callback=callback, reset_num_timesteps=False)
            model.save(args.run_dir / f"{stage['name']}_model")
            callback.evaluate()
        model.save(args.run_dir / "final_model")
        best = DQN.load(args.run_dir / "best_model", device="cpu")
        results = evaluate_model(best, evaluation, rewards)
        (args.run_dir / "best_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Entrenamiento terminado. Mejor modelo de desarrollo: {args.run_dir / 'best_model.zip'}")
    finally:
        if model is not None:
            model.get_env().close()


if __name__ == "__main__":
    main()
