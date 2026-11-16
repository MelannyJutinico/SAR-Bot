# Diseño técnico de la base

Este documento describe el contrato implementado en `src/sar_bot/`. Las reglas de fondo y su justificación están en [CONTEXTO.md](CONTEXTO.md); aquí se registra cómo quedaron en código y qué decisiones nuevas se tomaron al implementarlas.

## Estado

| Componente | Estado | Módulo | Responsable siguiente |
|---|---|---|---|
| Plano, acciones y acción conjunta | Hecho | `core/grid.py`, `core/actions.py` | Persona 2 |
| Daño térmico y campo de calor | Hecho | `core/rules.py`, `core/heat.py` | Persona 2 |
| Escenarios reproducibles y viabilidad | Hecho | `core/scenario.py`, `scenarios/layouts/` | Persona 2 |
| Motor de paso global | Hecho | `core/engine.py` | Persona 2 |
| Configuración y etapas | Hecho | `config.py`, `configs/` | Persona 1 |
| Adaptador Gymnasium, observación y recompensa | Hecho | `env/` | Persona 1 |
| Particiones entrenamiento / validación / prueba | Hecho | `env/sampling.py` | Personas 1 y 4 |
| Estrategia de referencia | Hecho | `agents/baseline.py` | Persona 4 |
| Entrenamiento DQN, guardado y carga | Hecho, sin ajuste de hiperparámetros | `agents/dqn.py`, `training.py`, `scripts/train.py` | Persona 1 |
| Evaluación por episodio a CSV | Hecho | `evaluation.py`, `scripts/evaluate.py` | Persona 4 |
| Render Pygame y demo | Hecho, versión mínima | `ui/renderer.py`, `scripts/play.py` | Persona 3 |
| Pruebas | 111 pruebas | `tests/` | Todos |

## Convenciones

- Posiciones `(fila, columna)`; la fila 0 está arriba.
- Acciones individuales: `UP=0`, `DOWN=1`, `LEFT=2`, `RIGHT=3`, `WAIT=4`.
- Acción conjunta: `5 × acción_robot_0 + acción_robot_1`, en `[0, 25)`. Se usan `encode_joint` y `decode_joint`.
- El código usa identificadores en inglés y comentarios en español.
- El motor es la única fuente de reglas. Entorno, interfaz, referencia y evaluación lo consumen; no recalculan daño ni deciden rescates.

## Paso global

`RescueSim.step(a0, a1)` (o `step_joint(j)`) sigue el orden de CONTEXTO.md §5:

1. Resuelve destinos, obstáculos y conflictos (`resolve_moves`).
2. Mueve a ambos robots y les aplica exposición térmica en su celda final, aunque esperen o queden bloqueados.
3. Si algún robot llega a integridad 0, termina en `robot_destruido` sin procesar entregas de ese paso.
4. Si no, procesa entregas en la base y recogidas automáticas.
5. Termina en `exito` si todas las víctimas están rescatadas; si no, en `limite_de_pasos` al alcanzar `max_steps`.

Cada paso devuelve un `StepResult` con posiciones, bloqueos, temperaturas, daño, recogidas, entregas y finalización. `terminated` corresponde a éxito o destrucción; `truncated`, al límite de pasos.

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
- Campo de un foco fijo: `T = max(25, 95 − 20 × distancia_Manhattan)`. Queda en 95 °C sobre el foco, 75 a distancia 1, 55 a distancia 2 y como mucho 35 desde distancia 3. Se ajusta en `[heat]`.
- La base se fuerza a temperatura ambiente (celda segura).

### Hallazgo para decidir en equipo

Con el calor actual, la referencia que ignora el calor completa el 100 % de los 150 escenarios de validación, con 17,7 de daño total medio. Evitando el calor, el daño podría bajar a unos 5 de media. Por tanto, el margen de mejora del agente aprendido está en **reducir daño y mantener la duración**, no en rescatar más.

Con un calor más severo (pico 100 y gradiente 15), la referencia sigue completando 149 de 150, pero el daño medio sube a 46,4. Si el equipo quiere que ignorar el calor cause fracasos, hay que endurecer `[heat]` o las franjas de daño. Es una decisión de la persona 2 que debe registrarse antes de comparar resultados.

## Escenarios y particiones

Los planos son archivos de texto en `scenarios/layouts/`: `.` libre, `#` obstáculo, `B` base. Hay tres de 6 × 6 (`edificio_a`, `edificio_b`, `edificio_c`), todos conexos.

`generate_scenario(plano, semilla)` es reproducible. Reglas del generador:

- Ambos robots empiezan en la base.
- Las víctimas quedan en celdas libres distintas, a una distancia de camino de al menos 2 desde la base.
- El foco queda en una celda libre a una distancia Manhattan de al menos 3 de la base.
- Se descartan los escenarios que `estimate_viability` considera inviables. Es una estimación aproximada: ignora conflictos entre robots. La referencia confirma la viabilidad completando los escenarios en el motor.

Particiones (`env/sampling.py`):

- **Validación:** cada plano con las semillas `[100000, 100050)`, es decir, 150 escenarios fijos.
- **Prueba:** cada plano con las semillas `[200000, 200100)`, es decir, 300 escenarios fijos.
- **Entrenamiento:** plano y semilla aleatorios. Se descarta cualquier escenario con la misma misión (plano, celdas de víctimas y foco) que uno de validación o prueba.

