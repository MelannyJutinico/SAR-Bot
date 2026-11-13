"""Controles reales y render Pygame con controlador de vídeo sin ventana."""

import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["SDL_VIDEODRIVER"] = "dummy"

try:
    import pygame
except ImportError:
    HAS_UI = False
else:
    HAS_UI = True
    from sar_bot.ui.app import RescueApp, SIZE


@unittest.skipUnless(HAS_UI, "Instalar el extra ui para verificar la interfaz")
class UITests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.app = RescueApp(ROOT, ROOT / "scenarios/demo.json", "shortest", asynchronous=False)
        self.app.render()

    def tearDown(self):
        self.app.close()
        pygame.quit()

    def click(self, key):
        self.app.click(self.app.controls[key].center)
        self.app.render()

    def test_buttons_control_playback_without_advancing_on_pause(self):
        self.click("play")
        self.app.update(1 / 3)
        self.assertEqual(self.app.state.steps, 1)
        self.click("play")
        self.app.update(10)
        self.assertEqual(self.app.state.steps, 1)
        self.click("step")
        self.assertEqual(self.app.state.steps, 2)
        self.click("reset")
        self.assertEqual(self.app.state.steps, 0)

    def test_dropdown_changes_scenario_and_resets_episode(self):
        self.click("step")
        self.click("scenario")
        target = next(i for i, (path, _) in enumerate(self.app.options)
                      if path.name == "pasillo_compartido.json")
        self.app.click(dict(self.app.dropdown_rows)[target].center)
        self.assertEqual(self.app.state.steps, 0)
        self.assertEqual(self.app.scenario.name, "pasillo_compartido")
        self.assertIsNone(self.app.dropdown)

    def test_toggles_and_speed_do_not_advance_mission(self):
        before = self.app.state
        self.click("heat")
        self.click("paths")
        self.click("faster")
        self.assertFalse(self.app.show_heat)
        self.assertFalse(self.app.show_paths)
        self.assertEqual(self.app.playback.speed, 4)
        self.assertEqual(self.app.state, before)

    def test_strategy_selector_prepares_a_new_episode(self):
        self.click("step")
        self.click("strategy")
        self.app.click(dict(self.app.dropdown_rows)[3].center)
        self.assertEqual(self.app.strategy_index, 3)
        self.assertEqual(self.app.state.steps, 0)
        self.assertEqual(self.app.render().get_size(), SIZE)

    def test_background_preparation_keeps_the_latest_configuration(self):
        app = RescueApp(ROOT, ROOT / "scenarios/demo.json", "shortest", asynchronous=True)
        try:
            app.scenario_index = next(i for i, (path, _) in enumerate(app.options)
                                      if path.name == "pasillo_compartido.json")
            app._select()
            app.future.result(timeout=30)
            app.update(0)
            self.assertEqual(app.playback.episode.scenario.name, "pasillo_compartido")
            self.assertEqual(app.state.steps, 0)
        finally:
            app.close()

    def test_success_frame_and_keyboard_replay(self):
        self.app.key(pygame.K_SPACE)
        self.app.update(100)
        self.assertEqual(self.app.state.outcome, "success")
        self.assertEqual(self.app.render().get_size(), SIZE)
        self.assertEqual(self.app._status()[0], "RESCATE COMPLETO")
        self.app.key(pygame.K_SPACE)
        self.assertEqual(self.app.state.steps, 0)

    def test_v2_three_people_render_and_finish_using_same_controls(self):
        app = RescueApp(ROOT, ROOT / "scenarios/v2/building_10x10.json", "shortest", asynchronous=False)
        try:
            app.render()
            app.click(app.controls["play"].center)
            app.update(100)
            self.assertEqual(app.scenario.victim_count, 3)
            self.assertEqual(app.state.outcome, "success")
            self.assertEqual(len(app.state.rescued), 3)
            self.assertEqual(app.render().get_size(), SIZE)
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()
