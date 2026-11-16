import pytest

from sar_bot.config import CONFIGS_DIR, load_config


def test_configuracion_base_coincide_con_las_reglas_acordadas():
    config = load_config()
    assert config.name == "base"
    assert config.rules.initial_integrity == 100.0
    assert config.rules.max_steps == 100
    assert config.rules.damage_bands == ((40.0, 2.0), (60.0, 5.0), (80.0, 10.0))
    assert config.scenarios.n_victims == 2
    assert config.training.net_arch == (256, 256)


def test_herencia_entre_configuraciones():
    base = load_config(CONFIGS_DIR / "base.toml")
    sin_calor = load_config(CONFIGS_DIR / "sin_calor.toml")
    una = load_config(CONFIGS_DIR / "una_victima.toml")
    assert sin_calor.heat.peak == sin_calor.heat.ambient == 25.0
    assert sin_calor.reward == base.reward and sin_calor.rules == base.rules
    assert una.scenarios.n_victims == 1 and una.heat.peak == 25.0


def test_claves_desconocidas_producen_error(tmp_path):
    bad = tmp_path / "mala.toml"
    bad.write_text("[reward]\ndelivry = 5.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="delivry"):
        load_config(bad)


def test_semillas_de_validacion_y_prueba_no_se_solapan(tmp_path):
    bad = tmp_path / "solape.toml"
    bad.write_text("[scenarios]\nvalidation_seeds = [0, 10]\ntest_seeds = [5, 20]\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(bad)
