"""SARB-013: snapshot, metricas, asincronia y regresiones de vistas."""
import csv
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from concurrent.futures import Future
from threading import Event
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
from sar_bot.core import Scenario, RescueSimulation
from sar_bot.agents import create_policy
from sar_bot.evaluation import evaluate_episode
from sar_bot.ui.app import RescueApp
from sar_bot.ui.comparison import Comparison, ComparisonRequest, ComparisonRow, run_strategy

class DeferredExecutor:
    def __init__(self): self.jobs = []
    def submit(self, fn, *args):
        future = Future();future.set_running_or_notify_cancel()
        self.jobs.append((future, fn, args));return future
    def shutdown(self, **kwargs): pass
    def finish(self, index):
        future, fn, args = self.jobs[index]
        future.set_result(fn(*args))

class ComparisonTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        self.app = RescueApp(ROOT, ROOT / "scenarios/v2/warmup_10x10.json", "shortest", asynchronous=False)
    def tearDown(self): self.app.close();pygame.quit()
    def finish(self):
        for _ in range(1000):
            self.app.update(0)
            if not self.app.comparison.futures: return
            time.sleep(.01)
        self.fail("Comparison timeout")
    def request(self):
        return ComparisonRequest(1, (), self.app.scenario, None, 17)

    def test_identical_initial_conditions_edited_positions_and_metrics(self):
        original = self.app.scenario
        self.app.action("edit");self.app.editor.clear()
        for i,pos in enumerate(((2,0),(0,3),(1,2))):
            self.app.editor.select(i);self.app.editor.place(pos)
        self.app.action("compare");self.finish()
        comparison = self.app.comparison
        frozen = comparison.request.scenario
        self.assertEqual(frozen.victims, ((2,0),(0,3),(1,2)))
        self.assertEqual(original.victims, ((1,0),(0,1),(1,1)))
        initial = RescueSimulation(frozen).state
        for row in comparison.rows.values():
            if row.episode:
                self.assertEqual(row.episode.configuration_id, frozen.configuration_id)
                self.assertEqual(row.episode.states[0], initial)
                self.assertEqual(row.episode.scenario.victims, frozen.victims)
                state = row.episode.states[-1]
                self.assertEqual(row.metrics, (len(state.rescued),state.outcome,state.steps,sum(r.damage for r in state.robots)))
        sim = RescueSimulation(frozen)
        reference = evaluate_episode(sim,create_policy(sim,"random",seed=0),"random",0)
        self.assertEqual(comparison.rows["random"].metrics[2],reference["steps"])

    def test_compatible_dqn_uses_selected_checkpoint(self):
        self.app.model_path = ROOT / "artifacts/v2_pilot/model.zip"
        self.app.action("compare");self.finish()
        row = self.app.comparison.rows["dqn"]
        self.assertEqual(row.status,"completed")
        self.assertIsNotNone(row.episode)
        self.assertEqual(self.app.comparison.request.model,str(self.app.model_path.resolve()))

    def test_incompatible_twelve_by_twelve_dqn_not_substituted(self):
        self.app.models=tuple(m for m in self.app.models if m.dimensions!=(12,12,3))
        self.app.scenario_index = next(i for i,(p,_) in enumerate(self.app.options) if p.name=="coordination_hub_12x12.json")
        self.app._select();self.app.action("compare");self.finish()
        row=self.app.comparison.rows["dqn"]
        self.assertEqual(row.status,"incompatible");self.assertIsNone(row.metrics)
        self.assertIn("DQN no disponible",row.error)
        self.assertTrue(all(self.app.comparison.rows[s].status=="completed" for s in ("shortest","thermal","random")))

    def test_missing_model_does_not_run_as_reference(self):
        request=ComparisonRequest(1,(),self.app.scenario,"missing.zip",0)
        row=run_strategy(request,"dqn",Event())
        self.assertEqual(row.status,"failed");self.assertIsNone(row.episode)
        self.app.model_path=ROOT/"missing.zip";self.app.action("compare")
        self.assertEqual(self.app.comparison.rows["dqn"].status,"incompatible")

    def test_strategy_error_isolated_and_pending_visible(self):
        pool=DeferredExecutor();comparison=Comparison(self.request(),"No compatible",pool)
        self.addCleanup(comparison.close)
        with patch("sar_bot.ui.comparison.prepare_episode",side_effect=RuntimeError("fallo controlado")):
            pool.finish(0)
        comparison.poll()
        self.assertEqual(comparison.rows["shortest"].status,"failed")
        self.assertEqual(comparison.rows["thermal"].status,"pending")
        pool.finish(2);pool.finish(1);comparison.poll()
        self.assertEqual(comparison.rows["random"].status,"completed")
        self.assertEqual(comparison.rows["thermal"].status,"completed")

    def test_out_of_order_results_keep_strategy_identity(self):
        pool=DeferredExecutor();comparison=Comparison(self.request(),"No compatible",pool)
        self.addCleanup(comparison.close)
        pool.finish(2);comparison.poll()
        self.assertEqual(comparison.rows["random"].status,"completed")
        self.assertEqual(comparison.rows["shortest"].status,"pending")
        pool.finish(1);pool.finish(0);comparison.poll()
        self.assertTrue(all(r.status=="completed" for s,r in comparison.rows.items() if s!="dqn"))

    def test_old_request_cannot_overwrite_new_even_if_running(self):
        pool=DeferredExecutor()
        with patch("sar_bot.ui.app.ThreadPoolExecutor",return_value=pool):
            self.app.action("compare");old=self.app.comparison
            self.app.action("compare");current=self.app.comparison
        future=pool.jobs[0][0]
        future.set_result(ComparisonRow("shortest","failed",error="old result"))
        old.poll();self.app.update(0)
        self.assertIs(self.app.comparison,current)
        self.assertTrue(old.cancelled.is_set())
        self.assertEqual(current.rows["shortest"].status,"pending")
        current.owns_executor=False;old.owns_executor=False

    def test_context_changes_invalidate_pending_comparison(self):
        for field,value in (("strategy_index",2),("model_path",ROOT/"other.zip"),("seed",44)):
            self.app.action("compare");old=self.app.comparison
            setattr(self.app,field,value);self.app.update(0)
            self.assertIsNone(self.app.comparison);self.assertTrue(old.cancelled.is_set())
        self.app.action("compare");self.app._enter_editor()
        self.assertIsNone(self.app.comparison)
        self.app.action("compare");self.app.scenario_index=0;self.app._select()
        self.assertIsNone(self.app.comparison)

    def test_individual_result_preserved_tabs_and_replay_do_not_compute(self):
        self.app.action("play");self.app.update(100)
        result=self.app.last_result
        self.app.action("compare");self.finish();comparison=self.app.comparison
        self.assertIs(self.app.last_result,result)
        with patch("sar_bot.ui.app.prepare_mission") as prepare:
            for view in ("preparation","execution","analysis"):
                self.app.set_view(view);self.app.render()
            self.app.action("replay_shortest")
            self.assertEqual(self.app.playback.index,0)
            self.app.action("play");self.app.update(100)
            prepare.assert_not_called()
        self.assertIs(self.app.comparison,comparison)
        self.assertIs(self.app.last_result,result)

    def test_imported_snapshot_export_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"scenario.json"
            scenario=self.app.scenario.with_victims(((2,0),(0,3),(1,2)))
            scenario.save(path)
            self.app.store.directory=Path(directory)
            self.app._start_file("load",path.name)
            self.app.action("compare");self.finish()
            comparison=self.app.comparison
            self.assertEqual(comparison.request.scenario.configuration_id,scenario.configuration_id)
            exported=comparison.export(Path(directory))
            with exported.open(encoding="utf-8",newline="") as stream: rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),4)
            self.assertEqual({r["configuration_id"] for r in rows},{scenario.configuration_id})
            replay=run_strategy(comparison.request,"random",Event())
            self.assertEqual(replay.episode.actions,comparison.rows["random"].episode.actions)

    def test_return_to_preparation_after_replay_restores_initial_preview(self):
        self.app.action("compare");self.finish()
        comparison=self.app.comparison
        self.app.action("replay_random");self.app.action("play");self.app.update(100)
        self.app.set_view("preparation")
        self.assertIs(self.app.comparison,comparison)
        self.assertEqual(self.app.state,RescueSimulation(self.app.scenario).state)
        self.assertFalse(self.app.comparison_replaying)

    def test_invalid_draft_never_submitted(self):
        self.app.action("edit");self.app.editor.clear()
        with patch("sar_bot.ui.app.Comparison") as constructor:
            self.app.action("compare");constructor.assert_not_called()
        self.assertIsNone(self.app.comparison)

    def test_close_detaches_and_signals_running_workers(self):
        self.app.action("compare");comparison=self.app.comparison
        self.app.close()
        self.assertTrue(comparison.cancelled.is_set())
        self.assertIsNone(self.app.comparison)

if __name__=="__main__":unittest.main()
