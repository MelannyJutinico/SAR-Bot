"""Comportamiento del borrador y transformación del mapa sin dependencias gr?ficas."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sar_bot.core import Scenario
from sar_bot.ui.editor import ScenarioDraft, Viewport, pixel_to_cell


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.template = Scenario.load(ROOT / "scenarios/v2/building_10x10.json")
        self.draft = ScenarioDraft(self.template)

    def test_select_each_person_and_reject_invalid_selection(self):
        for i in range(3):
            self.draft.select(i)
            self.assertEqual(self.draft.selected, i)
        for i in (-1, 3, True):
            with self.assertRaises(ValueError):
                self.draft.select(i)

    def test_place_relocate_and_build_preserves_original(self):
        original = self.template.to_dict()
        self.draft.clear()
        for i, position in enumerate(((1, 0), (0, 1), (1, 1))):
            self.draft.select(i)
            self.assertTrue(self.draft.place(position))
        self.draft.select(0)
        self.assertTrue(self.draft.place((2, 0)))
        custom = self.draft.build()
        self.assertEqual(custom.victims, ((2, 0), (0, 1), (1, 1)))
        self.assertEqual(custom.temperatures, self.template.temperatures)
        self.assertEqual(custom.walls, self.template.walls)
        self.assertEqual(custom.heat_sources, self.template.heat_sources)
        self.assertEqual(original, self.template.to_dict())
        self.assertNotEqual(custom.configuration_id, self.template.configuration_id)

    def test_occupied_cell_keeps_previous_position(self):
        before = self.draft.positions
        self.assertFalse(self.draft.place(before[1]))
        self.assertEqual(before, self.draft.positions)
        self.assertIn("ocupada", self.draft.message)

    def test_wall_base_outside_and_invalid_types(self):
        before = self.draft.positions
        for position in (next(iter(self.template.walls)), self.template.base,
                         (-1, 0), (self.template.width, 0), (0, self.template.height),
                         (True, 1), (1.5, 0), None):
            with self.subTest(position=position):
                self.assertFalse(self.draft.place(position))
                self.assertTrue(self.draft.invalid)
                self.assertEqual(before, self.draft.positions)

    def test_disconnected_cell_is_rejected_by_core(self):
        scenario = Scenario("island", 4, 4, (0, 0), ((1, 0), (0, 1), (1, 1)),
                            frozenset({(2, 3), (3, 2)}), ((25.0,) * 4,) * 4)
        draft = ScenarioDraft(scenario)
        self.assertFalse(draft.place((3, 3)))
        self.assertIn("conectadas", draft.message)

    def test_clear_incomplete_build_and_restore(self):
        self.draft.clear()
        self.assertEqual(self.draft.positions, (None, None, None))
        self.assertEqual(self.draft.missing, 3)
        self.assertTrue(self.draft.place((1, 0)))
        self.assertEqual(self.draft.missing, 2)
        with self.assertRaisesRegex(ValueError, "Faltan 2"):
            self.draft.build()
        self.draft.restore()
        self.assertEqual(self.draft.missing, 0)
        self.assertEqual(self.draft.build().configuration_id, self.template.configuration_id)

    def test_two_person_template_is_not_silently_expanded(self):
        scenario = Scenario.load(ROOT / "scenarios/demo.json")
        with self.assertRaises(ValueError):
            ScenarioDraft(scenario)

    def test_pixel_to_cell_edges_and_controls(self):
        grid = (60, 246, 36)
        for pixel, expected in (((60, 246), (0, 0)), ((491.9, 677.9), (11, 11)),
                                ((59.99, 246), None), ((492, 246), None),
                                ((60, 678), None), ((900, 300), None)):
            self.assertEqual(pixel_to_cell(pixel, grid, (12, 12)), expected)

    def test_resize_and_letterbox_preserve_same_cell(self):
        logical = (60 + 7 * 36 + 18, 246 + 4 * 36 + 18)
        for size in ((1280, 860), (800, 600), (1920, 1080), (600, 1000)):
            viewport = Viewport(size)
            physical = tuple(viewport.offset[i] + logical[i] * viewport.size[i] / viewport.canvas[i]
                             for i in range(2))
            self.assertEqual(pixel_to_cell(viewport.logical(physical), (60, 246, 36), (12, 12)), (7, 4))
            self.assertEqual(viewport.logical((-1, -1)), (-1, -1))
            if viewport.offset[0]:
                self.assertEqual(viewport.logical((viewport.offset[0] - 0.1, 300)), (-1, -1))


if __name__ == "__main__":
    unittest.main()
