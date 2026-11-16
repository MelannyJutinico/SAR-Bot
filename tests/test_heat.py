import pytest

from sar_bot.core import HeatFieldConfig, Layout, RulesConfig, damage_rate, temperature_field


@pytest.mark.parametrize(
    "temperature, expected",
    [
        (-10.0, 0.0),
        (39.999, 0.0),
        (40.0, 2.0),
        (59.999, 2.0),
        (60.0, 5.0),
        (79.999, 5.0),
        (80.0, 10.0),
        (500.0, 10.0),
    ],
)
def test_umbrales_40_60_80_sin_huecos_ni_solapamientos(temperature, expected):
    assert damage_rate(temperature) == expected


def test_delta_t_escala_el_dano():
    assert RulesConfig(delta_t=1.0).damage_for(65.0) == 5.0
    assert RulesConfig(delta_t=0.5).damage_for(65.0) == 2.5


def test_franjas_de_dano_deben_ser_crecientes():
    with pytest.raises(ValueError):
        RulesConfig(damage_bands=((60.0, 5.0), (40.0, 2.0)))
    with pytest.raises(ValueError):
        RulesConfig(damage_bands=((40.0, 5.0), (60.0, 2.0)))


def test_campo_termico_decrece_con_la_distancia_al_foco():
    layout = Layout.from_text("t", "B.....\n......\n......")
    temps = temperature_field(layout, hotspot=(1, 4))
    assert temps[1, 4] == 95.0
    assert temps[1, 3] == 75.0
    assert temps[1, 2] == 55.0
    assert temps[1, 1] == 35.0
    assert temps[1, 0] == 25.0


def test_la_base_es_celda_segura():
    layout = Layout.from_text("t", "B..\n...")
    hot_base = temperature_field(layout, hotspot=(0, 1), config=HeatFieldConfig(safe_base=False))
    safe_base = temperature_field(layout, hotspot=(0, 1))
    assert hot_base[0, 0] == 75.0
    assert safe_base[0, 0] == 25.0
