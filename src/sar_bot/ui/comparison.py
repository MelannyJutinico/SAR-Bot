"""Comparaciones congeladas: sin dependencia de Pygame ni reglas del motor."""
from concurrent.futures import CancelledError, ThreadPoolExecutor
from dataclasses import dataclass
from threading import Event
import csv
from uuid import uuid4
from types import MappingProxyType
from pathlib import Path
from .local_files import atomic_text
from sar_bot.core import Scenario
from .playback import Episode, prepare_episode

STRATEGIES = ("dqn", "shortest", "thermal", "random")

@dataclass(frozen=True)
class ComparisonRequest:
    generation: int
    context: tuple
    scenario: Scenario
    model: str | None
    seed: int

@dataclass(frozen=True)
class ComparisonRow:
    strategy: str
    status: str
    episode: Episode | None = None
    error: str = ""

    @property
    def metrics(self):
        if self.episode is None:
            return None
        state = self.episode.states[-1]
        return (len(state.rescued), state.outcome, state.steps,
                sum(robot.damage for robot in state.robots))


def run_strategy(request, strategy, cancelled):
    try:
        episode = prepare_episode(request.scenario, strategy,
                                  request.model if strategy == "dqn" else None,
                                  request.seed, cancel_event=cancelled)
        if cancelled.is_set():
            raise CancelledError()
        if episode.configuration_id != request.scenario.configuration_id:
            raise ValueError("El episodio no coincide con la configuracion congelada")
        return ComparisonRow(strategy, "completed", episode)
    except CancelledError:
        raise
    except Exception as error:
        return ComparisonRow(strategy, "failed", error=str(error) or type(error).__name__)


class Comparison:
    def __init__(self, request, dqn_problem=None, executor=None):
        self.request = request
        self.cancelled = Event()
        self.executor = executor or ThreadPoolExecutor(max_workers=4)
        self.owns_executor = executor is None
        self.rows = {s: ComparisonRow(s, "pending") for s in STRATEGIES}
        self.futures = {}
        for strategy in STRATEGIES:
            if strategy == "dqn" and dqn_problem:
                self.rows[strategy] = ComparisonRow(strategy, "incompatible", error=dqn_problem)
            else:
                self.futures[strategy] = self.executor.submit(run_strategy, request, strategy, self.cancelled)

    def poll(self):
        if self.cancelled.is_set():
            return
        for strategy, future in tuple(self.futures.items()):
            if not future.done():
                continue
            del self.futures[strategy]
            try:
                row = future.result()
                if row.strategy != strategy or (row.episode is not None and
                        row.episode.configuration_id != self.request.scenario.configuration_id):
                    raise ValueError("Resultado ajeno a esta comparacion")
                self.rows[strategy] = row
            except Exception as error:
                self.rows[strategy] = ComparisonRow(strategy, "failed", error=str(error))
        if not self.futures and self.owns_executor:
            self.executor.shutdown(wait=False)

    def close(self):
        self.cancelled.set()
        for future in self.futures.values():
            future.cancel()
        if self.owns_executor:
            self.executor.shutdown(wait=False, cancel_futures=True)

    def snapshot(self):
        if self.futures or self.cancelled.is_set():
            raise ValueError("Espera a que termine la comparacion vigente")
        return CompletedComparison(self.request, tuple(self.rows.values()))

    def export(self, directory):
        return self.snapshot().export(directory)


@dataclass(frozen=True)
class CompletedComparison:
    request: ComparisonRequest
    entries: tuple[ComparisonRow, ...]
    futures: tuple = ()

    @property
    def rows(self):
        return MappingProxyType({row.strategy: row for row in self.entries})

    def export(self, directory):
        import json
        path = Path(directory) / ("comparison-" + uuid4().hex + ".csv")
        scenario = self.request.scenario
        rows = [("scenario_id", "configuration_id", "strategy", "model", "seed", "status",
                 "rescued", "outcome", "steps", "damage_total", "error", "scenario_json")]
        for row in self.entries:
            rows.append((scenario.scenario_id, scenario.configuration_id, row.strategy,
                         self.request.model if row.strategy == "dqn" else "", self.request.seed,
                         row.status, *(row.metrics or ("", "", "", "")), row.error,
                         json.dumps(scenario.to_dict(), ensure_ascii=True)))
        expected = [["" if value is None else str(value) for value in row] for row in rows]
        def validate(temporary):
            with temporary.open(encoding="utf-8", newline="") as stream:
                if list(csv.reader(stream)) != expected:
                    raise ValueError("El CSV escrito no coincide con la comparacion")
        with atomic_text(path, validate) as stream:
            csv.writer(stream).writerows(rows)
        return path
