"""Reproduce rescates programados o estrategias de referencia, sin aprendizaje."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.core import Action, RescueSimulation, Scenario
from sar_bot.agents import RandomPolicy, ShortestPathPolicy


def render(simulation):
    scenario, state = simulation.scenario, simulation.state
    cells = [[" ." for _ in range(scenario.width)] for _ in range(scenario.height)]
    for x, y in scenario.walls:
        cells[y][x] = " #"
    for victim_id, (x, y) in enumerate(scenario.victims):
        if victim_id not in state.rescued and not any(
            r.carrying == victim_id for r in state.robots
        ):
            cells[y][x] = " V"
    x, y = scenario.base
    cells[y][x] = " B"
    for i, robot in enumerate(state.robots):
        x, y = robot.position
        cells[y][x] = "12" if state.robots[0].position == state.robots[1].position else f" {i+1}"
    print(f"\nPaso {state.steps} | {state.outcome} | Rescatados: {len(state.rescued)}/2")
    print("\n".join(" ".join(row) for row in cells))
    for i, robot in enumerate(state.robots):
        print(f"Robot {i+1}: integridad={robot.integrity}, daño={robot.damage}, "
              f"carga={robot.carrying}, T={scenario.temperature_at(robot.position):g} C")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Una instantánea JSON por paso")
    parser.add_argument("--strategy", choices=("scripted", "shortest", "random"), default="scripted")
    parser.add_argument("--scenario", type=Path, default=ROOT / "scenarios" / "demo.json")
    parser.add_argument("--seed", type=int, default=0, help="Semilla de la estrategia aleatoria")
    args = parser.parse_args()
    if args.strategy == "scripted" and args.scenario.resolve() != (ROOT / "scenarios/demo.json").resolve():
        parser.error("La secuencia scripted solo es válida para el escenario demo.json")
    simulation = RescueSimulation(Scenario.load(args.scenario))
    emit = (lambda s: print(json.dumps(s.snapshot(), ensure_ascii=False))) if args.json else render
    emit(simulation)
    # Ruta reproducible para este escenario: ida por dos bordes y vuelta a la base.
    # No es una estrategia general ni una política aprendida.
    plan = [(Action.RIGHT, Action.DOWN)] * 5 + [(Action.LEFT, Action.UP)] * 5
    policy = (ShortestPathPolicy(simulation) if args.strategy == "shortest" else
              RandomPolicy(simulation, args.seed) if args.strategy == "random" else None)
    while simulation.state.outcome == "running":
        if policy is None:
            if simulation.state.steps >= len(plan):
                raise RuntimeError("La secuencia programada terminó sin completar la misión")
            action = simulation.encode_actions(*plan[simulation.state.steps])
        else:
            action = policy.act(simulation.state)
        simulation.step(action)
        emit(simulation)
    return 0 if simulation.state.outcome == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
