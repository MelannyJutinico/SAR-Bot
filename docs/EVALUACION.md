# Referencias y evaluación de desarrollo

## Qué existe

Las referencias no aprenden. Sirven para verificar escenarios y comparar con el primer modelo DQN, que ya fue entrenado y evaluado.

### Navegación automática: shortest

1. Asigna víctimas pendientes distintas a robots libres minimizando la suma de distancias de camino. Mantiene cada asignación mientras la víctima siga pendiente. Los empates se resuelven determinísticamente.
2. Un robot con carga tiene como objetivo la base. Un robot sin tarea también vuelve a la base.
3. Busca mediante BFS sobre pares de posiciones una secuencia con el menor número de pasos globales hasta los dos objetivos actuales.
4. Ejecuta la primera acción conjunta y vuelve a planificar desde el estado actualizado.

La búsqueda respeta obstáculos, espera, ocupación y prohibición de intercambio directo. Puede mover temporalmente un robot para dejar pasar al otro. Reutiliza `RescueSimulation.resolve_movement()`, la misma función que usa el motor; planificar no aplica daño ni avanza el reloj.

Ignora temperatura e integridad al elegir acciones. No garantiza el óptimo de la misión completa: optimiza los objetivos actuales con la asignación vigente. Tampoco incorpora cambios de carga durante la búsqueda hipotética; el estado real se actualiza después de cada acción y se replantean los objetivos. Si no encuentra un plan, espera y registra `planning_failures` hasta la finalización normal del entorno.

Es más fuerte que dos rutas geométricas independientes porque coordina movimientos para evitar conflictos. En un mapa 6 × 6 hay como máximo 1296 pares de posiciones; no se plantea como solución escalable a edificios grandes.

### Política aleatoria: random

Selecciona uniformemente una de las 25 acciones conjuntas. Incluye esperas e intentos contra obstáculos. Usa un generador local con semilla y no altera las reglas del entorno.

## Ejecución reproducible

Desde la raíz del repositorio:

```powershell
uv run --no-project --python 3.12 scripts/evaluate.py --seed 0
```

Salida: `outputs/reference_results.csv`. Cada fila contiene escenario, estrategia, semilla (solo para random), resultado, éxito, víctimas entregadas, pasos globales, daño e integridad por robot y número de fallos de planificación.

La lista por defecto son los archivos JSON del primer nivel de `scenarios/`. En la futura evaluación final se indicará explícitamente una partición de prueba; estos mapas ya se usaron para desarrollo.

## Primera ejecución medida

Fecha de registro: 12 de noviembre de 2026. Semilla de la política aleatoria: 0. Un episodio por combinación. La referencia determinista no utiliza semilla.

| Escenario | Estrategia | Finalización | Rescates | Pasos globales | Daño total |
|---|---|---|---:|---:|---:|
| rescate_inicial | shortest | Éxito | 2 | 10 | 18 |
| rescate_inicial | random | Destrucción | 0 | 24 | 136 |
| pasillo_compartido | shortest | Éxito | 2 | 20 | 0 |
| pasillo_compartido | random | Límite de tiempo | 0 | 100 | 17 |
| ruta_caliente | shortest | Éxito | 2 | 10 | 74 |
| ruta_caliente | random | Destrucción | 0 | 25 | 122 |

El daño total suma pérdida de integridad de ambos robots, por lo que puede superar 100. Una destrucción finaliza la misión aunque el otro robot todavía esté operativo.

Estos datos muestran que la referencia puede ejecutar rescates y que el escenario térmico cambia las consecuencias de una ruta. No demuestran aprendizaje, superioridad estadística ni generalización.

El escenario `pasillo_compartido` obliga a que los robots salgan de la base por una única celda; la referencia introduce una espera para evitar que se bloqueen. En `ruta_caliente`, la geometría coincide con `rescate_inicial` y cambia el campo térmico: la referencia mantiene sus decisiones y recibe más daño.

## Próximos pasos experimentales

- Mejorar la política a partir del primer entrenamiento ya ejecutado.
- Escenarios separados de entrenamiento, validación y prueba.
- Varias configuraciones y semillas; no repetir un mapa determinista para aparentar muestras distintas.
- Comparar rescates y éxito antes de interpretar menor daño o menor duración.

## Referencia adicional que considera temperatura

`thermal` usa Dijkstra sobre posiciones conjuntas con costo `1 + 2 × daño previsto de ambos robots` por paso. Reutiliza las reglas de movimiento y la asignación de víctimas de `shortest`. Replanifica para los objetivos actuales; no garantiza un óptimo global ni incorpora la integridad como restricción de búsqueda.

Se comprobó una misión completa en `ruta_caliente`: **35 pasos y 34 puntos de daño total**, frente a 10 pasos y 74 puntos de `shortest`. Confirma que existe una alternativa térmicamente más segura. La referencia no alimenta acciones ni demostraciones al entrenamiento DQN.

