"""Prueba de humo: DQN entrena unos pasos, se guarda, se carga y actúa.

No verifica que aprenda; solo que el circuito completo funciona.
"""

import dataclasses
import json

from sar_bot.agents.dqn import DQNPolicy
from sar_bot.config import load_config
from sar_bot.evaluation import evaluate
from sar_bot.training import train


def test_entrenar_guardar_cargar_y_evaluar(tmp_path):
    config = load_config()
    config = dataclasses.replace(
        config,
        scenarios=dataclasses.replace(config.scenarios, validation_seeds=(100_000, 100_002)),
        training=dataclasses.replace(
            config.training, learning_starts=50, buffer_size=1_000, batch_size=16, eval_freq=300, net_arch=(32,)
        ),
    )
    model_dir = train(
        config, "humo", total_timesteps=600, models_dir=tmp_path / "models", runs_dir=tmp_path / "runs", verbose=0
    )
    assert (model_dir / "final_model.zip").exists()
    assert (model_dir / "best_model.zip").exists()
    metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["total_timesteps"] == 600
    assert metadata["validation_episodes"] == 6

    policy = DQNPolicy.load(model_dir / "final_model.zip")
    rows = evaluate(policy, config, "validation", limit=2)
    assert len(rows) == 2 and all(r["strategy"] == "dqn" for r in rows)
