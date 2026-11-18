# Comparación unificada y diccionario de métricas (SARB-020)

**Responsable:** persona 4. **Revisa:** persona 1. **Actualización:** 18 de noviembre de 2026.

Este documento describe cómo se comparan DQN y las tres referencias sobre los mismos casos, qué significa cada columna del CSV y cómo comprobar que los números salen del motor. Es la base para la evaluación final (SARB-021), las gráficas (SARB-022) y el estudio de escala (SARB-031).

## 1. Garantías

- **Mismo caso para todas.** DQN, ruta corta, ruta térmica y aleatoria reciben el mismo `Scenario`: posiciones, temperaturas, integridad inicial y límite de pasos. Las columnas `scenario_id`, `configuration_id`, `scenario_sha256` y `max_steps` lo hacen visible en cada fila.
- **Episodio limpio.** Cada fila crea un `RescueEnv`, una `RescueSimulation` y una política nuevos. No se reutilizan estados, planes ni memoria de una misión anterior; las pruebas comparan un caso evaluado solo y evaluado después de otro.
- **Sin interfaz.** La evaluación no usa Pygame ni el reloj visual. La velocidad de reproducción no interviene en ninguna métrica.
- **Métricas desde la traza.** Todas las métricas de resultado se calculan a partir de la secuencia de estados del motor. Las acciones de cada episodio se guardan, y `--verify` las reproduce en un motor nuevo y compara fila por fila.
- **Un solo perfil por evaluación.** No se mezclan edificios de tamaños o cantidades de personas distintos, y un modelo incompatible con el perfil se rechaza antes de ejecutar.
- **Prueba protegida.** La partición `test` solo se abre con `--final`, sin `--limit`, y debe hacerse con los modelos congelados de SARB-019.

## 2. Tres semillas que no se mezclan

| Columna | Qué controla | De dónde sale |
|---|---|---|
| `generation_seed` | Las posiciones de las personas del escenario | Manifiesto de particiones (SARB-009) |
| `training_seed` | El entrenamiento del modelo DQN | `config.seed` en `metadata.json` del modelo |
| `random_seed` | Las acciones de la referencia aleatoria | Argumento `--random-seeds` (por defecto 0 a 4) |

La ruta corta y la térmica son deterministas: se ejecutan una vez por caso, porque repetirlas no aporta evidencia. DQN se ejecuta una vez por modelo y caso, con acciones deterministas.

## 3. Diccionario de columnas

El orden de las columnas es fijo (`sar_bot.experiment.COLUMNS`). Una prueba comprueba que esta tabla documenta todas y solo esas columnas.

| Columna | Significado |
|---|---|
| `episode_id` | Identificador del episodio: hash de configuración, estrategia, modelo, semilla aleatoria y peso térmico |
| `partition` | `training`, `validation`, `test` o una etiqueta de desarrollo |
| `manifest_id` | Manifiesto de particiones de origen; vacío en listas libres |
| `scenario_path` | Ruta del escenario relativa al repositorio |
| `scenario_name` | Nombre interno del escenario |
| `building` | Clave del edificio en el manifiesto (`hub`, `detour`) |
| `difficulty` | Familia de generación: `easy`, `intermediate` o `demanding` |
| `scenario_id` | Firma física, independiente del orden de etiquetas de las personas |
| `configuration_id` | Identidad exacta, incluido el orden de las personas |
| `scenario_sha256` | Hash del archivo de escenario con finales de línea LF |
| `width` | Ancho del edificio |
| `height` | Alto del edificio |
| `generation_seed` | Semilla que generó las posiciones del caso |
| `strategy` | `dqn`, `shortest`, `thermal` o `random` |
| `model_label` | Nombre del modelo DQN (carpeta del artefacto) |
| `model_sha256` | Hash del archivo del modelo DQN |
| `training_seed` | Semilla de entrenamiento del modelo DQN |
| `random_seed` | Semilla de acciones de la referencia aleatoria |
| `thermal_damage_weight` | Peso del daño en el costo de la referencia térmica |
| `victims_total` | Personas del escenario |
| `rescued` | Personas entregadas en la base |
| `success` | `True` si se entregaron todas y ambos robots siguen operativos |
| `outcome` | `success`, `destroyed` o `time_limit` |
| `steps` | Pasos simulados hasta finalizar; no es tiempo de cómputo |
| `max_steps` | Límite de pasos del escenario |
| `damage_robot_1` | Daño térmico acumulado del robot 1 |
| `damage_robot_2` | Daño térmico acumulado del robot 2 |
| `damage_total` | Suma del daño de ambos robots |
| `integrity_robot_1` | Integridad final del robot 1 (empieza en 100) |
| `integrity_robot_2` | Integridad final del robot 2 |
| `deliveries_robot_1` | Personas entregadas por el robot 1 |
| `deliveries_robot_2` | Personas entregadas por el robot 2 |
| `wait_actions` | Acciones individuales de esperar, sumando ambos robots |
| `blocked_moves` | Movimientos pedidos que no cambiaron la posición de un robot operativo (pared, borde o colisión) |
| `planning_failures` | Pasos en que la referencia no encontró plan; 0 para DQN |
| `replans` | Replanificaciones de la referencia; 0 para DQN y aleatoria |
| `expanded_states` | Estados expandidos por la búsqueda de la referencia |
| `return` | Retorno del episodio según la función de recompensa indicada en `reward_config_sha256` |
| `reward_config_sha256` | Hash de la configuración de recompensas usada para `return` |
| `actions_sha256` | Hash de la secuencia de acciones conjuntas guardada en las trazas |
| `compute_seconds` | Segundos de cómputo en la máquina que evaluó; no es tiempo simulado y varía entre ejecuciones |

