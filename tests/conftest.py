from __future__ import annotations

import numpy as np
import pytest

from sar_bot.core import Layout, Scenario

AMBIENT = 25.0


def make_scenario(layout_text, victims, *, hot=None, starts=None, name="prueba"):
    """Escenario manual: temperatura ambiente salvo las celdas de ``hot`` ({pos: °C})."""
    layout = Layout.from_text(name, layout_text)
    temps = np.full(layout.shape, AMBIENT)
    for pos, temperature in (hot or {}).items():
        temps[pos] = temperature
    return Scenario(
        layout=layout,
        victims=tuple(victims),
        temperatures=temps,
        robot_starts=starts,
        scenario_id=name,
    )


@pytest.fixture
def scenario_factory():
    return make_scenario
