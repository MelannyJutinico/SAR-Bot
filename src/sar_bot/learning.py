"""Evaluación determinista de políticas DQN sobre el entorno real."""

from sar_bot.env import RescueEnv, RewardConfig


def evaluate_model(model, scenarios, rewards: RewardConfig | None = None):
    results = []
    for scenario in scenarios:
        env = RescueEnv([scenario], rewards)
        observation, _ = env.reset(seed=0)
        episode_return = 0.0
        while True:
            action, _ = model.predict(observation, deterministic=True)
            observation, reward, terminated, truncated, info = env.step(int(action))
            episode_return += reward
            if terminated or truncated:
                break
        state = env.simulation.state
        results.append({
            "scenario": scenario.name, "strategy": "dqn", "outcome": state.outcome,
            "success": info["is_success"], "rescued": len(state.rescued), "steps": state.steps,
            "damage_total": sum(r.damage for r in state.robots),
            "integrity_robot_1": state.robots[0].integrity,
            "integrity_robot_2": state.robots[1].integrity,
            "return": episode_return,
        })
        env.close()
    return results


def model_score(results):
    """Selección de desarrollo: rescates completos, víctimas y finalmente retorno."""
    return (sum(r["success"] for r in results), sum(r["rescued"] for r in results),
            sum(r["return"] for r in results))