```powershell
uv run --no-project --python 3.12 scripts/demo.py --strategy thermal --scenario scenarios/ruta_caliente.json
```

Los comandos de comparación ahora incluyen `thermal` además de `shortest` y `random`. Las tablas históricas conservan los resultados originales, previos a esta referencia.

## Primer DQN: evaluación del modelo recargado

Se entrenó una única semilla (0), durante 82000 pasos, y se seleccionó el checkpoint de 42000 mediante controles de desarrollo. La carga desde archivo produjo estos resultados:

| Escenario | DQN: rescates | DQN: pasos | DQN: daño | Referencia: rescates | Referencia: pasos | Referencia: daño |
|---|---:|---:|---:|---:|---:|---:|
| warmup_sin_calor | 2 | 2 | 0 | 2 | 2 | 0 |
| navegacion_sin_calor | 2 | 10 | 0 | 2 | 10 | 0 |
| rescate_inicial | 2 | 10 | 18 | 2 | 10 | 18 |
| ruta_caliente | 2 | 10 | 74 | 2 | 10 | 74 |
| pasillo_compartido | 0 | 100 | 0 | 2 | 20 | 0 |

Los primeros cuatro escenarios aparecen en el currículo y se usaron para seleccionar el checkpoint. El pasillo compartido es una comprobación adicional fuera del currículo; tampoco constituye por sí solo una prueba estadística reservada. DQN agota el tiempo en ese mapa.

El modelo sin entrenar no completó ninguno de los primeros cuatro escenarios. Esto es evidencia de aprendizaje de la tarea en esos casos, pero el checkpoint seleccionado no supera la referencia ni demuestra adaptación al riesgo térmico. La política de daño cero que no entrega víctimas no debe considerarse mejor.

Los resultados completos y la evidencia están en `artifacts/initial_dqn/`. Para regenerar la misma comparación:

```powershell
uv run --extra rl python scripts/evaluate_dqn.py --model artifacts/initial_dqn/model.zip --scenarios scenarios/curriculum/warmup.json scenarios/curriculum/navigation.json scenarios/demo.json scenarios/ruta_caliente.json scenarios/pasillo_compartido.json
```

## Modelo recomendado: tercer experimento con sensores

El segundo experimento, iniciado desde el modelo original, completó cinco de los seis controles. El tercero se entrenó desde cero durante 155000 pasos con sensores locales adicionales. Se seleccionó el checkpoint de 60000 utilizando solo los seis controles de entrenamiento. Se volvió a cargar antes de comparar.

| Escenario de entrenamiento/control | DQN: rescates | DQN: pasos | DQN: daño | Ruta corta: pasos | Ruta corta: daño |
|---|---:|---:|---:|---:|---:|
| warmup_sin_calor | 2 | 3 | 0 | 2 | 0 |
| navegacion_sin_calor | 2 | 11 | 0 | 10 | 0 |
| paso_compartido_cercano | 2 | 6 | 0 | 5 | 0 |
| rescate_inicial | 2 | 13 | 18 | 10 | 18 |
| ruta_caliente | 2 | 10 | 74 | 10 | 74 |
| pasillo_compartido | 2 | 22 | 0 | 20 | 0 |

Una vez fijado el checkpoint se evaluaron las particiones nuevas:

| Partición | Escenario | Rescates DQN | Pasos DQN | Daño DQN | Daño ruta corta | Daño referencia térmica |
|---|---|---:|---:|---:|---:|---:|
| Validación | validacion_foco_desplazado | 2 | 14 | 22 | 22 | 22 |
| Validación | validacion_victimas_pasillo | 2 | 19 | 9 | 2 | 0 |
| Prueba | prueba_rescate_intermedio | 2 | 8 | 35 | 35 | 15 |
| Prueba | prueba_obstaculos_pasillo | 2 | 22 | 4 | 6 | 4 |

Todas las misiones DQN de estas tablas terminaron con éxito. Las dos particiones nuevas no se usaron para entrenar ni seleccionar este checkpoint. Solo hay una semilla y dos casos de prueba: no se presenta un porcentaje como estimación de rendimiento general.

El avance comprobado es completar el pasillo largo sin perder las otras tareas en el modelo seleccionado. No hay mejora térmica consistente: en un caso recibe menos daño que la ruta corta, en otro más, y la referencia térmica iguala o mejora el daño de DQN. Las trayectorias corresponden a planificación con mapa conocido y sensores de distancia, no a búsqueda a ciegas.

La etapa térmica final fue peor que el checkpoint seleccionado, tanto en este experimento como en los anteriores. El registro conserva todos los controles para evitar mostrar solo el último modelo o combinar éxitos de políticas distintas.

Archivos reproducibles: `artifacts/sensors_dqn/comparison.csv`, `validation.csv`, `test.csv`, sus metadatos y `summary.json`. Cada evaluación registra el mismo hash del modelo congelado. Si estos casos de prueba se usan para diseñar futuros cambios, habrá que reclasificarlos como desarrollo y reservar otros para la entrega final.
