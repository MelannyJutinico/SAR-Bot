import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402

from sar_bot.config import load_config  # noqa: E402
from sar_bot.core import Action  # noqa: E402
from sar_bot.env import RescueEnv  # noqa: E402
from sar_bot.ui.renderer import Renderer  # noqa: E402


def test_render_produce_imagen_y_refleja_cambios_de_estado():
    config = load_config()
    env = RescueEnv(config, "validation", render_mode="rgb_array")
    env.reset()
    first = env.render()
    renderer = Renderer((6, 6), config.rules)
    assert first.shape == (renderer.size[1], renderer.size[0], 3)
    assert first.dtype == np.uint8
    env.sim.step(Action.RIGHT, Action.DOWN)
    assert not np.array_equal(first, env.render())


def test_render_no_modifica_el_estado():
    env = RescueEnv(load_config(), "validation", render_mode="rgb_array")
    env.reset()
    before = (env.sim.step_count, env.sim.positions, [r.integrity for r in env.sim.robots])
    env.render()
    env.render()
    assert before == (env.sim.step_count, env.sim.positions, [r.integrity for r in env.sim.robots])
