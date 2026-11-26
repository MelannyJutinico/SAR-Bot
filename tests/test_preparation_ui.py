"""SARB-011: escenario real editado e invalidacion determinista de trabajadores."""
import os
from pathlib import Path
import sys
import unittest
from concurrent.futures import Future, CancelledError
from dataclasses import replace
from threading import Event
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["SDL_VIDEODRIVER"] = "dummy"
try:
    import pygame
except ImportError:
    pygame = None


class QueuedExecutor:
    def __init__(self):
        self.jobs = []

    def submit(self, fn, *args):
        future = Future()
        future.set_running_or_notify_cancel()  # cancel() no puede detenerlo
        self.jobs.append((future, fn, args))
        return future

    def finish(self, index, result=None):
        future, fn, args = self.jobs[index]
        try:
            future.set_result(fn(*args) if result is None else result)
        except Exception as error:
            future.set_exception(error)

    def shutdown(self, **kwargs):
        pass


@unittest.skipIf(pygame is None, "Instalar extra ui")
class PreparationUITests(unittest.TestCase):
    def setUp(self):
        from sar_bot.ui.app import RescueApp
        pygame.display.init(); pygame.font.init()
        self.app = RescueApp(ROOT, ROOT / "scenarios/v2/warmup_10x10.json",
                             "shortest", asynchronous=False)
        self.original = self.app.options[self.app.scenario_index][1].to_dict()

    def tearDown(self):
        self.app.close(); pygame.quit()

    def edit(self, positions=((2, 0), (0, 2), (1, 1))):
        self.app.action("edit"); self.app.action("editor_clear")
        for i, position in enumerate(positions):
            self.app.editor.select(i)
            self.assertTrue(self.app.editor.place(position))
        return self.app.editor.build()

    def test_real_episode_uses_exact_three_positions_and_original_is_unchanged(self):
        custom = self.edit()
        self.app.action("editor_apply")
        episode = self.app.playback.episode
        self.assertEqual(episode.scenario.victims, custom.victims)
        self.assertEqual(episode.configuration_id, custom.configuration_id)
        self.assertEqual(self.app.state.steps, 0)
        self.assertFalse(self.app.playback.playing)
        self.assertEqual(episode.states[-1].outcome, "success")
        self.assertEqual(len(episode.states[-1].rescued), 3)
        self.assertEqual(self.original, self.app.options[self.app.scenario_index][1].to_dict())
        self.assertEqual(self.app.validation_status, "certified")

    def test_incomplete_draft_never_reaches_worker(self):
        self.edit(); self.app.action("editor_clear")
        with patch("sar_bot.ui.app.prepare_mission") as worker:
            self.app.action("editor_apply")
            worker.assert_not_called()
        self.assertIsNotNone(self.app.editor)
        self.assertIsNone(self.app.playback)
        self.assertEqual(self.app.validation_status, "structural_invalid")

    def test_invalid_draft_is_rejected_by_public_core_api(self):
        self.edit()
        with patch.object(type(self.app.editor), "build", side_effect=ValueError("invalid")):
            with patch("sar_bot.ui.app.prepare_mission") as worker:
                self.app.action("editor_apply"); worker.assert_not_called()
        self.assertTrue(self.app.editor.invalid)

    def test_strategy_reset_and_return_keep_edited_configuration(self):
        custom = self.edit(); self.app.action("editor_apply")
        first = self.app.playback.episode
        self.app.action("play"); self.app.update(1)
        self.app.strategy_index = 2; self.app._select()
        self.assertEqual(self.app.scenario.configuration_id, custom.configuration_id)
        self.assertEqual(self.app.request.strategy, "thermal")
        self.assertEqual(self.app.state.steps, 0)
        self.assertTrue(all(r.integrity == 100 and r.carrying is None for r in self.app.state.robots))
        self.app.action("play"); self.app.update(100); self.app.action("reset")
        self.assertEqual(self.app.state.steps, 0)
        self.app.action("edit")
        self.assertEqual(self.app.editor.positions, custom.victims)
        self.app.action("editor_apply")
        self.app.strategy_index = 1; self.app._select()
        self.assertEqual(first.states, self.app.playback.episode.states)

    def test_noncertified_configuration_can_be_explored_without_substitution(self):
        from sar_bot.core import certify_viability
        self.edit()
        with patch("sar_bot.ui.preparation.certify_viability",
                   side_effect=lambda s: certify_viability(s, action_budget=0)):
            self.app.action("editor_apply")
        self.assertEqual(self.app.validation_status, "not_certified")
        self.assertEqual(self.app.request.strategy, "shortest")
        self.assertIsNotNone(self.app.playback)
        self.app.render((125.5, 310.2))
        self.app.action("play"); self.app.update(100)
        self.assertEqual(self.app.state.outcome, "success")

    def test_model_error_is_visible_without_fallback(self):
        self.edit(); self.app.strategy_index = 0
        self.app.model_path = ROOT / "tmp/nonexistent-model-sarb011.zip"
        self.app.action("editor_apply")
        self.assertTrue(self.app.error)
        self.assertIsNone(self.app.playback)
        self.assertEqual(self.app.request.strategy, "dqn")
        self.app.render()

    def test_running_old_result_and_old_error_cannot_overwrite_new_configuration(self):
        old = self.app.request
        from sar_bot.ui.preparation import prepare_mission
        previous = prepare_mission(old, self.app.scenario, Event())
        queue = QueuedExecutor(); self.app.executor = queue
        self.app._prepare(); pending = self.app.future; token = self.app.cancelled
        custom = self.edit(); self.app.action("editor_apply")
        self.assertTrue(token.is_set())
        self.assertFalse(pending.cancelled())
        queue.finish(1); self.app.update(0)
        current = self.app.playback
        self.app._accept(previous)
        pending.set_exception(ValueError("old error")); self.app.update(0)
        self.assertIs(self.app.playback, current)
        self.assertIsNone(self.app.error)
        self.assertEqual(current.episode.configuration_id, custom.configuration_id)

    def test_rapid_scenarios_and_strategies_accept_only_latest(self):
        queue = QueuedExecutor(); self.app.executor = queue
        for path in ("building_10x10.json", "demo.json", "warmup_10x10.json"):
            self.app.scenario_index = next(i for i,(p,_) in enumerate(self.app.options) if p.name == path)
            self.app._select()
        self.app.strategy_index = 2; self.app._select()
        queue.finish(3); self.app.update(0)
        accepted = self.app.playback
        for i in (2,0,1):queue.finish(i)
        self.app.update(0)
        self.assertIs(self.app.playback, accepted)
        self.assertEqual(self.app.request.strategy, "thermal")
        self.assertEqual(accepted.episode.configuration_id, self.app.scenario.configuration_id)

    def test_generation_distinguishes_repeated_identical_requests(self):
        old = self.app.request
        self.app._prepare()
        self.assertNotEqual(old, self.app.request)
        self.assertEqual(old.configuration_id, self.app.request.configuration_id)

    def test_label_permutation_has_new_exact_identity(self):
        custom = self.edit(); self.app.action("editor_apply"); first = self.app.request
        self.edit(tuple(reversed(custom.victims))); self.app.action("editor_apply")
        self.assertEqual(self.app.scenario.scenario_id, custom.scenario_id)
        self.assertNotEqual(first.configuration_id, self.app.request.configuration_id)

    def test_real_worker_runs_off_main_thread_and_edit_invalidates_it(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import get_ident
        from sar_bot.ui.preparation import prepare_mission
        entered, release = Event(), Event()
        main_thread = get_ident()
        threads = []

        def blocked(*args):
            threads.append(get_ident()); entered.set()
            if not release.wait(5):
                raise TimeoutError("test worker")
            return prepare_mission(*args)

        self.app.executor = ThreadPoolExecutor(max_workers=2)
        with patch("sar_bot.ui.app.prepare_mission", blocked):
            self.app._prepare(); future = self.app.future
            try:
                self.assertTrue(entered.wait(3))
                self.app.update(0); self.app.render((125.5, 310.2))
                self.app.action("edit")
                self.assertIsNotNone(self.app.editor)
                self.assertNotEqual(threads[0], main_thread)
            finally:
                release.set()
            with self.assertRaises(CancelledError):future.result(timeout=5)
            self.app.update(0)
            self.assertIsNone(self.app.playback)

    def test_worker_cancellation_and_wrong_result_identity(self):
        from sar_bot.ui.preparation import prepare_mission
        from sar_bot.ui.playback import prepare_episode
        event = Event(); event.set()
        for run in (lambda: prepare_mission(self.app.request, self.app.scenario, event),
                    lambda: prepare_episode(self.app.scenario, "shortest", cancel_event=event)):
            with self.assertRaises(CancelledError):run()
        result = prepare_mission(self.app.request, self.app.scenario, Event())
        self.app.playback = None
        self.app._accept(replace(result, request=replace(result.request, strategy="random")))
        self.assertIsNone(self.app.playback)


if __name__ == "__main__":unittest.main()
