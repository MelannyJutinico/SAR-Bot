"""El profesor programado solo aporta casos de entrenamiento y precede a RL real."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"scripts"))
import torch
from train_guided import canonical_action,collect_demonstrations
from sar_bot.agents.masked_dqn import MaskedDQN,MaskedDQNPolicy,joint_action_mask
from sar_bot.core import RescueSimulation,Scenario
from sar_bot.env import RescueEnv


class GuidedTrainingTests(unittest.TestCase):
    def test_invalid_attempts_become_physically_identical_waits(self):
        scenario=Scenario.load(ROOT/"scenarios/v2/warmup_10x10.json")
        simulation=RescueSimulation(scenario)
        action=canonical_action(simulation,0)
        self.assertEqual(action,24)
        self.assertEqual(simulation.resolve_movement(((0,0),(0,0)),0),
                         simulation.resolve_movement(((0,0),(0,0)),action))

    def test_demonstrations_are_successful_real_transitions_with_valid_actions(self):
        torch.set_num_threads(1)
        scenario=Scenario.load(ROOT/"scenarios/v2/warmup_10x10.json")
        env=RescueEnv([scenario],observation_mode="sensors")
        model=MaskedDQN(MaskedDQNPolicy,env,device="cpu",buffer_size=64,
                        policy_kwargs={"net_arch":[16,16],"rescue_profile":env.profile})
        observations,actions,traces=collect_demonstrations(env,model)
        self.assertEqual(traces[0]["rescued"],3)
        self.assertEqual(traces[0]["outcome"],"success")
        mask=joint_action_mask(observations,env.profile)
        self.assertTrue(mask[torch.arange(len(actions)),actions].all())
        self.assertEqual(model.replay_buffer.size(),len(actions))

    def test_guided_cli_only_selects_checkpoints_after_reinforcement(self):
        root=ROOT/"tmp/tests";root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            directory=Path(directory)
            cfg=json.loads((ROOT/"configs/dqn_v2_12x12_guided.json").read_text(encoding="utf-8"))
            manifest=json.loads((ROOT/cfg["partition_manifest"]).read_text(encoding="utf-8"))
            cfg["stages"][0].pop("training_filter")
            cfg["stages"][0].update(steps=16,scenarios=manifest["training"][:1])
            cfg["evaluation_scenarios"]=manifest["validation"][:1]
            cfg["pretraining"].update(epochs=1,evaluation_every=1,minimum_rl_steps=8)
            cfg["dqn"].update(buffer_size=128,batch_size=8,policy_kwargs={"net_arch":[16,16]})
            cfg["evaluation_interval"]=8
            path=directory/"config.json";path.write_text(json.dumps(cfg),encoding="utf-8")
            run=directory/"run"
            result=subprocess.run([sys.executable,str(ROOT/"scripts/train_guided.py"),
                                   "--config",str(path),"--run-dir",str(run)],
                                   cwd=ROOT,capture_output=True,text=True,timeout=180)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            summary=json.loads((run/"training_summary.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(summary["selected_steps"],8)
            self.assertFalse(summary["test_evaluated"])
            from stable_baselines3 import DQN
            loaded=DQN.load(run/"best_model.zip",device="cpu")
            self.assertGreater(loaded._n_updates,0)
            metadata=json.loads((run/"metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["demonstrations"]["partition"],"training")
            self.assertEqual(metadata["demonstrations"]["cases"],1)


if __name__=="__main__":unittest.main()
