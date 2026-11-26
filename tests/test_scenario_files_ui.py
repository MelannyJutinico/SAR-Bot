"""Flujo visual de archivos y resultados de importacion obsoletos."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import Future

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "src"))
os.environ["SDL_VIDEODRIVER"]="dummy"
try:
    import pygame
except ImportError:pygame=None


@unittest.skipIf(pygame is None,"Instalar extra ui")
class ScenarioFilesUITests(unittest.TestCase):
    def setUp(self):
        from sar_bot.ui.app import RescueApp
        from sar_bot.ui.scenario_store import ScenarioStore
        pygame.display.init();pygame.font.init()
        self.app=RescueApp(ROOT,ROOT/'scenarios/v2/warmup_10x10.json','shortest',asynchronous=False)
        self.temp=tempfile.TemporaryDirectory();self.app.store=ScenarioStore(Path(self.temp.name)/'personal')

    def tearDown(self):
        self.app.close();pygame.quit();self.temp.cleanup()

    def edit(self):
        self.app.action('edit');self.app.action('editor_clear')
        for i,pos in enumerate(((2,0),(0,2),(1,1))):
            self.app.editor.select(i);self.app.editor.place(pos)
        return self.app.editor.build()

    def test_complete_save_change_load_prepare_flow(self):
        scenario=self.edit();self.app.action('save_file');path=self.app.last_saved_path
        self.assertTrue(path.is_file());self.assertIn('Guardado',self.app.file_message)
        self.app.editor.select(0);self.app.editor.place((3,0))
        self.app.action('load_file');self.app.render();self.app.action('file_0')
        self.assertEqual(self.app.editor.positions,scenario.victims)
        self.assertEqual(self.app.scenario.configuration_id,scenario.configuration_id)
        self.assertIn('Cargado',self.app.file_message)
        self.app.action('editor_apply')
        self.assertEqual(self.app.playback.episode.configuration_id,scenario.configuration_id)
        self.assertEqual(self.app.playback.episode.states[-1].outcome,'success')

    def test_incomplete_draft_and_file_errors_preserve_state(self):
        self.edit();self.app.action('editor_clear')
        with patch.object(self.app.store,'save') as save:
            self.app.action('save_file');save.assert_not_called()
        self.assertIn('Faltan',self.app.file_message)
        original=self.app.scenario;positions=self.app.editor.positions
        self.app._start_file('load','missing.json')
        self.assertIs(self.app.scenario,original);self.assertEqual(self.app.editor.positions,positions)
        self.assertIn('no existe',self.app.file_message)
        self.app.store.directory.mkdir();(self.app.store.directory/'broken.json').write_text('{')
        self.app._start_file('load','broken.json')
        self.assertIs(self.app.scenario,original);self.assertEqual(self.app.editor.positions,positions)
        self.assertIn('invalido',self.app.file_message)

    def test_save_twice_reports_existing_and_no_overwrite(self):
        self.edit();self.app.action('save_file');path=self.app.last_saved_path;before=path.read_bytes()
        self.app.action('save_file')
        self.assertIn('No se sobrescribio',self.app.file_message);self.assertEqual(path.read_bytes(),before)

    def test_import_invalidates_running_preparation(self):
        from sar_bot.ui.preparation import prepare_mission
        from threading import Event
        old=prepare_mission(self.app.request,self.app.scenario,Event())
        custom=self.edit();path=self.app.store.save(custom)
        self.app.action('editor_exit');request=self.app.request
        self.app._start_file('load',path.name)
        self.assertGreater(self.app.generation,request.generation)
        self.app._accept(old)
        self.assertIsNone(self.app.playback)
        self.assertEqual(self.app.editor.positions,custom.victims)

    def test_load_finishing_after_edit_is_discarded(self):
        class Delayed:
            def submit(self,*args):
                self.future=Future();self.future.set_running_or_notify_cancel();return self.future
            def shutdown(self,**kwargs):pass
        custom=self.edit();queue=Delayed();self.app.file_executor=queue
        self.app._start_file('load','late.json')
        self.app.action('editor_clear');queue.future.set_result(custom);self.app.update(0)
        self.assertEqual(self.app.editor.positions,(None,None,None))
        self.assertNotEqual(self.app.scenario.configuration_id,custom.configuration_id)

    def test_closing_library_discards_pending_load(self):
        self.edit();self.app.action('load_file');self.app.action('library_close')
        self.assertFalse(self.app.library_open)
        self.assertIsNotNone(self.app.editor)

    def test_reserved_scenarios_and_personal_files_not_in_template_menu(self):
        self.assertEqual(self.app.store.directory.parent,Path(self.temp.name))
        self.assertFalse(any(p.parent.name in ('validation','test','curriculum','custom_scenarios')
                             for p,_ in self.app.options))
        self.edit();self.app.action('save_file')
        self.assertNotIn(self.app.last_saved_path,[p for p,_ in self.app.options])

    def test_library_pages_and_clicks_do_not_edit_map(self):
        self.edit();positions=self.app.editor.positions
        self.app.library_open=True;self.app.library_files=tuple(f'file{i}.json' for i in range(8))
        self.app.render();self.app.action('library_next');self.app.render()
        self.assertIn('file_6',self.app.controls)
        self.app.click((130,310));self.assertEqual(positions,self.app.editor.positions)
        self.app.action('library_prev');self.assertEqual(self.app.library_page,0)


if __name__=='__main__':unittest.main()
