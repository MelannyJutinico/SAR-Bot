"""La red elige objetivos; la navegación no sustituye silenciosamente sus decisiones."""
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import torch
from sar_bot.core import Scenario,RescueSimulation
from sar_bot.agents.assignment import AssignmentPolicy,AssignmentFeatures,AssignmentNetwork,save_network,load_network
from sar_bot.agents import create_policy
from sar_bot.online import LearningSession
from sar_bot.assignment_learning import AssignmentLearningSession


class AssignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.scenario=Scenario.load(ROOT/'scenarios/v2/coordination_hub_12x12.json')

    def test_neural_scores_change_target_assignment_and_assign_distinct_people(self):
        class Score(torch.nn.Module):
            def __init__(self,sign):super().__init__();self.sign=sign;self.calls=0
            def forward(self,x):self.calls+=1;return self.sign*x[:,0]
        first=Score(1);second=Score(-1)
        a=AssignmentPolicy(RescueSimulation(self.scenario),network=first)
        b=AssignmentPolicy(RescueSimulation(self.scenario),network=second)
        state=RescueSimulation(self.scenario).state
        a.targets(state);b.targets(state)
        self.assertEqual(first.calls,1);self.assertEqual(second.calls,1)
        self.assertNotEqual(a.assignments[0],b.assignments[0])
        self.assertEqual(len(set(a.assignments.values())),2)
        selected=dict(a.assignments);a.targets(state)
        self.assertEqual(a.assignments,selected);self.assertEqual(first.calls,1)

    def test_features_are_finite_and_only_feasible_assignments_are_offered(self):
        helper=AssignmentFeatures(self.scenario);state=RescueSimulation(self.scenario).state
        options=helper.candidates(state,{})
        self.assertEqual(len(options),6)
        for candidate in options:
            features,label=helper.describe(state,candidate)
            self.assertEqual(features.shape,(16,));self.assertTrue(np.isfinite(features).all());self.assertGreater(label,0)
        state=replace(state,rescued=frozenset({0,1}))
        self.assertEqual(helper.candidates(state,{}),[{0:2},{1:2}])

    def test_factory_uses_assignment_model_and_completes_default_mission(self):
        simulation=RescueSimulation(self.scenario)
        policy=create_policy(simulation,'dqn',model_path=ROOT/'artifacts/rescue_network/model.zip')
        self.assertIsInstance(policy,AssignmentPolicy)
        while simulation.state.outcome=='running':simulation.step(policy.act(simulation.state))
        self.assertEqual(simulation.state.outcome,'success')
        self.assertEqual(len(simulation.state.rescued),3)
        self.assertTrue(policy.decisions)
        self.assertLess(simulation.state.steps,self.scenario.max_steps)

    def test_model_roundtrip_and_incompatible_map_rejection(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/tests') as temp:
            path=Path(temp)/'model.zip';network=AssignmentNetwork().eval()
            save_network(path,network,{'width':12,'height':12,'victims':3})
            loaded,_=load_network(path)
            x=torch.randn(4,16)
            self.assertTrue(torch.equal(network(x),loaded(x)))
            small=Scenario.load(ROOT/'scenarios/demo.json')
            with self.assertRaises(ValueError):AssignmentPolicy(RescueSimulation(small),path)

    def test_session_factory_and_memory_resume_do_not_modify_base_model(self):
        base=ROOT/'artifacts/rescue_network/model.zip'
        configured=LearningSession.for_project(ROOT,base,self.scenario)
        self.assertIsInstance(configured,AssignmentLearningSession)
        scenario=Scenario.load(ROOT/'scenarios/partitions/v2_12x12/training/hub_training_01_easy.json')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/tests') as temp:
            session=AssignmentLearningSession(Path(temp)/'session',base,control_scenarios=(scenario,))
            episode=session.prepare_episode(scenario)
            # Forzar regresión de control comprueba recuperar red y conservar experiencias.
            with patch('sar_bot.assignment_learning.assignment_score',side_effect=[(1,3,-10),(0,0,-100)]):
                result=session.learn_episode(episode)
            self.assertFalse(result['last_guard']['accepted']);self.assertEqual(result['updates'],0)
            self.assertGreater(result['buffer_size'],0);self.assertEqual(result['missions'],1)
            resumed=AssignmentLearningSession(Path(temp)/'session',base,control_scenarios=(scenario,))
            network,_,optimizer,memory=resumed._load(resumed.snapshot())
            original,_=load_network(base)
            for key,value in network.state_dict().items():self.assertTrue(torch.equal(value,original.state_dict()[key]))
            self.assertEqual(len(memory['labels']),result['buffer_size'])
            self.assertTrue(resumed.learn_episode(episode)['duplicate'])

    def test_accepted_session_updates_and_optimizer_continue_after_restart(self):
        base=ROOT/'artifacts/rescue_network/model.zip'
        scenario=Scenario.load(ROOT/'scenarios/partitions/v2_12x12/training/hub_training_01_easy.json')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/tests') as temp:
            directory=Path(temp)/'session'
            session=AssignmentLearningSession(directory,base,control_scenarios=(scenario,))
            first=session.prepare_episode(scenario)
            with patch('sar_bot.assignment_learning.assignment_score',side_effect=[(1,3,-100),(1,3,-90)]):
                result=session.learn_episode(first)
            self.assertTrue(result['last_guard']['accepted']);self.assertEqual(result['updates'],64)
            resumed=AssignmentLearningSession(directory,base,control_scenarios=(scenario,))
            _,_,optimizer,_=resumed._load(resumed.snapshot())
            self.assertTrue(all(int(state['step'])==64 for state in optimizer.state.values()))
            second=resumed.prepare_episode(scenario)
            with patch('sar_bot.assignment_learning.assignment_score',side_effect=[(1,3,-100),(1,3,-90)]):
                result=resumed.learn_episode(second)
            self.assertEqual(result['missions'],2);self.assertEqual(result['updates'],128)
            _,_,optimizer,_=resumed._load(resumed.snapshot())
            self.assertTrue(all(int(state['step'])==128 for state in optimizer.state.values()))

    def test_main_interface_centers_neural_agent_and_keeps_references_in_comparison(self):
        import os
        os.environ['SDL_VIDEODRIVER']='dummy'
        import pygame
        from sar_bot.ui.app import RescueApp
        pygame.display.init();pygame.font.init()
        app=RescueApp(ROOT,ROOT/'scenarios/v2/coordination_hub_12x12.json','dqn',
                      ROOT/'artifacts/rescue_network/model.zip',asynchronous=False)
        try:
            app.neural_focus=True;app.render()
            self.assertNotIn('strategy',app.controls)
            self.assertNotIn('models',app.controls)
            self.assertIn('mode_evaluate',app.controls);self.assertIn('mode_learn',app.controls)
            self.assertIn('compare',app.controls)
            app.action('scenario');app.render()
            for index,_ in app.dropdown_rows:
                scenario=app.options[index][1]
                self.assertEqual((scenario.width,scenario.height,scenario.victim_count),(12,12,3))
        finally:app.close();pygame.quit()


if __name__=='__main__':unittest.main()
