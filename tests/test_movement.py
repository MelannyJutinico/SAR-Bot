"""Convenciones de movimiento simultáneo (docs/CONTEXTO.md §6)."""

import pytest

from sar_bot.core import Action, Layout, resolve_moves

U, D, L, R, W = Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT, Action.WAIT

# Base en (0, 0); obstáculo en (1, 1).
LAYOUT = Layout.from_text(
    "movimiento",
    """
    B....
    .#...
    .....
    """,
)


def test_limites_y_obstaculos_bloquean_y_el_robot_se_queda():
    res = resolve_moves(LAYOUT, ((0, 1), (2, 4)), (D, R))
    assert res.positions == ((0, 1), (2, 4))
    assert res.blocked_by_wall == (True, True)
    assert res.blocked_by_robot == (False, False)


def test_movimiento_libre():
    res = resolve_moves(LAYOUT, ((0, 1), (2, 2)), (R, U))
    assert res.positions == ((0, 2), (1, 2))
    assert res.blocked_by_wall == (False, False)
    assert res.blocked_by_robot == (False, False)


def test_mismo_destino_fuera_de_la_base_bloquea_a_ambos():
    res = resolve_moves(LAYOUT, ((0, 2), (0, 4)), (R, L))
    assert res.positions == ((0, 2), (0, 4))
    assert res.blocked_by_robot == (True, True)


def test_intercambio_directo_bloquea_a_ambos():
    res = resolve_moves(LAYOUT, ((0, 2), (0, 3)), (R, L))
    assert res.positions == ((0, 2), (0, 3))
    assert res.blocked_by_robot == (True, True)


def test_entrar_en_celda_que_el_otro_abandona_esta_permitido():
    res = resolve_moves(LAYOUT, ((0, 2), (0, 3)), (R, R))
    assert res.positions == ((0, 3), (0, 4))
    assert res.blocked_by_robot == (False, False)


def test_entrar_en_celda_de_robot_que_espera_queda_bloqueado():
    res = resolve_moves(LAYOUT, ((0, 2), (0, 3)), (R, W))
    assert res.positions == ((0, 2), (0, 3))
    assert res.blocked_by_robot == (True, False)


def test_entrar_en_celda_de_robot_bloqueado_por_obstaculo_queda_bloqueado():
    # El robot 1 intenta bajar hacia el obstáculo (1, 1) y no puede salir de (0, 1).
    res = resolve_moves(LAYOUT, ((0, 2), (0, 1)), (L, D))
    assert res.positions == ((0, 2), (0, 1))
    assert res.blocked_by_wall == (False, True)
    assert res.blocked_by_robot == (True, False)


def test_la_base_admite_ambos_robots():
    res = resolve_moves(LAYOUT, ((0, 0), (0, 1)), (W, L))
    assert res.positions == ((0, 0), (0, 0))
    assert res.blocked_by_robot == (False, False)


def test_desde_la_base_no_pueden_salir_ambos_a_la_misma_celda():
    res = resolve_moves(LAYOUT, ((0, 0), (0, 0)), (R, R))
    assert res.positions == ((0, 0), (0, 0))
    assert res.blocked_by_robot == (True, True)


def test_desde_la_base_salen_a_celdas_distintas():
    res = resolve_moves(LAYOUT, ((0, 0), (0, 0)), (R, D))
    assert res.positions == ((0, 1), (1, 0))


def test_intercambio_con_la_base_tambien_se_bloquea():
    res = resolve_moves(LAYOUT, ((0, 0), (0, 1)), (R, L))
    assert res.positions == ((0, 0), (0, 1))
    assert res.blocked_by_robot == (True, True)


@pytest.mark.parametrize("a0", list(Action))
@pytest.mark.parametrize("a1", list(Action))
def test_nunca_comparten_celda_fuera_de_la_base(a0, a1):
    for p0, p1 in [((0, 2), (0, 3)), ((1, 2), (0, 2)), ((2, 1), (1, 0)), ((0, 0), (0, 1))]:
        res = resolve_moves(LAYOUT, (p0, p1), (a0, a1))
        q0, q1 = res.positions
        assert q0 != q1 or q0 == LAYOUT.base
        assert LAYOUT.is_free(q0) and LAYOUT.is_free(q1)
