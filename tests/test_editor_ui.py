"""Editor integrado: eventos y render sobre RescueApp con v?deo dummy."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["SDL_VIDEODRIVER"] = "dummy"
try:
    import pygame
except ImportError:
    pygame = None


@unittest.skipIf(pygame is None, "Instalar extra ui")
class EditorUITests(unittest.TestCase):
    def setUp(self):
        from sar_bot.ui.app import RescueApp
        pygame.display.init()
        pygame.font.init()
        self.app = RescueApp(ROOT, ROOT / "scenarios/v2/warmup_10x10.json",
                             "shortest", asynchronous=False)
        self.app.render()

    def tearDown(self):
        self.app.close()
        pygame.quit()

    def click(self, key):
        if key not in self.app.controls:
            self.app.set_view("execution" if key in ("play","step","reset","heat","paths","faster","slower") else "preparation")
            self.app.render()
        self.app.click(self.app.controls[key].center)
        self.app.render()

    def enter(self):
        self.click("edit")
        self.assertIsNotNone(self.app.editor)

    def test_visible_entry_and_person_controls(self):
        self.enter()
        self.assertIn("EDICIÓN", self.app._status()[0])
        for i in range(3):
            self.click(f"person_{i}")
            self.assertEqual(self.app.editor.selected, i)
        self.click("editor_clear")
        self.assertEqual(self.app.editor.missing, 3)
        self.click("editor_restore")
        self.assertEqual(self.app.editor.positions, self.app.scenario.victims)

    def test_map_click_and_control_click_are_separate(self):
        self.enter()
        self.click("editor_clear")
        self.assertEqual(self.app.editor.missing, 3)
        gx, gy, cell = self.app.grid
        self.app.click((gx + cell + cell / 2, gy + cell / 2))
        self.assertEqual(self.app.editor.positions[0], (1, 0))
        before = self.app.editor.positions
        self.click("person_2")
        self.assertEqual(self.app.editor.positions, before)
        self.app.click((10, 10))
        self.assertEqual(self.app.editor.positions, before)
        self.app.click((gx + cell / 2, gy + cell / 2))
        self.assertTrue(self.app.editor.invalid)
        self.assertEqual(self.app.editor.positions, before)

    def test_editor_does_not_execute_or_tick_and_exit_uses_template(self):
        self.enter()
        original = self.app.scenario.to_dict()
        self.click("editor_clear")
        with patch("sar_bot.ui.app.prepare_episode") as prepare:
            self.app.key(pygame.K_SPACE)
            self.app.key(pygame.K_n)
            self.app.key(pygame.K_r)
            self.app.update(100)
            prepare.assert_not_called()
        self.assertEqual(self.app.state.steps, 0)
        self.assertEqual(original, self.app.scenario.to_dict())
        self.click("editor_exit")
        self.assertIsNone(self.app.editor)
        self.assertEqual(self.app.playback.episode.configuration_id, self.app.scenario.configuration_id)

    def test_return_to_editor_after_mission_started_preserves_draft(self):
        self.click("step")
        self.click("edit")
        self.assertIs(self.app.editor, self.app.draft)
        self.assertEqual(self.app.state.steps, 0)

    def test_pending_preparation_cannot_replace_editor(self):
        from concurrent.futures import Future
        future = Future()
        future.set_running_or_notify_cancel()
        self.app.future = future
        self.enter()
        future.set_result(None)
        self.app.update(0)
        self.assertIsNotNone(self.app.editor)
        self.assertIsNone(self.app.playback)

    def test_hover_temperature_receives_integer_cells_through_all_ui_states(self):
        from sar_bot.core import Scenario
        from sar_bot.ui.editor import Viewport
        original = Scenario.temperature_at
        calls = []

        def checked_temperature(scenario, position):
            self.assertTrue(all(type(value) is int for value in position), position)
            self.assertTrue(scenario.in_bounds(position), position)
            calls.append(position)
            return original(scenario, position)

        with patch.object(Scenario, "temperature_at", checked_temperature):
            for size in ((1280, 860), (800, 600), (1600, 900)):
                viewport = Viewport(size)
                gx, gy, cell = self.app.grid
                logical = (gx + 1.5 * cell, gy + 1.5 * cell)
                physical = tuple(viewport.offset[i] + logical[i] * viewport.size[i] / viewport.canvas[i]
                                 for i in range(2))
                mouse = viewport.logical(physical)
                self.assertIsInstance(mouse[0], float)
                before = len(calls)
                self.app.render(mouse)
                self.assertIn((1, 1), calls[before:])
                self.app.mouse = mouse
                self.app._board()
                self.enter()
                self.click("editor_clear")
                for person, position in enumerate(((1, 0), (0, 1), (1, 1))):
                    self.app.action(f"person_{person}")
                    self.app.click((gx + (position[0] + .5) * cell,
                                    gy + (position[1] + .5) * cell))
                    self.app.render(mouse)
                self.app.action("person_0")
                self.app.click((gx + 2.5 * cell, gy + .5 * cell))
                self.assertEqual(self.app.editor.positions[0], (2, 0))
                self.app.render(mouse)
                self.click("editor_exit")
                self.app.action("play")
                self.app.update(.5)
                self.app.render(mouse)
                self.app.action("reset")
                self.app.render(mouse)

    def test_resized_window_click_selects_same_map_cell(self):
        from sar_bot.ui.editor import Viewport
        self.enter()
        self.click("editor_clear")
        gx, gy, cell = self.app.grid
        logical = (gx + cell * 1.5, gy + cell * 1.5)
        for size in ((800, 600), (1600, 900)):
            viewport = Viewport(size)
            physical = tuple(viewport.offset[i] + logical[i] * viewport.size[i] / viewport.canvas[i]
                             for i in range(2))
            self.app.click(viewport.logical(physical))
            self.assertEqual(self.app.editor.positions[0], (1, 1))
            window = pygame.display.set_mode(size, pygame.RESIZABLE)
            window.blit(pygame.transform.smoothscale(self.app.render(), viewport.size), viewport.offset)
            pygame.display.flip()


if __name__ == "__main__":
    unittest.main()
