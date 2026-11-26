"""Preentrena con recorridos térmicos de entrenamiento y refina con DQN.

Los checkpoints elegibles para entrega tienen al menos minimum_rl_steps de
interacción y actualización por refuerzo. Validación no aporta demostraciones.
"""

import argparse
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

import numpy as np
import torch
from torch.nn import functional as F
from stable_baselines3 import DQN
from stable_baselines3.common.monitor import Monitor
from sar_bot.agents import create_policy
from sar_bot.agents.masked_dqn import (MaskedDQN, MaskedDQNPolicy,
                                      RescueFeaturesExtractor, joint_action_mask)
from sar_bot.core import Scenario
from sar_bot.env import RescueEnv, RewardConfig
from sar_bot.learning import evaluate_model, model_score
from sar_bot.training import resolve_training_config, StageExploration
from train import DevelopmentEvaluation


def canonical_action(simulation, action):
    positions = tuple(r.position for r in simulation.state.robots)
    destinations = simulation.resolve_movement(positions,int(action))
    individual = [int(action)//5,int(action)%5]
    for i in range(2):
        if positions[i]==destinations[i]:individual[i]=4
    result=5*individual[0]+individual[1]
    if simulation.resolve_movement(positions,result)!=destinations:
        raise ValueError("La normalizacion cambio la transicion de referencia")
    return result


def collect_demonstrations(env, model):
    observations, actions, traces = [], [], []
    for index,scenario in enumerate(env.scenarios):
        observation,_=env.reset(seed=0,options={"scenario_index":index})
        policy=create_policy(env.simulation,"thermal")
        sequence=[]
        while env.simulation.state.outcome=="running":
            action=canonical_action(env.simulation,policy.act(env.simulation.state))
            mask=joint_action_mask(torch.as_tensor(observation),env.profile)[0]
            if not bool(mask[action]):raise ValueError("Demostracion incompatible con la mascara")
            next_observation,reward,terminated,truncated,_=env.step(action)
            model.replay_buffer.add(observation[None,:],next_observation[None,:],
                                    np.array([action]),np.array([reward]),
                                    np.array([terminated or truncated]),
                                    [{"TimeLimit.truncated":truncated and not terminated}])
            observations.append(observation);actions.append(action);sequence.append(action)
            observation=next_observation
        if env.simulation.state.outcome!="success":
            raise ValueError("La referencia no completo un caso de entrenamiento")
        traces.append({"scenario_id":scenario.scenario_id,"configuration_id":scenario.configuration_id,
                       "scenario":scenario.name,"actions":sequence,"strategy":"thermal",
                       "rescued":len(env.simulation.state.rescued),"outcome":"success"})
    return torch.as_tensor(np.asarray(observations)),torch.as_tensor(actions,dtype=torch.long),traces


class RefinementEvaluation(DevelopmentEvaluation):
    def __init__(self,*args,minimum_steps,**kwargs):
        super().__init__(*args,**kwargs)
        self.minimum_steps=minimum_steps

    def _on_step(self):
        if self.num_timesteps>=self.minimum_steps:
            return super()._on_step()
        return True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=ROOT/"configs/dqn_v2_12x12_guided.json")
    parser.add_argument("--run-dir",type=Path,required=True)
    parser.add_argument("--seed",type=int,default=0)
    args=parser.parse_args()
    if not 0<=args.seed<2**32:parser.error("Semilla invalida")
    if args.run_dir.exists() and any(args.run_dir.iterdir()):parser.error("El directorio debe ser nuevo")
    config,partition=resolve_training_config(json.loads(args.config.read_text(encoding="utf-8")),ROOT)
    if not partition:parser.error("Se requiere un manifiesto congelado")
    config["seed"]=args.seed
    if len(config["stages"])!=1:parser.error("El refinamiento guiado usa una etapa completa")
    stage=config["stages"][0];pre=config["pretraining"]
    if pre["strategy"]!="thermal":parser.error("Las demostraciones usan la referencia termica")
    if not (1<=pre["epochs"]<=1000 and 1<=pre["evaluation_every"]<=pre["epochs"]
            and 1<=pre["minimum_rl_steps"]<=stage["steps"]):parser.error("Presupuesto invalido")
    rewards=RewardConfig(**config["rewards"])
    if rewards.gamma!=config["dqn"]["gamma"]:parser.error("Descuentos distintos")
    torch.set_num_threads(config["torch_threads"])
    scenarios=[Scenario.load(ROOT/p) for p in stage["scenarios"]]
    validation=[Scenario.load(ROOT/p) for p in config["evaluation_scenarios"]]
    raw_env=RescueEnv(scenarios,rewards,observation_mode="sensors")
    args.run_dir.mkdir(parents=True,exist_ok=True)
    env=Monitor(raw_env,str(args.run_dir/"refinement.monitor.csv"))
    dqn=deepcopy(config["dqn"])
    dqn.setdefault("policy_kwargs",{}).update(rescue_profile=raw_env.profile,
        features_extractor_class=RescueFeaturesExtractor,
        features_extractor_kwargs={"rescue_profile":raw_env.profile})
    model=MaskedDQN(MaskedDQNPolicy,env,seed=args.seed,device="cpu",verbose=0,**dqn)
    model.sar_bot_profile=raw_env.profile
    paths=sorted(set(stage["scenarios"])|set(config["evaluation_scenarios"]))
    metadata={"config":config,"rewards":asdict(rewards),"observation_profile":raw_env.profile,
              "partition_manifest":partition,"evaluation_scope":"validation/selection; test not evaluated",
              "evaluation_overlap_with_training":[],"training_method":"imitation pretraining plus DQN reinforcement",
              "git_revision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
              "python":sys.version,"packages":{p:importlib.metadata.version(p)
                  for p in ("numpy","torch","gymnasium","stable-baselines3")},
              "scenario_hashes":{p:sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}
    for path in paths:
        target=args.run_dir/"inputs"/path;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/path).read_bytes())
    (args.run_dir/"partition_manifest.json").write_bytes((ROOT/config["partition_manifest"]).read_bytes())
    started=time.monotonic()
    try:
        observations,actions,traces=collect_demonstrations(raw_env,model)
        trace_path=args.run_dir/"demonstrations.jsonl"
        trace_path.write_text("".join(json.dumps(r)+"\n" for r in traces),encoding="utf-8")
        metadata["demonstrations"]={"strategy":"thermal","cases":len(traces),"transitions":len(actions),
                                     "partition":"training","sha256":sha256(trace_path.read_bytes()).hexdigest(),
                                     "blocked_attempts_normalized_to_wait":True}
        (args.run_dir/"metadata.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
        print(f"Demostraciones: {len(traces)} casos de entrenamiento, {len(actions)} transiciones",flush=True)
        best=None
        rng=np.random.default_rng(args.seed)
        for group in model.policy.optimizer.param_groups:group["lr"]=pre["learning_rate"]
        for epoch in range(1,pre["epochs"]+1):
            model.policy.set_training_mode(True)
            losses=[]
            order=rng.permutation(len(actions))
            for start in range(0,len(actions),pre["batch_size"]):
                batch=order[start:start+pre["batch_size"]]
                loss=F.cross_entropy(model.q_net(observations[batch]),actions[batch])
                model.policy.optimizer.zero_grad();loss.backward()
                torch.nn.utils.clip_grad_norm_(model.q_net.parameters(),10)
                model.policy.optimizer.step();losses.append(float(loss.detach()))
            if epoch%pre["evaluation_every"]==0 or epoch==pre["epochs"]:
                results=evaluate_model(model,validation,rewards);score=model_score(results)
                record={"epoch":epoch,"loss":float(np.mean(losses)),"score":score,"results":results}
                with (args.run_dir/"pretraining.jsonl").open("a",encoding="utf-8") as stream:
                    stream.write(json.dumps(record)+"\n")
                if best is None or score>best:
                    best=score;model.save(args.run_dir/"pretrained_model.zip")
                print(f"Preentrenamiento {epoch}: {score[0]}/{len(results)} misiones, {score[1]} personas",flush=True)
        replay=model.replay_buffer
        model=MaskedDQN.load(args.run_dir/"pretrained_model.zip",env=env,device="cpu",
                             learning_rate=config["dqn"]["learning_rate"])
        model.replay_buffer=replay
        model.q_net_target.load_state_dict(model.q_net.state_dict())
        model.exploration_schedule=StageExploration(0,stage["steps"],**stage["exploration"])
        model.exploration_rate=stage["exploration"]["initial"]
        callback=RefinementEvaluation(validation,rewards,config["evaluation_interval"],args.run_dir,
                                      minimum_steps=pre["minimum_rl_steps"])
        callback.stage="reinforcement_refinement"
        model.learn(total_timesteps=stage["steps"],callback=callback,reset_num_timesteps=False)
        model.save(args.run_dir/"final_model.zip")
        callback.init_callback(model);callback.evaluate()
        selected=DQN.load(args.run_dir/"best_model.zip",device="cpu")
        results=evaluate_model(selected,validation,rewards)
        (args.run_dir/"best_results.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
        records=[json.loads(l) for l in (args.run_dir/"evaluations.jsonl").read_text(encoding="utf-8").splitlines()]
        record=max(records,key=lambda r:tuple(r["score"]))
        summary={"scope":"guided training","training_method":metadata["training_method"],
                 "training_steps":model.num_timesteps,"training_seed":args.seed,"selected_steps":record["steps"],
                 "selection_split":"validation","validation_cases":len(results),
                 "successes":sum(r["success"] for r in results),"rescued":sum(r["rescued"] for r in results),
                 "elapsed_seconds":round(time.monotonic()-started,2),"test_evaluated":False,
                 "model_sha256":sha256((args.run_dir/"best_model.zip").read_bytes()).hexdigest()}
        (args.run_dir/"training_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
        print(json.dumps(summary),flush=True)
    finally:env.close()


if __name__=="__main__":main()
