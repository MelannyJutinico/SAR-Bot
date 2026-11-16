"""Prueba de humo: DQN entrena unos pasos, se guarda, se carga y actúa.

No verifica que aprenda; solo que el circuito completo funciona.
"""

import dataclasses
import json

import numpy as np
import torch

from sar_bot.agents.dqn import DQNPolicy
from sar_bot.config import load_config
from sar_bot.evaluation import evaluate
from sar_bot.training import selection_key, train


def _small_config():
    config = load_config()
    return dataclasses.replace(
        config,
        scenarios=dataclasses.replace(config.scenarios, validation_seeds=(100_000, 100_002)),
        training=dataclasses.replace(
            config.training, learning_starts=50, buffer_size=1_000, batch_size=16, eval_freq=300, net_arch=(32,)
        ),
    )


def test_entrenar_guardar_cargar_y_evaluar(tmp_path):
    config = _small_config()
    model_dir = train(
        config, "humo", total_timesteps=600, models_dir=tmp_path / "models", runs_dir=tmp_path / "runs", verbose=0
    )
    assert (model_dir / "final_model.zip").exists()
    assert (model_dir / "best_model.zip").exists()
    metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["total_timesteps"] == 600
    assert metadata["validation_episodes"] == 6
    assert metadata["best"]["timesteps"] in (300, 600)
    assert 0.0 <= metadata["best"]["success_rate"] <= 1.0

    curve = np.load(tmp_path / "runs" / "humo" / "evaluations.npz")
    assert curve["timesteps"].tolist() == [300, 600]
    assert set(curve.files) == {"timesteps", "success_rate", "task_return", "damage", "steps_success"}

    policy = DQNPolicy.load(model_dir / "final_model.zip")
    rows = evaluate(policy, config, "validation", limit=2)
    assert len(rows) == 2 and all(r["strategy"] == "dqn" for r in rows)


def test_arrancar_desde_un_modelo_previo(tmp_path):
    config = _small_config()
    first = train(config, "a", total_timesteps=300, models_dir=tmp_path, runs_dir=tmp_path / "runs", verbose=0)
    no_learning = dataclasses.replace(
        config, training=dataclasses.replace(config.training, learning_starts=10_000, eval_freq=0)
    )
    second = train(
        no_learning,
        "b",
        total_timesteps=100,
        init_model=first / "final_model.zip",
        models_dir=tmp_path,
        runs_dir=tmp_path / "runs",
        verbose=0,
    )
    a = DQNPolicy.load(first / "final_model.zip").model.q_net.state_dict()
    b = DQNPolicy.load(second / "final_model.zip").model.q_net.state_dict()
    # Sin pasos de aprendizaje, los pesos del segundo modelo son los del primero.
    assert all(torch.equal(a[k], b[k]) for k in a)
    assert json.loads((second / "metadata.json").read_text(encoding="utf-8"))["init_model"].endswith("final_model.zip")


def test_la_seleccion_prioriza_exito_sobre_retorno():
    alto_exito = {"success_rate": 0.9, "task_return_mean": 10.0}
    alto_retorno = {"success_rate": 0.5, "task_return_mean": 80.0}
    mejor_retorno = {"success_rate": 0.9, "task_return_mean": 12.0}
    assert selection_key(alto_exito) > selection_key(alto_retorno)
    assert selection_key(mejor_retorno) > selection_key(alto_exito)
