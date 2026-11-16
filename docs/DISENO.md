# Diseño técnico de la base

Este documento describe el contrato que ya está implementado en `src/sar_bot/core/`. Las reglas de fondo y su justificación están en [CONTEXTO.md](CONTEXTO.md); aquí se registra cómo quedaron en código y qué decisiones nuevas se tomaron al implementarlas.

## Estado

| Componente | Estado | Módulo |
|---|---|---|
| Plano, acciones y acción conjunta | Hecho | `core/grid.py`, `core/actions.py` |
| Daño térmico y campo de calor | Hecho | `core/rules.py`, `core/heat.py` |
| Escenarios reproducibles y viabilidad | Hecho | `core/scenario.py`, `scenarios/layouts/` |
| Motor de paso global | Hecho | `core/engine.py` |
| Verificaciones de reglas críticas | Hecho (85 pruebas) | `tests/` |
| Adaptador Gymnasium y recompensa | Pendiente (día 2) | `env/` |
| Estrategia de referencia | Pendiente (día 2) | `agents/` |
| Entrenamiento DQN | Pendiente (día 2) | `scripts/` |
| Render Pygame | Pendiente (día 2) | `ui/` |
| Evaluación por episodio | Pendiente | `scripts/` |

## Convenciones

- Posiciones `(fila, columna)`; la fila 0 está arriba.
- Acciones individuales: `UP=0`, `DOWN=1`, `LEFT=2`, `RIGHT=3`, `WAIT=4`.
- Acción conjunta: `5 × acción_robot_0 + acción_robot_1`, en `[0, 25)`. Se usan `encode_joint` y `decode_joint`.
- El código usa identificadores en inglés y comentarios en español.

## Paso global

`RescueSim.step(a0, a1)` (o `step_joint(j)`) sigue el orden de CONTEXTO.md §5:

1. Resuelve destinos, obstáculos y conflictos (`resolve_moves`).
2. Mueve a ambos robots y les aplica exposición térmica en su celda final, aunque esperen o queden bloqueados.
3. Si algún robot llega a integridad 0, termina en `robot_destruido` sin procesar entregas de ese paso.
4. Si no, procesa entregas en la base y recogidas automáticas.
5. Termina en `exito` si todas las víctimas están rescatadas; si no, en `limite_de_pasos` al alcanzar `max_steps`.

Cada paso devuelve un `StepResult` con posiciones, bloqueos, temperaturas, daño, recogidas, entregas y finalización. El entorno de Gymnasium calculará la recompensa a partir de esos eventos, sin recalcular reglas.

`terminated` corresponde a éxito o destrucción; `truncated`, al límite de pasos.

## Movimiento simultáneo

Implementa CONTEXTO.md §6:

- Un obstáculo o el borde del mapa bloquea el movimiento (`blocked_by_wall`).
- Si ambos robots apuntan a la misma celda fuera de la base, los dos se quedan (`blocked_by_robot`). Esto cubre entrar en la celda de un robot que espera o que choca con una pared.
- El intercambio directo se bloquea para ambos, incluso si uno está en la base.
- Seguir al otro robot (entrar en la celda que abandona) está permitido.
- En la base ambos pueden coincidir.

## Calor y daño

- Tasas por temperatura: menos de 40 °C → 0; de 40 a 60 → 2; de 60 a 80 → 5; desde 80 → 10. Cada franja es `[umbral, siguiente)`.
- `daño = tasa × delta_t` con `delta_t = 1`. La integridad se recorta en 0.
- `damage_taken` registra la integridad perdida, así que siempre se cumple `damage_taken = inicial − integridad`.
- Campo de un foco fijo: `T = max(25, 95 − 20 × distancia_Manhattan)`. Queda en 95 °C sobre el foco, 75 a distancia 1, 55 a distancia 2 y como mucho 35 desde distancia 3. Es un modelo inicial que puede ajustar la persona 2 en `HeatFieldConfig`.
- La base se fuerza a temperatura ambiente (celda segura).

## Escenarios

Los planos son archivos de texto en `scenarios/layouts/`: `.` libre, `#` obstáculo, `B` base. Por ahora hay tres de 6 × 6 (`edificio_a`, `edificio_b`, `edificio_c`), todos conexos.

`generate_scenario(plano, semilla)` es reproducible: la misma semilla produce el mismo escenario. Reglas del generador:

- Ambos robots empiezan en la base.
- Las víctimas quedan en celdas libres distintas, a una distancia de camino de al menos 2 desde la base.
- El foco queda en una celda libre a una distancia Manhattan de al menos 3 de la base.
- Se descartan los escenarios que `estimate_viability` considera inviables.

`estimate_viability` prueba cada reparto de víctimas y cada orden de visita con caminos de menor daño, y exige integridad mayor que 0 y que la misión quepa en `max_steps`. Es aproximada: ignora conflictos entre robots y la recogida automática al pasar sobre otra víctima. La confirmación definitiva será que la estrategia de referencia complete el escenario en el motor.

## Métricas por episodio

`RescueSim.episode_metrics()` devuelve: `scenario_id`, `seed`, `outcome`, `success`, `rescued`, `victims`, `steps`, `damage_r0`, `damage_r1`, `damage_total`, `integrity_r0`, `integrity_r1`, `wall_bumps` y `robot_blocks`. La evaluación añadirá la estrategia y el retorno.

## Decisiones tomadas al implementar (revisar en equipo)

- Los robots empiezan en la base, y ninguna víctima puede estar en la base ni en la celda inicial de un robot.
- El campo de calor usa distancia Manhattan y los obstáculos no lo bloquean.
- El intercambio directo se bloquea también cuando involucra la base.
- Se cuentan choques con paredes y bloqueos entre robots. No se penalizan por ahora; la recompensa se decidirá en `env/`.

## Ejemplo de uso

```python
from sar_bot.core import Action, RescueSim, generate_scenario, load_layouts

layout = load_layouts()["edificio_a"]
sim = RescueSim(generate_scenario(layout, seed=0))
result = sim.step(Action.RIGHT, Action.DOWN)
print(sim.to_text())
print(result.damage, result.outcome)
```
