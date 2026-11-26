"""SARB-032: estados reales, persistencia verificable y reproduccion sin politica."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from concurrent.futures import Future
from dataclasses import replace
from hashlib import sha256
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
os.environ['SDL_VIDEODRIVER']='dummy'
import pygame
from sar_bot.ui.app import RescueApp
from sar_bot.ui.history import (History, canonical, derive_events, export_trace, load_trace, make_record)
from sar_bot.ui.playback import prepare_episode

class HistoryTests(unittest.TestCase):
 def setUp(self):
  pygame.display.init();pygame.font.init()
  self.app=RescueApp(ROOT,ROOT/'scenarios/v2/warmup_10x10.json','shortest',asynchronous=False)
 def tearDown(self):self.app.close();pygame.quit()
 def wait(self):
  for _ in range(1000):
   self.app.update(0)
   if not self.app.history.pending and not self.app.history.io:return
   time.sleep(.005)
  self.fail('Timeout del historial')
 def completed(self):
  self.app.action('play');self.app.update(100);self.wait()
  return self.app.history.records[-1]
 def test_real_mission_registered_once_with_identity_and_states(self):
  record=self.completed()
  for _ in range(10):self.app.update(0)
  self.assertEqual(len(self.app.history.records),1)
  self.assertIs(record.episode,self.app.last_episode)
  self.assertEqual(record.episode.configuration_id,self.app.scenario.configuration_id)
  self.assertEqual(record.episode.scenario.victims,self.app.scenario.victims)
  self.assertEqual(record.episode.actions,self.app.playback.episode.actions)
  self.assertEqual(record.metrics['rescued'],3)
 def test_pickups_deliveries_and_finalization_are_not_duplicated(self):
  record=self.completed();events=record.events
  self.assertEqual({e.value for e in events if e.kind=='recogida'},{0,1,2})
  self.assertEqual(len([e for e in events if e.kind=='recogida']),3)
  self.assertEqual(len([e for e in events if e.kind=='entrega']),3)
  self.assertEqual(events[0].kind,'inicio');self.assertEqual(events[-1].kind,'finalizacion')
  self.assertEqual(sum(e.kind=='rescate_completado' for e in events),1)
  self.assertFalse(any(e.kind in ('dano','destruccion') for e in events))
 def test_damage_and_destruction_match_real_engine_totals(self):
  episode=prepare_episode(ROOT/'scenarios/ruta_caliente.json','random',seed=0)
  events=derive_events(episode)
  for robot in (1,2):
   self.assertEqual(sum(e.value for e in events if e.kind=='dano' and e.robot==robot),episode.states[-1].robots[robot-1].damage)
  self.assertEqual(sum(e.kind=='destruccion' for e in events),1)
  self.assertEqual(events[-1].value,'destroyed')
  self.assertFalse(any(e.kind=='rescate_completado' for e in events))
 def test_events_have_state_evidence(self):
  record=self.completed()
  for event in record.events:
   if event.step==0:continue
   old,new=record.episode.states[event.step-1:event.step+1]
   if event.kind=='movimiento':self.assertNotEqual(old.robots[event.robot-1].position,new.robots[event.robot-1].position)
   if event.kind=='recogida':self.assertEqual(new.robots[event.robot-1].carrying,event.value)
   if event.kind=='entrega':self.assertIn(event.value,new.rescued-old.rescued)
 def test_replay_pause_reset_without_policy_training_or_simulation(self):
  record=self.completed();result=self.app.last_result
  self.app.history_selected=record
  with patch('sar_bot.ui.playback.create_policy',side_effect=AssertionError('policy')),patch('sar_bot.ui.playback.prepare_episode',side_effect=AssertionError('episode')),patch('sar_bot.core.RescueSimulation.step',side_effect=AssertionError('motor')):
   self.app.action('history_replay');self.assertEqual(self.app.playback.index,0)
   self.assertIs(self.app.playback.episode,record.episode)
   self.app.action('play');self.app.update(.5);self.assertGreater(self.app.playback.index,0)
   self.app.action('play');index=self.app.playback.index;self.app.update(10);self.assertEqual(self.app.playback.index,index)
   self.app.action('reset');self.assertEqual(self.app.playback.index,0)
   self.app.action('play');self.app.update(100)
   self.app.set_view('analysis');self.app.render()
  self.assertIs(self.app.last_result,result)
  self.assertEqual(len(self.app.history.records),1)
 def test_json_round_trip_preserves_every_state_action_event_and_hash(self):
  record=self.completed()
  with tempfile.TemporaryDirectory() as directory:
   path=export_trace(record,directory)
   with patch('sar_bot.ui.playback.create_policy',side_effect=AssertionError('policy')):
    loaded=load_trace(path)
   self.assertEqual(record,loaded)
   data=json.loads(path.read_text())
   digest=data.pop('trace_sha256')
   self.assertEqual(digest,sha256(canonical(data).encode()).hexdigest())
   self.assertEqual(record.episode.engine_sha256,data['engine_sha256'])
 def test_corrupt_or_forged_states_events_metrics_and_versions_rejected(self):
  record=self.completed()
  with tempfile.TemporaryDirectory() as directory:
   path=export_trace(record,directory);original=json.loads(path.read_text())
   for field in ('states','events','metrics','engine_sha256','version'):
    data=json.loads(json.dumps(original))
    if field=='states':data[field][1]['robots'][0]['damage']=999
    elif field=='events':data[field]=[]
    elif field=='metrics':data[field]['rescued']=999
    elif field=='version':data[field]=999
    else:data[field]='0'*64
    data.pop('trace_sha256');data['trace_sha256']=sha256(canonical(data).encode()).hexdigest()
    path.write_text(json.dumps(data))
    with self.assertRaises(ValueError):load_trace(path)
   path.write_text('{')
   with self.assertRaises(ValueError):load_trace(path)
 def test_checksum_change_is_rejected(self):
  with tempfile.TemporaryDirectory() as directory:
   path=export_trace(self.completed(),directory);data=json.loads(path.read_text());data['seed']=88;path.write_text(json.dumps(data))
   with self.assertRaisesRegex(ValueError,'hash'):load_trace(path)
 def test_bad_async_import_preserves_selection_individual_and_comparison(self):
  record=self.completed();self.app.history_selected=record;result=self.app.last_result
  self.app.action("compare");comparison=self.app.comparison
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'trace-bad.json';path.write_text('{}')
   self.app.history.start_io('load',path.name,Path(directory));self.wait()
  self.assertIs(self.app.history_selected,record);self.assertIs(self.app.last_result,result)
  self.assertIn('invalida',self.app.history.message)
  self.assertIs(self.app.comparison,comparison)
 def test_comparison_completed_rows_are_archived_once_and_survive_new_configuration(self):
  self.app.action('compare')
  for _ in range(1000):
   self.app.update(0)
   if not self.app.comparison.futures:break
   time.sleep(.005)
  self.wait();comparison=self.app.comparison
  self.assertEqual({r.strategy for r in self.app.history.records},{'shortest','thermal','random'})
  self.app.history_selected=self.app.history.records[0];self.app.action('history_replay')
  self.assertIs(self.app.comparison,comparison)
  self.app.set_view('analysis');self.assertIs(self.app.comparison,comparison)
  record=self.app.history_selected;self.app._enter_editor();self.app.editor.clear()
  self.assertIn(record,self.app.history.records)
 def test_stale_import_result_cannot_replace_selection(self):
  record=self.completed();self.app.history_selected=record
  future=Future();future.set_running_or_notify_cancel()
  self.app.history.io=(future,self.app.history.token,'load')
  self.app._enter_editor();future.set_result(replace(record,record_id='old'))
  self.app.update(0)
  self.assertIs(self.app.history_selected,record);self.assertEqual(len(self.app.history.records),1)
 def test_selection_invalidates_pending_import(self):
  record=self.completed();future=Future();future.set_running_or_notify_cancel()
  self.app.history.io=(future,self.app.history.token,'load')
  self.app.action('history_select_0');future.set_result(replace(record,record_id='old'))
  self.app.update(0);self.assertIs(self.app.history_selected,record)
 def test_history_retention_is_bounded_and_does_not_delete_exports(self):
  record=self.completed()
  with tempfile.TemporaryDirectory() as directory:
   path=export_trace(record,directory)
   for i in range(25):self.app.history.add(replace(record,record_id=str(i)))
   self.assertEqual(len(self.app.history.records),20)
   self.assertEqual(self.app.history.records[0].record_id,'5')
   self.assertTrue(path.exists())
 def test_valid_async_import_and_export_are_independent_of_current_scenario(self):
  record=self.completed()
  with tempfile.TemporaryDirectory() as directory:
   path=export_trace(record,directory)
   self.app._enter_editor();self.app.editor.clear()
   self.app.history.start_io('load',path.name,Path(directory));self.wait()
   self.assertEqual(self.app.history_selected,record)
   self.app.history.start_io('export',record,Path(directory));self.wait()
   self.assertEqual(len(list(Path(directory).glob('*.json'))),2)
 def test_checkpoint_hash_is_real_and_replay_does_not_need_weights(self):
  model=ROOT/'artifacts/v2_pilot/model.zip'
  episode=prepare_episode(self.app.scenario,'dqn',model)
  self.assertEqual(episode.checkpoint_sha256,sha256(model.read_bytes()).hexdigest())
  record=make_record(episode,'dqn',str(model),0)
  with tempfile.TemporaryDirectory() as directory:
   path=export_trace(record,directory)
   with patch('sar_bot.ui.playback.create_policy',side_effect=AssertionError('DQN')):
    self.app.history_selected=load_trace(path);self.app.action('history_replay')
    self.assertEqual(self.app.playback.index,0)
 def test_close_discards_late_io(self):
  record=self.completed();future=Future();future.set_running_or_notify_cancel()
  self.app.history.io=(future,self.app.history.token,'load');self.app.close()
  future.set_result(record);self.assertIsNone(self.app.history.poll())

if __name__=='__main__':unittest.main()
