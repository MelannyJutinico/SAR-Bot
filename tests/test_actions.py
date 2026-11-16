import pytest

from sar_bot.core import N_JOINT_ACTIONS, Action, decode_joint, encode_joint


def test_hay_25_acciones_conjuntas_y_la_codificacion_es_biyectiva():
    codes = {encode_joint(a0, a1) for a0 in Action for a1 in Action}
    assert N_JOINT_ACTIONS == 25
    assert codes == set(range(25))
    for a0 in Action:
        for a1 in Action:
            assert decode_joint(encode_joint(a0, a1)) == (a0, a1)


def test_formula_de_la_accion_conjunta():
    assert encode_joint(Action.RIGHT, Action.UP) == 5 * 3 + 0
    assert decode_joint(24) == (Action.WAIT, Action.WAIT)


@pytest.mark.parametrize("joint", [-1, 25, 100])
def test_accion_conjunta_fuera_de_rango(joint):
    with pytest.raises(ValueError):
        decode_joint(joint)
