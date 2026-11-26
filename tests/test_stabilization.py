"""Estabilizacion Persona 3: defectos auditados y limites en entradas propias."""
import csv
from dataclasses import replace
from concurrent.futures import Future
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from threading import Event, get_ident
import time
import unittest
from unittest.mock import patch
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
os.environ['SDL_VIDEODRIVER']='dummy'
import pygame
from sar_bot.core import Scenario
from sar_bot.ui.app import RescueApp
from sar_bot.ui.comparison import CompletedComparison, ComparisonRow
from sar_bot.ui.history import make_record, export_trace, load_trace
from sar_bot.ui.local_files import atomic_text
from sar_bot.ui.model_catalog import discover_models, inspect_model
from sar_bot.ui.playback import prepare_episode
from sar_bot.ui.resources import load_ui_scenario, MAX_FILE_BYTES
from sar_bot.ui.scenario_store import ScenarioStore
from sar_bot.ui.views import notice

class DeferredExecutor:
 def __init__(self):self.jobs=[]
 def submit(self,fn,*args):
  future=Future();future.set_running_or_notify_cancel();self.jobs.append((future,fn,args));return future
 def shutdown(self,**kwargs):pass
 def finish(self,index):
  future,fn,args=self.jobs[index];future.set_result(fn(*args))

