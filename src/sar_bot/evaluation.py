"""Un episodio por escenario y estrategia; sin resultados de aprendizaje."""

from sar_bot.core import RescueSimulation


def evaluate_episode(simulation: RescueSimulation, policy, strategy: str,
                     seed: int | None = None) -> dict:
    """Consume un simulador y política nuevos, desde su estado inicial."""
    if simulation.state.steps != 0 or simulation.state.outcome != "running":
        raise ValueError("La evaluación requiere un episodio nuevo")
    planning_failures = 0
    while simulation.state.outcome == "running":
        action = policy.act(simulation.state)
        if not getattr(policy, "last_plan_found", True):
            planning_failures += 1
        simulation.step(action)
    state = simulation.state
    return {
        "scenario": simulation.scenario.name,
        "scenario_id": simulation.scenario.fingerprint(),
        "victims_total": simulation.scenario.victim_count,
        "strategy": strategy,
        "seed": seed,
        "outcome": state.outcome,
        "success": state.outcome == "success",
        "rescued": len(state.rescued),
        "steps": state.steps,
        "damage_robot_1": state.robots[0].damage,
        "damage_robot_2": state.robots[1].damage,
        "damage_total": sum(r.damage for r in state.robots),
        "integrity_robot_1": state.robots[0].integrity,
        "integrity_robot_2": state.robots[1].integrity,
        "planning_failures": planning_failures,
        "replans": getattr(policy, "replans", 0),
        "expanded_states": getattr(policy, "total_expanded", 0),
    }
