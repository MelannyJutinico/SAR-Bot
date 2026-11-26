"""Vistas y catalogo: conservar resultados y no inventar compatibilidad."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
os.environ['SDL_VIDEODRIVER']='dummy'
try:
 import pygame
 from sar_bot.env import RescueEnv
except ImportError:pygame=None
from sar_bot.core import Scenario
from sar_bot.ui.model_catalog import inspect_model


@unittest.skipIf(pygame is None,'Instalar extras ui y rl')
class ViewsModelsTests(unittest.TestCase):
 def setUp(self):
  from sar_bot.ui.app import RescueApp
  pygame.display.init();pygame.font.init()
  self.app=RescueApp(ROOT,ROOT/'scenarios/v2/warmup_10x10.json','shortest',asynchronous=False)
 def tearDown(self):self.app.close();pygame.quit()

 def test_transitions_do_not_prepare_and_preserve_episode_and_selection(self):
  episode=self.app.playback.episode;request=self.app.request
  with patch('sar_bot.ui.app.prepare_mission') as prepare:
   for view in ('execution','analysis','preparation'):
    self.app.set_view(view);self.app.render((125.4,310.5))
   prepare.assert_not_called()
  self.assertIs(self.app.playback.episode,episode);self.assertEqual(self.app.request,request)

 def test_preparation_does_not_draw_catalog_pagination(self):
  for strategy in (0,1):
   self.app.strategy_index=strategy
   self.app.set_view('preparation');self.app.render()
   self.assertIn('prepare',self.app.controls)
   self.assertNotIn('models_prev',self.app.controls)
   self.assertNotIn('models_next',self.app.controls)
  self.app.action('models');self.app.render()
  self.assertNotIn('models_prev',self.app.controls)
  self.assertNotIn('models_next',self.app.controls)

 def test_catalog_only_offers_compatible_models_and_marks_current_one(self):
  self.app.action('models');self.app.render()
  offered=[int(key.split('_')[1]) for key in self.app.controls if key.startswith('model_')]
  self.assertTrue(offered)
  for index in offered:
   self.assertIsNone(self.app.models[index].reason(self.app.scenario))
   self.assertNotIn(f'model_{index}',self.app.disabled_controls)
  target=offered[0]
  self.app.click(self.app.controls[f'model_{target}'].center)
  self.assertEqual(self.app.model_path,self.app.models[target].path)
  self.assertFalse(self.app.models_open)

 def test_programmed_strategies_hide_model_and_learning_controls(self):
  for strategy in (1,2,3):
   self.app.strategy_index=strategy;self.app.render()
   for key in ('models','mode_evaluate','mode_learn','learning_mode'):
    self.assertNotIn(key,self.app.controls)

 def test_explicit_learning_choices_do_not_toggle_when_already_selected(self):
  self.app.strategy_index=0
  with patch.object(self.app,'_prepare') as prepare:
   self.app.render()
   self.app.click(self.app.controls['mode_learn'].center)
   self.assertTrue(self.app.learning_enabled)
   self.app.click(self.app.controls['mode_learn'].center)
   self.assertEqual(prepare.call_count,1)
   self.app.click(self.app.controls['mode_evaluate'].center)
   self.assertFalse(self.app.learning_enabled)
   self.assertEqual(prepare.call_count,2)

 def test_tabs_close_selectors_without_late_import_or_rerun(self):
  self.app.models_open=True
  self.app.set_view('execution')
  self.assertFalse(self.app.models_open)
  self.app.library_open=True;token=self.app.file_request
  episode=self.app.playback.episode
  self.app.set_view('analysis')
  self.assertFalse(self.app.library_open)
  self.assertGreater(self.app.file_request,token)
  self.assertIs(self.app.playback.episode,episode)

 def test_finished_result_and_board_survive_new_configuration(self):
  self.app.action('play');self.app.update(100)
  result=self.app.last_result;episode=self.app.last_episode
  self.assertEqual(result.outcome,'success')
  self.app.set_view('preparation');self.app.action('edit');self.app.action('editor_clear')
  for i,pos in enumerate(((2,0),(0,2),(1,1))):self.app.editor.select(i);self.app.editor.place(pos)
  self.app.action('editor_apply')
  self.assertIs(self.app.last_result,result)
  self.app.set_view('analysis');self.app.render()
  self.assertIs(self.app.display_scenario,episode.scenario)
  self.assertNotEqual(self.app.scenario.configuration_id,result.configuration_id)

 def test_model_catalog_has_real_legacy_and_v2_profiles(self):
  entries={m.path.parent.name:m for m in self.app.models}
  self.assertEqual(entries['sensors_dqn'].dimensions,(6,6,2))
  self.assertEqual(entries['sensors_dqn'].observation_size,157)
  self.assertEqual(entries['v2_pilot'].dimensions,(10,10,3))
  self.assertEqual(entries['v2_pilot'].observation_size,302)
  self.assertEqual(entries['final'].dimensions,(12,12,3))
  self.assertEqual(entries['final'].status,'congelado / una semilla')
  self.assertTrue(all(m.status=='piloto / desarrollo' for name,m in entries.items() if name!='final'))
  self.assertIsNone(entries['v2_pilot'].reason(self.app.scenario))
  self.assertIsNotNone(entries['sensors_dqn'].reason(self.app.scenario))

 def test_select_compatible_and_reject_incompatible_model(self):
  self.app.models_open=True
  wrong=next(i for i,m in enumerate(self.app.models) if m.path.parent.name=='sensors_dqn')
  before=self.app.model_path
  self.app.action(f'model_{wrong}')
  self.assertEqual(self.app.model_path,before);self.assertTrue(self.app.error)
  compatible=next(i for i,m in enumerate(self.app.models) if m.path.parent.name=='v2_pilot')
  self.app.action(f'model_{compatible}')
  self.assertEqual(self.app.model_path,self.app.models[compatible].path)
  self.app.strategy_index=0;self.app._select()
  self.assertIsNotNone(self.app.playback)
  self.assertEqual(self.app.request.strategy,'dqn')

 def test_twelve_by_twelve_unavailable_without_loading_model(self):
  # Ausencia explícita: publicar un modelo nuevo no cambia esta precondición.
  self.app.models=tuple(m for m in self.app.models if m.dimensions!=(12,12,3))
  self.app.scenario_index=next(i for i,(p,_) in enumerate(self.app.options) if p.name=='coordination_hub_12x12.json')
  self.app.strategy_index=0
  with patch('sar_bot.ui.app.prepare_mission') as prepare:
   self.app._select();prepare.assert_not_called()
  self.assertIn('DQN no disponible',self.app.error)
  self.assertIsNone(self.app.playback)
  self.app.action('models');self.app.render()

 def test_published_twelve_by_twelve_model_can_be_selected_and_loaded(self):
  self.app.scenario_index=next(i for i,(p,_) in enumerate(self.app.options) if p.name=='coordination_hub_12x12.json')
  self.app._select()
  index=next(i for i,m in enumerate(self.app.models) if m.path.parent.name=='v2_12x12')
  self.assertIsNone(self.app.models[index].reason(self.app.scenario))
  self.app.action('models')
  self.app.action(f'model_{index}')
  self.app.strategy_index=0;self.app._select()
  self.assertIsNotNone(self.app.playback,self.app.error)
  self.assertEqual(self.app.request.strategy,'dqn')
  self.assertEqual(self.app.playback.episode.scenario.victim_count,3)

 def test_unknown_or_missing_metadata_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'model.zip'
   self.assertTrue(inspect_model(ROOT,path).error)
   (path.parent/'metadata.json').write_text('{')
   self.assertTrue(inspect_model(ROOT,path).error)
   (path.parent/'metadata.json').write_text(json.dumps({'config':{},'observation_profile':{'schema_version':999}}))
   self.assertIn('Esquema',inspect_model(ROOT,path).error)

 def test_checkpoint_and_metadata_mismatch_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'model.zip'
   profile={'schema_version':2,'width':10,'height':10,'victims':3,'mode':'sensors','observation_size':302,'actions':25}
   metadata={'config':{'dqn':{'policy_kwargs':{'net_arch':[128,128]}}},'observation_profile':profile}
   (path.parent/'metadata.json').write_text(json.dumps(metadata))
   with ZipFile(path,'w') as z:z.writestr('data',json.dumps({'observation_space':{'_shape':[157]},'action_space':{'n':25}}))
   self.assertIn('no coinciden',inspect_model(ROOT,path).error)

 def test_person_pickup_and_delivery_labels(self):
  from sar_bot.core import MissionState,Robot
  from sar_bot.ui.views import person_status
  state=MissionState((Robot((1,0),carrying=0),Robot((0,0))))
  self.assertIn('Recogida',person_status(state,0))
  from dataclasses import replace
  self.assertEqual(person_status(replace(state,rescued=frozenset({0})),0),'Entregada en base')
  self.assertIn('Pendiente',person_status(state,1))

 def test_analysis_distinguishes_failure_and_time_limit_without_fabricating_metrics(self):
  from dataclasses import replace
  self.app.action('play');self.app.update(100)
  result=self.app.last_result
  for outcome in ('destroyed','time_limit','success'):
   self.app.last_result=replace(result,outcome=outcome)
   self.app.set_view('analysis');self.app.render()
   self.assertEqual(self.app.last_result.steps,result.steps)

 def test_certification_warning_and_preparation_error_are_actionable(self):
  from sar_bot.ui.views import notice
  self.app.validation_status='not_certified'
  self.assertIn('No significa imposible',notice(self.app))
  self.app.error='Selecciona otro modelo o una referencia.'
  self.assertIn('Selecciona',notice(self.app))
  self.app.set_view('execution');self.app.render()

if __name__=='__main__':unittest.main()