class StabilizationTests(unittest.TestCase):
 def setUp(self):
  pygame.display.init();pygame.font.init()
  self.app=RescueApp(ROOT,ROOT/'scenarios/v2/warmup_10x10.json','shortest',asynchronous=False)
 def tearDown(self):self.app.close();pygame.quit()
 def wait(self,predicate):
  for _ in range(2000):
   self.app.update(0)
   if predicate():return
   time.sleep(.005)
  self.fail('Timeout')
 def completed(self):
  self.app.action('compare');self.wait(lambda:not self.app.comparison.futures)
  return self.app.last_comparison
 def test_completed_table_survives_edited_mission_and_new_scenario(self):
  self.app.action('play');self.app.update(100);individual=self.app.last_result
  saved=self.completed();original=tuple(saved.rows.items())
  self.app.set_view('preparation');self.app.action('edit')
  for i,pos in enumerate(((2,0),(0,3),(1,2))):self.app.editor.select(i);self.app.editor.place(pos)
  self.app.action('editor_apply');self.app.set_view('analysis');self.app.action('comparison_table')
  self.assertIs(self.app.comparison_for_display,saved)
  self.assertIs(self.app.last_result,individual)
  self.assertNotEqual(saved.request.scenario.configuration_id,self.app.scenario.configuration_id)
  with patch.object(self.app,'text',wraps=self.app.text) as text:
   self.app.render();self.assertTrue(any('Configuracion anterior' in str(c.args[0]) for c in text.call_args_list))
  self.app.scenario_index=0;self.app._select()
  self.assertIs(self.app.last_comparison,saved);self.assertEqual(tuple(saved.rows.items()),original)
 def test_failed_and_incompatible_rows_remain_exactly_preserved(self):
  saved=self.completed()
  rows=tuple(ComparisonRow(r.strategy,'failed',error='fallo real del trabajador') if r.strategy=='thermal' else r for r in saved.entries)
  self.app.last_comparison=CompletedComparison(saved.request,rows)
  self.app.action('prepare');self.app.set_view('analysis');self.app.action('comparison_table')
  comparison=self.app.comparison_for_display
  self.assertEqual(len(comparison.rows),4)
  self.assertEqual(comparison.rows['dqn'].status,'incompatible')
  self.assertEqual(comparison.rows['thermal'].error,'fallo real del trabajador')
  with self.assertRaises(TypeError):comparison.rows['random']=None
 def test_pending_and_late_results_cannot_replace_completed_snapshot(self):
  saved=self.completed();pool=DeferredExecutor()
  self.app.comparison_executor=pool
  self.app.action('compare');old=self.app.comparison
  self.app.action('compare');current=self.app.comparison
  self.assertIs(self.app.last_comparison,saved)
  self.app.action('comparison_saved');self.assertIs(self.app.comparison_for_display,saved)
  for index in (5,3,4):pool.finish(index)
  self.app.update(0);new=self.app.last_comparison
  self.assertEqual(new.request,current.request)
  pool.jobs[0][0].set_result(ComparisonRow('shortest','failed',error='obsoleto'))
  old.poll();self.app.update(0)
  self.assertIs(self.app.last_comparison,new)
  self.assertTrue(old.cancelled.is_set())
 def test_historical_replay_clears_other_configuration_error_and_old_future(self):
  record=make_record(self.app.playback.episode,'shortest',None,0)
  self.app.action('play');self.app.update(100);individual=self.app.last_result
  saved=self.completed()
  self.app.models=tuple(m for m in self.app.models if m.dimensions!=(12,12,3))
  self.app.scenario_index=next(i for i,(p,_) in enumerate(self.app.options) if p.name=='coordination_hub_12x12.json')
  self.app.strategy_index=0;self.app._select();self.assertIn('12x12',self.app.error)
  future=Future();future.set_running_or_notify_cancel();self.app.future=future
  self.app.history_selected=record;self.app.action('history_replay')
  future.set_exception(RuntimeError('error viejo'));self.app.update(0)
  self.assertIsNone(self.app.error);self.assertIsNone(self.app.validation_status)
  self.assertEqual(self.app.playback.index,0);self.assertEqual(self.app.display_scenario.configuration_id,record.episode.configuration_id)
  self.assertNotIn('12x12',notice(self.app));self.assertNotEqual(self.app._status()[0],'ERROR DE CARGA')
  self.assertIs(self.app.last_result,individual);self.assertIs(self.app.last_comparison,saved)
 def test_catalog_rejects_encrypted_corrupt_and_invalid_metadata_and_keeps_valid(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   for name in ('encrypted','corrupt','metadata'):
    folder=root/'artifacts'/name;folder.mkdir(parents=True)
    (folder/'metadata.json').write_bytes((ROOT/'artifacts/v2_pilot/metadata.json').read_bytes())
   encrypted=root/'artifacts/encrypted/model.zip'
   with ZipFile(encrypted,'w') as z:z.writestr('data','{}')
   data=bytearray(encrypted.read_bytes())
   for signature,offset in ((b'PK\x03\x04',6),(b'PK\x01\x02',8)):
    index=data.index(signature)+offset;struct.pack_into('<H',data,index,struct.unpack_from('<H',data,index)[0]|1)
   encrypted.write_bytes(data)
   (root/'artifacts/corrupt/model.zip').write_bytes(b'not a ZIP')
   (root/'artifacts/metadata/model.zip').write_bytes(b'not a ZIP')
   (root/'artifacts/metadata/metadata.json').write_text('{')
   with patch('sar_bot.agents.dqn.DQNPolicy',side_effect=AssertionError('no cargar pesos')):
    entries=discover_models(root,ROOT/'artifacts/v2_pilot/model.zip')
   self.assertEqual(sum(e.error is None for e in entries),1)
   self.assertIn('cifrado',next(e for e in entries if e.path==encrypted).error)
   app=RescueApp(ROOT,ROOT/'scenarios/v2/warmup_10x10.json','shortest',encrypted,asynchronous=False)
   try:self.assertTrue(any(e.error is None for e in app.models));app.action('models');app.render()
   finally:app.close()
 def test_catalog_does_not_hide_unexpected_programming_runtime_errors(self):
  with patch('sar_bot.ui.model_catalog.ZipFile') as archive:
   archive.return_value.__enter__.return_value.getinfo.return_value.file_size=1
   archive.return_value.__enter__.return_value.getinfo.return_value.flag_bits=0
   archive.return_value.__enter__.return_value.read.side_effect=RuntimeError('unexpected programming defect')
   with self.assertRaisesRegex(RuntimeError,'programming'):
    inspect_model(ROOT,ROOT/'artifacts/v2_pilot/model.zip')
 def test_headless_incompatible_exits_two_without_secondary_exception(self):
  with tempfile.TemporaryDirectory() as directory:
   target=Path(directory)/'capture.png'
   original=Scenario.load(ROOT/'scenarios/v2/coordination_hub_12x12.json')
   unsupported=replace(original,width=13,temperatures=tuple(row+(25.0,) for row in original.temperatures))
   scenario=Path(directory)/'unsupported.json';unsupported.save(scenario)
   p=subprocess.run([sys.executable,str(ROOT/'scripts/ui.py'),'--headless','--scenario',str(scenario),'--strategy','dqn','--steps','1','--screenshot',str(target)],capture_output=True,text=True,cwd=ROOT,timeout=20)
   self.assertEqual(p.returncode,2);self.assertIn('DQN no disponible',p.stderr);self.assertNotIn('AttributeError',p.stderr);self.assertFalse(target.exists())
 def test_headless_valid_episode_still_produces_capture_and_metrics(self):
  with tempfile.TemporaryDirectory() as directory:
   target=Path(directory)/'capture.png'
   p=subprocess.run([sys.executable,str(ROOT/'scripts/ui.py'),'--headless','--scenario',str(ROOT/'scenarios/demo.json'),'--strategy','shortest','--steps','1','--screenshot',str(target)],capture_output=True,text=True,cwd=ROOT,timeout=20)
   self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(target.exists());self.assertEqual(json.loads(p.stdout.splitlines()[-1])['steps'],1)
 def test_async_export_keeps_frozen_rows_and_ui_responsive(self):
  saved=self.completed();started=Event();release=Event();main=get_ident();threads=[]
  original=CompletedComparison.export
  def delayed(snapshot,directory):
   threads.append(get_ident());started.set();release.wait(10);return original(snapshot,directory)
  with tempfile.TemporaryDirectory() as directory:
   self.app.root=Path(directory);self.app.set_view('analysis');self.app.action('comparison_table')
   with patch.object(CompletedComparison,'export',delayed):
    self.app.action('comparison_export');self.assertTrue(started.wait(2))
    try:
     self.app.update(0);self.app.render();self.assertFalse(self.app.export_future.done())
     self.app.comparison.rows['thermal']=ComparisonRow('thermal','failed',error='cambio posterior')
    finally:release.set()
    self.wait(lambda:self.app.export_future is None)
   with self.app.last_comparison_export.open(newline='',encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
   self.assertNotEqual(threads[0],main)
   self.assertEqual({r['configuration_id'] for r in rows},{saved.request.scenario.configuration_id})
   self.assertEqual(next(r for r in rows if r['strategy']=='thermal')['status'],'completed')
   self.assertIn('CSV exportado',self.app.comparison_message)
 def test_export_error_is_reported_without_losing_comparison(self):
  saved=self.completed();self.app.set_view('analysis');self.app.action('comparison_table')
  with patch.object(CompletedComparison,'export',side_effect=PermissionError('sin permiso')):
   self.app.action('comparison_export');self.wait(lambda:self.app.export_future is None)
  self.assertIn('No se pudo exportar',self.app.comparison_message);self.assertIs(self.app.last_comparison,saved)
 def test_context_change_during_export_preserves_file_without_stale_confirmation(self):
  self.completed();started=Event();release=Event();original=CompletedComparison.export
  def delayed(snapshot,directory):started.set();release.wait(10);return original(snapshot,directory)
  with tempfile.TemporaryDirectory() as directory:
   self.app.root=Path(directory)
   with patch.object(CompletedComparison,'export',delayed):
    self.app.action('comparison_export');self.assertTrue(started.wait(2))
    try:self.app.set_view('preparation');self.app.action('prepare')
    finally:release.set()
    self.wait(lambda:self.app.export_future is None)
   self.assertTrue(self.app.last_comparison_export.exists());self.assertEqual(self.app.comparison_message,'')
 def test_large_personal_file_rejected_before_reading_and_previous_state_preserved(self):
  before=self.app.scenario;draft=self.app.draft;episode=self.app.playback.episode
  with tempfile.TemporaryDirectory() as directory:
   store=ScenarioStore(Path(directory));path=Path(directory)/'large.json'
   with path.open('wb') as stream:stream.truncate(MAX_FILE_BYTES+1)
   with patch('pathlib.Path.open',side_effect=AssertionError('no debe leer')):
    with self.assertRaisesRegex(ValueError,'16 MiB'):store.load(path.name)
   self.app.store=store;self.app._start_file('load',path.name)
   self.assertIs(self.app.scenario,before);self.assertIs(self.app.draft,draft);self.assertIs(self.app.playback.episode,episode)
 def test_dimensions_steps_and_person_count_rejected_before_core_construction(self):
  source=self.app.scenario.to_dict()
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'large.json'
   for key,value in (('width',1000000),('max_steps',5000),('victims',[[1,0]]*4)):
    data=dict(source);data[key]=value;path.write_text(json.dumps(data))
    with patch('sar_bot.ui.resources.Scenario.from_dict',side_effect=AssertionError('no construir')):
     with self.assertRaises(ValueError):load_ui_scenario(path)
  with patch('sar_bot.ui.playback.create_policy',side_effect=AssertionError('no cargar politica')):
   with self.assertRaises(ValueError):prepare_episode(replace(self.app.scenario,max_steps=5000),'shortest')
 def test_all_official_scenarios_remain_supported(self):
  for path in (ROOT/'scenarios').rglob('*.json'):
   self.assertEqual(load_ui_scenario(path),Scenario.load(path))
 def test_atomic_write_failure_leaves_no_partial_destination_or_temp(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'result.json'
   with self.assertRaises(OSError):
    with atomic_text(path,lambda temporary:None) as stream:
     stream.write('{');raise OSError('interrupcion')
   self.assertEqual(list(Path(directory).iterdir()),[])
 def test_atomic_publish_failure_and_existing_file_never_delete_user_data(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'result.json';path.write_text('original')
   with self.assertRaises(FileExistsError):
    with atomic_text(path,lambda temporary:json.loads(temporary.read_text())) as stream:stream.write('{}')
   self.assertEqual(path.read_text(),'original')
   other=Path(directory)/'new.json'
   with patch('sar_bot.ui.local_files.os.link',side_effect=OSError('fallo publicar')):
    with self.assertRaises(OSError):
     with atomic_text(other,lambda temporary:None) as stream:stream.write('{}')
   self.assertEqual([p.name for p in Path(directory).iterdir()],['result.json'])
 def test_atomic_scenario_trace_and_csv_round_trip(self):
  saved=self.completed();record=make_record(self.app.playback.episode,'shortest',None,0)
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);store=ScenarioStore(root)
   path=store.save(self.app.scenario);self.assertEqual(store.load(path.name),self.app.scenario)
   trace=export_trace(record,root);self.assertEqual(load_trace(trace),record)
   csv_path=saved.export(root)
   with csv_path.open(newline='',encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
   self.assertEqual(len(rows),4);self.assertFalse(list(root.glob('.sarbot-*.tmp')))
 def test_failed_validation_does_not_publish(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'bad.json'
   with self.assertRaises(ValueError):
    with atomic_text(path,lambda temporary:json.loads(temporary.read_text())) as stream:stream.write('{')
   self.assertFalse(path.exists());self.assertEqual(list(Path(directory).iterdir()),[])

 def test_known_dqn_incompatibility_has_distinct_status_and_never_loads_weights(self):
  self.app.model_path=ROOT/'artifacts/sensors_dqn/model.zip';self.app.strategy_index=0
  with patch('sar_bot.ui.app.prepare_mission',side_effect=AssertionError('No preparar incompatible')):
   self.app.scenario_index=next(i for i,(p,_) in enumerate(self.app.options) if p.name=='building_10x10.json')
   self.app._select();self.app.set_view('execution');self.app.render()
   self.assertEqual(self.app._status()[0],'MODELO INCOMPATIBLE')
   self.assertIn('6x6',self.app.error);self.assertIsNone(self.app.playback)
   self.assertTrue({'play','step','reset'}.issubset(self.app.disabled_controls))
   self.app.scenario_index=next(i for i,(p,_) in enumerate(self.app.options) if p.name=='coordination_hub_12x12.json')
   self.app._select();self.assertEqual(self.app._status()[0],'MODELO INCOMPATIBLE')
   self.app.models=tuple(m for m in self.app.models if m.dimensions!=(12,12,3))
   self.app._select();self.assertEqual(self.app._status()[0],'DQN NO DISPONIBLE')
  self.app.strategy_index=1;self.app._select()
  self.assertIsNone(self.app.error);self.assertIsNone(self.app.error_kind);self.assertIsNotNone(self.app.playback)
 def test_valid_v2_model_clears_model_notice_without_fallback(self):
  self.app.model_path=ROOT/'artifacts/sensors_dqn/model.zip';self.app.strategy_index=0;self.app._select()
  self.assertEqual(self.app.error_kind,'model_incompatible')
  self.app.action('models');index=next(i for i,e in enumerate(self.app.models) if e.path.parent.name=='v2_pilot')
  self.app.action('model_'+str(index))
  self.assertEqual(self.app.request.strategy,'dqn');self.assertIsNone(self.app.error_kind)
  self.assertIsNone(self.app.error);self.assertIsNotNone(self.app.playback)
 def test_disabled_buttons_do_not_dispatch_mouse_actions(self):
  self.app.scenario_index=next(i for i,(p,_) in enumerate(self.app.options) if p.name=='demo.json');self.app._select()
  self.app.set_view('preparation');self.app.render()
  with patch.object(self.app,'action',wraps=self.app.action) as action:
   self.app.click(self.app.controls['edit'].center);action.assert_not_called()
  self.app.action('models');self.app.render()
  with patch.object(self.app,'action',wraps=self.app.action) as action:
   self.app.click(self.app.controls['models_prev'].center);action.assert_not_called()
  self.app.action('models_close');self.app.scenario_index=next(i for i,(p,_) in enumerate(self.app.options) if p.name=='warmup_10x10.json');self.app._select()
  self.app.action('edit');self.app.action('editor_clear');self.app.render()
  with patch.object(self.app,'action',wraps=self.app.action) as action:
   self.app.click(self.app.controls['editor_apply'].center);action.assert_not_called()
 def test_secondary_text_contrast_on_panel_and_controls(self):
  from sar_bot.ui.app import MUTED,BG,PANEL,INSET
  def luminance(rgb):
   values=[v/255 for v in rgb];linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
   return sum(v*w for v,w in zip(linear,(.2126,.7152,.0722)))
  for background in (BG,PANEL,INSET):self.assertGreaterEqual((luminance(MUTED)+.05)/(luminance(background)+.05),7)

 def test_wrapped_long_path_stays_inside_panel_width(self):
  from unittest.mock import patch
  message='Modelo no verificable: '+('very_long_path_without_spaces/'*8)
  with patch.object(self.app,'text',wraps=self.app.text) as text:
   self.app.wrap(message,900,220,320,12)
  self.assertGreater(len(text.call_args_list),2)
  font=self.app.fonts[12,False]
  for call in text.call_args_list:self.assertLessEqual(font.size(call.args[0])[0],320)
 def test_missing_catalog_file_has_clear_message_without_absolute_path(self):
  entry=inspect_model(ROOT,ROOT/'outputs/nonexistent-audit-model/model.zip')
  self.assertIn('Falta model.zip o metadata.json',entry.error)
  self.assertNotIn(str(ROOT),entry.error)

 def test_temperature_labels_have_contrast_over_all_heat_colors(self):
  from sar_bot.ui.app import TEXT,heat_color
  def luminance(rgb):
   c=[v/255 for v in rgb]
   return sum((v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4)*w for v,w in zip(c,(.2126,.7152,.0722)))
  for temperature in range(25,161):
   self.assertGreaterEqual((luminance(TEXT)+.05)/(luminance(heat_color(temperature))+.05),4.5)
  with patch.object(self.app,'text',wraps=self.app.text) as text:self.app.render()
  labels=[c for c in text.call_args_list if isinstance(c.args[0],str) and c.args[0].endswith(chr(176))]
  self.assertTrue(labels)
  self.assertTrue(all(c.args[3]==TEXT for c in labels))

if __name__=='__main__':unittest.main()