## Configuración y etapas

`configs/*.toml` tiene las secciones `[rules]`, `[heat]`, `[scenarios]`, `[reward]` y `[training]`. Un archivo puede heredar con `extends`. Las claves desconocidas producen error.

| Archivo | Etapa (CONTEXTO.md §8) |
|---|---|
| `una_victima.toml` | 1: una víctima, sin calor, dos robots en el entorno |
| `sin_calor.toml` | 2: dos víctimas sin calor, para validar coordinación |
| `base.toml` | 3: dos víctimas con calor |

## Entorno Gymnasium

`RescueEnv(config, split)` está registrado como `SARBot-v0`.

- **Acción:** `Discrete(25)`.
- **Observación:** vector `float32` de 227 valores en [0, 1] para planos de 6 × 6.
  - Seis capas del mapa: obstáculos, calor (tasa / tasa máxima), base, robot 0, robot 1 y víctimas esperando.
  - Integridad relativa y carga de cada robot.
  - Estado one-hot de cada víctima, con ceros si no existe.
  - Fracción de pasos restantes.
- **Recompensa compartida** (`[reward]`):

| Evento | Valor inicial |
|---|---:|
| Cada paso | −0,05 |
| Cada punto de daño (suma de ambos robots) | −0,1 |
| Recogida (una vez por víctima) | +2 |
| Entrega | +10 |
| Misión completa | +20 |
| Robot destruido | −20 |
| Choque o bloqueo | 0 |

- **`info`:** `scenario_id`, `step`, `outcome`, `rescued`, `integrity` y `step_result`. Al terminar incluye además `is_success` y `metrics`, las métricas del episodio más `return`.
- `reset(options={"scenario": s})` fuerza un escenario concreto.

## Estrategia de referencia

`ShortestPathBaseline` sigue estas reglas (detalle en el docstring de `agents/baseline.py`):

- Asigna víctimas distintas minimizando la suma de distancias de camino, y reasigna cuando cambia el estado de las víctimas.
- Sigue rutas más cortas que ignoran el calor.
- Ante un bloqueo, cede el robot sin prioridad. Tiene prioridad el que transporta una víctima; si ambos o ninguno, el más cercano a su objetivo; si empatan, el robot 0. El que cede elige la acción que no bloquea al otro y deja menor distancia a su objetivo. Prefiere esperar y, si hace falta, se aparta en un pasillo.

Completa el 100 % de validación y prueba en las tres etapas.

## Entrenamiento

`scripts/train.py` entrena DQN (`MlpPolicy`, red 256×256, CPU). Evalúa en los 150 escenarios de validación cada `eval_freq` pasos y guarda:

- `models/<corrida>/best_model.zip`: el de mejor retorno medio en validación.
- `models/<corrida>/final_model.zip`.
- `models/<corrida>/metadata.json`: configuración completa, versiones y duración.
- `runs/<corrida>/`: registros de Monitor y `evaluations.npz`.

Los hiperparámetros iniciales no están ajustados.

## Evaluación

`scripts/evaluate.py` ejecuta una o varias estrategias sobre la partición fija de validación o prueba y exporta un CSV con una fila por episodio. Las columnas son `strategy`, `split`, `layout`, `scenario_id`, `seed`, `outcome`, `success`, `rescued`, `victims`, `steps`, `damage_r0`, `damage_r1`, `damage_total`, `integrity_r0`, `integrity_r1`, `wall_bumps`, `robot_blocks` y `return`.

El resumen por consola reporta tasa de éxito, destrucción y límite, rescates, daño y retorno. Los pasos y el daño también se calculan solo entre misiones exitosas, para no favorecer fracasos tempranos (CONTEXTO.md §9).

## Visualización

`scripts/play.py` reproduce una estrategia sobre validación o prueba con Pygame. Controles:

- Espacio: pausa o continúa.
- →: avanza un paso en pausa.
- R: reinicia el escenario.
- N / B: escenario siguiente o anterior.
- + / −: velocidad.
- E: cambia de estrategia.
- Esc: sale.

La velocidad solo cambia cuántos pasos se muestran por segundo; no altera el tiempo simulado, el calor ni el daño. El render (`ui/renderer.py`) solo lee el estado del motor.

## Decisiones tomadas al implementar (revisar en equipo)

- Los robots empiezan en la base, y ninguna víctima puede estar en la base ni en la celda inicial de un robot.
- El campo de calor usa distancia Manhattan y los obstáculos no lo bloquean.
- El intercambio directo se bloquea también cuando involucra la base.
- La observación usa capas one-hot del mapa en lugar de coordenadas, para que una red densa generalice entre planos.
- Los valores de recompensa e hiperparámetros son iniciales. Deben fijarse y registrarse antes de comparar resultados.
- Los choques no se penalizan por ahora (`blocked = 0`).

## Ejemplo de uso

```python
from sar_bot.core import Action, RescueSim, generate_scenario, load_layouts

layout = load_layouts()["edificio_a"]
sim = RescueSim(generate_scenario(layout, seed=0))
result = sim.step(Action.RIGHT, Action.DOWN)
print(sim.to_text())
print(result.damage, result.outcome)
```
