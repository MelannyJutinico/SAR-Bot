"""Evaluación determinista de políticas DQN sobre el entorno real."""

from sar_bot.env import RescueEnv, RewardConfig


def observation_mode_for_model(model, scenario):
    profile = getattr(model, "sar_bot_profile", None)
    if profile and profile.get("schema_version") != 2:
        raise ValueError("El esquema de observación de este modelo no es compatible")
    if profile and (profile["width"], profile["height"], profile["victims"]) != (
            scenario.width, scenario.height, scenario.victim_count):
        raise ValueError("Modelo incompatible: tamaño de edificio o cantidad de personas distintos")
    modes = {(RescueEnv.observation_size(scenario.width, scenario.height, scenario.victim_count, mode),): mode
             for mode in ("full", "sensors")}
    try:
        mode = modes[model.observation_space.shape]
        if profile and profile.get("mode") != mode:
            raise ValueError("El perfil del modelo no coincide con su espacio de observación")
        return mode
    except KeyError:
        raise ValueError("El modelo no coincide con las dimensiones o esquema del escenario") from None


def evaluate_model(model, scenarios, rewards: RewardConfig | None = None):
    results = []
    if not scenarios:
        return results
    mode = observation_mode_for_model(model, scenarios[0])
    for scenario in scenarios:
        observation_mode_for_model(model, scenario)
    # Un mismo entorno comparte las tablas geométricas de los edificios.
    env = RescueEnv(scenarios, rewards, observation_mode=mode)
    try:
        return _evaluate_in_env(model, scenarios, env)
    finally:
        env.close()


def _evaluate_in_env(model, scenarios, env):
    results = []
    for index, scenario in enumerate(scenarios):
        observation, _ = env.reset(seed=0, options={"scenario_index": index})
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
            "scenario_id": scenario.fingerprint(), "victims_total": scenario.victim_count,
            "configuration_id": scenario.configuration_id,
            "success": info["is_success"], "rescued": len(state.rescued), "steps": state.steps,
            "damage_total": sum(r.damage for r in state.robots),
            "integrity_robot_1": state.robots[0].integrity,
            "integrity_robot_2": state.robots[1].integrity,
            "return": episode_return,
        })
    return results


def model_score(results):
    """Selección de desarrollo: rescates completos, víctimas y finalmente retorno."""
    return (sum(r["success"] for r in results), sum(r["rescued"] for r in results),
            sum(r["return"] for r in results))