Las entregas por robot, las esperas y los bloqueos describen lo observado en la traza. No prueban por sí solos que haya una cooperación mejor.

## 4. Cómo leer los resultados

- **Primero el éxito.** Una misión fallida con poco daño no es mejor que un rescate completo. El resumen solo promedia pasos y daño entre misiones exitosas, y siempre muestra el denominador.
- **El retorno depende de su recompensa.** Solo es comparable entre filas con el mismo `reward_config_sha256`. Con un modelo, el retorno usa por defecto las recompensas de sus metadatos; con varios modelos de recompensas distintas hay que fijar `--rewards`.
- **Casos relacionados.** Varias estrategias o modelos sobre el mismo mapa producen datos emparejados, no mapas independientes. `configurations` cuenta los casos distintos y `episodes` las filas.
- **Sesgo de certificación.** Los casos de las particiones se aceptaron porque una referencia los resolvió. Las tasas de éxito de las referencias en ellas están infladas por construcción (ver `docs/PARTICIONES_V2.md`).

## 5. Uso

```powershell
# Referencias sobre la validación congelada 12 × 12.
uv run --extra rl python scripts/evaluate_experiment.py --manifest configs/partitions/v2_12x12.json --split validation --strategies shortest thermal random --rewards configs/dqn_v2_pilot.json --output outputs/eval/validacion.csv

# DQN y referencias sobre escenarios de desarrollo (perfil 10 × 10).
uv run --extra rl python scripts/evaluate_experiment.py --scenarios scenarios/v2/warmup_10x10.json scenarios/v2/building_10x10.json --model artifacts/v2_pilot/model.zip --output outputs/eval/piloto.csv

# Varias semillas DQN en una sola tabla (SARB-019/021): repetir --model.
uv run --extra rl python scripts/evaluate_experiment.py --manifest configs/partitions/v2_12x12.json --split test --final --model <semilla0>/model.zip --model <semilla1>/model.zip --model <semilla2>/model.zip --output results/final/test.csv

# Comprobar un CSV ya escrito.
uv run --extra rl python scripts/evaluate_experiment.py --verify outputs/eval/validacion.csv
```

Cada ejecución escribe tres archivos: el CSV, `<nombre>.traces.jsonl` con las acciones de cada episodio y `<nombre>.metadata.json`. Los metadatos registran el commit y si había cambios sin guardar, las versiones, el manifiesto y su hash, los hashes de escenarios y modelos, las semillas, la recompensa y los hashes del CSV y de las trazas. Al terminar, el script reproduce todas las trazas y falla si alguna métrica no coincide.

`scripts/evaluate_dqn.py` se conserva por compatibilidad con los resultados históricos. Las comparaciones nuevas usan `scripts/evaluate_experiment.py`.

## 6. Comparación pequeña reproducible

Se guardan en `results/sarb020/` como evidencia de esta tarea. Ninguna usa la partición de prueba.

**Referencias sobre la validación 12 × 12** (`v2_12x12_validation_referencias.csv`): 20 casos, 140 episodios (aleatoria con cinco semillas por caso).

| Estrategia | Éxitos | Rescates | Pasos medios (éxitos) | Daño medio (éxitos) | Destruidos | Límite de pasos |
|---|---:|---:|---:|---:|---:|---:|
| Ruta corta | 17/20 | 57/60 | 34,8 | 38,0 | 3 | 0 |
| Ruta térmica | 20/20 | 60/60 | 41,0 | 10,1 | 0 | 0 |
| Aleatoria | 0/100 | 55/300 | — | — | 60 | 40 |

La ruta térmica tarda unos 6 pasos más en promedio y recibe mucho menos daño. La ruta corta pierde un robot en tres casos. Este es el conflicto entre distancia y calor que la comparación en pantalla (SARB-013) debe mostrar. La tasa de la térmica está favorecida porque fue ella la que certificó los casos.

**Piloto DQN 10 × 10 en desarrollo** (`v2_10x10_piloto_desarrollo.csv`): `artifacts/v2_pilot/model.zip` y referencias en `warmup_10x10` y `building_10x10`. El piloto resuelve el calentamiento y agota el límite de pasos en el edificio, como ya documentaba `docs/EVALUACION.md`. No es un resultado del perfil final.

Para regenerar ambas tablas se usan los comandos guardados en el campo `command` de cada archivo de metadatos.
