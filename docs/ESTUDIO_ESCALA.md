# Escala, reparto de rescates y dificultad (SARB-031)

**Responsable:** persona 4. **Revisan:** personas 1 y 2. **Actualización:** 18 de noviembre de 2026.

Este estudio describe cómo cambian rescates, pasos y daño con el tamaño del edificio, la familia de dificultad, la separación entre personas y la exposición térmica inicial. Usa las referencias en todos los perfiles y los modelos DQN de desarrollo que ya existen, cada uno en su propio perfil. No abre la partición de prueba. La comparación con los modelos finales de 12 × 12 queda para cuando existan (SARB-019 y SARB-021).

Todas las cifras de este documento salen de [`results/sarb031/estudio/tablas.md`](../results/sarb031/estudio/tablas.md). Ese archivo se genera desde los CSV conservados y se comprueba con `scale_study.py check`.

## 1. Datos

| Conjunto | Perfil | Casos | Estrategias | CSV |
|---|---|---:|---|---|
| Escenarios 6 × 6 de desarrollo (sin los dos de prueba histórica) | 6 × 6, 2 personas | 8 | DQN `sensors_dqn`, referencias | `results/sarb031/v2_6x6_desarrollo.csv` |
| Escenarios fijos 10 × 10 (`warmup_10x10`, `building_10x10`) | 10 × 10, 3 personas | 2 | DQN `v2_pilot`, referencias | `results/sarb020/v2_10x10_piloto_desarrollo.csv` |
| Conjunto de desarrollo generado `v2_10x10_dev_v1` | 10 × 10, 3 personas | 30 | DQN `v2_pilot`, referencias | `results/sarb031/v2_10x10_desarrollo.csv` |
| Entrenamiento `v2_12x12_v1` | 12 × 12, 3 personas | 60 | Referencias | `results/sarb031/v2_12x12_training_referencias.csv` |
| Validación `v2_12x12_v1` | 12 × 12, 3 personas | 20 | Referencias | `results/sarb020/v2_12x12_validation_referencias.csv` |

La referencia aleatoria usa cinco semillas de acciones por caso (0 a 4). Las referencias deterministas se ejecutan una vez por caso y DQN una vez por modelo y caso.

### Conjunto de desarrollo 10 × 10

Solo había dos escenarios 10 × 10, así que no se podía estudiar la dificultad en ese tamaño. `v2_10x10_dev_v1` aplica el generador certificado de SARB-009 sobre `scenarios/v2/building_10x10.json`, con semilla de generación `1010001`. Produjo 30 casos, 10 por familia, en 66 intentos, y excluye la configuración de la plantilla.

- Registro: `configs/development/v2_10x10_dev.json`, con hashes y `content_sha256`.
- Escenarios: `scenarios/development/v2_10x10/`.
- Verificación: `python scripts/scale_study.py verify --record configs/development/v2_10x10_dev.json`.

**Es un conjunto de desarrollo, no una partición experimental.** No se usa para entrenar, elegir checkpoints ni afirmar generalización. Si el equipo reduce el alcance a 10 × 10 (SARB-002), la prueba de ese perfil necesita un manifiesto propio con otro `manifest_id`.

## 2. Resultados

### Escala (tabla 2)

- **Las referencias siguen resolviendo los casos al crecer el edificio.** La térmica completa 8/8 en 6 × 6, 30/30 en el conjunto 10 × 10, 60/60 en el entrenamiento 12 × 12 y 20/20 en la validación. La ruta corta completa 8/8, 26/30, 55/60 y 17/20. Sus fracasos son siempre por robot destruido. Esa tasa está favorecida por construcción: los casos generados entraron porque la térmica los resolvió al certificarlos.
- **El costo de planificar crece más que los pasos.** La mediana de estados expandidos de la térmica pasa de 239 en 6 × 6 a 2660 en el conjunto 10 × 10 y a entre 1588 y 2247 en 12 × 12. La de la ruta corta va de 12 a 554 y de 788 a 889. En los casos exigentes de 12 × 12 la térmica llega a 34 726 estados y unos 4 s de cómputo en un episodio (tabla 7). Los pasos simulados medianos de esos casos son 56. El cómputo depende de la máquina y no es tiempo simulado.
- **Los modelos DQN de desarrollo no escalan a posiciones nuevas.** `sensors_dqn` completa 8/8 en 6 × 6, pero son sus propios escenarios de entrenamiento y validación histórica. `v2_pilot` completa 1/2 en los dos escenarios fijos 10 × 10 con los que se entrenó. En los 30 casos con posiciones nuevas del mismo edificio completa 0/30 y entrega 9/90 personas.

### Dificultad por edificio y familia (tabla 3)

- **Las familias ordenan el esfuerzo de las referencias.** Con la térmica, los pasos medios en 10 × 10 son 12,4 (fácil), 40,4 (intermedio) y 62,6 (exigente). En 12 × 12 las cifras son parecidas en ambos edificios.
- **En los casos fáciles las dos referencias coinciden.** El Δ de pasos y de daño es 0 en las familias fáciles de los tres edificios, salvo −0,6 de daño en `hub`.
- **La ruta corta falla donde la distancia y el calor se combinan.** En la familia exigente completa 6/10 en 10 × 10 y 8/13 en el desvío térmico de 12 × 12. La térmica completa todos.
- **El edificio decide si existe una ruta segura.** En el desvío térmico (`detour`), la térmica paga entre 3,2 y 5,0 pasos más que la ruta corta y reduce el daño entre 57,6 y 124,8 puntos en los casos emparejados intermedios y exigentes. Su daño medio queda por debajo de 4. En el centro de coordinación (`hub`), el calor rodea los destinos. La térmica reduce menos el daño (−11,4 y −29,1) y sigue recibiendo entre 20 y 47 puntos de media.

### Separación entre personas (tabla 4)

En 12 × 12 los pasos medios de la térmica crecen con la separación: 27,6, 41,7 y 47,5 en los terciles bajo, medio y alto. La ruta corta falla en los tres terciles, entre 2 y 4 casos por tercil. Las esperas por episodio son bajas en las referencias (entre 0,8 y 3,5) y algo mayores en la térmica cuando la separación es alta en 10 × 10.

Esta tabla no está emparejada. Una referencia puede tener más éxitos que la otra en el mismo tercil, así que sus medias de pasos y daño cubren casos distintos. Las comparaciones emparejadas están en las tablas 3 y 5.

### Exposición térmica inicial (tabla 5)

En 12 × 12, cuantas más personas empiezan en zona de daño, más daño recibe la térmica: de media, 2,5 sin personas en calor, 30,2 con una, 36,1 con dos y 48,0 con tres, en casos emparejados. También necesita más pasos extra que la ruta corta: +1,4, +2,0, +4,3 y +6,5. La ruta corta recibe entre 29,5 y 81,5. Incluso sin personas en calor, la ruta corta pierde un robot en 5 de 53 casos, porque atraviesa calor en el camino aunque los destinos estén fríos.

### Reparto de trabajo observado (tabla 6)

- **Con tres personas, las referencias siempre reparten 2–1.** Cada robot lleva una persona a la vez, así que todo éxito incluye un segundo viaje. En ningún éxito de referencia un robot hizo los tres rescates.
- **Con dos personas, las referencias reparten 1–1 en los 8 casos 6 × 6.** `sensors_dqn` reparte 1–1 en 7 y 2–0 en 1.
- **Las referencias casi no esperan ni chocan.** Tienen 0 movimientos bloqueados y entre 0 y 2,3 esperas por episodio. Replanifican entre 4,0 y 4,4 veces por misión de tres personas.

Estas columnas describen la traza: cuántas personas entregó cada robot, cuántas veces esperó o chocó. No prueban que una estrategia coopere mejor ni revelan intenciones del controlador.

## 3. Cambio de comportamiento observado

**Política memorizada frente a posiciones nuevas.** En `warmup_10x10`, uno de sus escenarios de entrenamiento, `v2_pilot` completa el rescate en 6 pasos sin daño. En los 30 casos de `v2_10x10_dev_v1` (mismo edificio, posiciones nuevas) agota el límite de 240 pasos en todos. De media acumula 342,1 movimientos bloqueados y 80,0 esperas por episodio, y entrega 9 personas de 90. Las referencias, en los mismos casos, tienen 0 bloqueos.

Lo observable es que la política repite acciones que chocan contra paredes o contra el otro robot cuando las personas no están donde estaban al entrenar. Eso coincide con lo que motiva SARB-015 y SARB-016: entrenar con posiciones variables. No demuestra por qué la red elige esas acciones. Las trazas de cada episodio están en `results/sarb031/v2_10x10_desarrollo.traces.jsonl` y se pueden reproducir sin volver a entrenar.

**Rodeo térmico según el edificio.** En el desvío térmico, la térmica elige recorridos unos 3 a 5 pasos más largos que casi eliminan el daño. En el centro de coordinación, el mismo criterio solo lo reduce, porque no existe un rodeo frío hacia esos destinos. La diferencia está en la geometría del calor, no en otra regla del planificador.

## 4. Cómo regenerar

```powershell
# Conjunto de desarrollo (ya generado; el script se niega a sobrescribirlo).
uv run python scripts/scale_study.py generate --template scenarios/v2/building_10x10.json --set-id v2_10x10_dev_v1 --building building10 --seed 1010001 --requested 30 --record configs/development/v2_10x10_dev.json --scenario-dir scenarios/development/v2_10x10

# Evaluaciones (escriben CSV, trazas y metadatos con el commit).
uv run --extra rl python scripts/evaluate_experiment.py --scenarios scenarios/demo.json scenarios/pasillo_compartido.json scenarios/ruta_caliente.json scenarios/curriculum/warmup.json scenarios/curriculum/navigation.json scenarios/curriculum/handoff.json scenarios/validation/corridor_targets.json scenarios/validation/heat_shift.json --model artifacts/sensors_dqn/model.zip --output results/sarb031/v2_6x6_desarrollo.csv
uv run --extra rl python scripts/evaluate_experiment.py --development-set configs/development/v2_10x10_dev.json --model artifacts/v2_pilot/model.zip --rewards configs/dqn_v2_pilot.json --output results/sarb031/v2_10x10_desarrollo.csv
uv run --extra rl python scripts/evaluate_experiment.py --manifest configs/partitions/v2_12x12.json --split training --strategies shortest thermal random --rewards configs/dqn_v2_pilot.json --output results/sarb031/v2_12x12_training_referencias.csv

# Tablas del estudio y figuras de los dos conjuntos generados.
uv run python scripts/scale_study.py analyze --results results/sarb031/v2_6x6_desarrollo.csv results/sarb020/v2_10x10_piloto_desarrollo.csv results/sarb031/v2_10x10_desarrollo.csv results/sarb031/v2_12x12_training_referencias.csv results/sarb020/v2_12x12_validation_referencias.csv --output-dir results/sarb031/estudio
uv run python scripts/report_figures.py --results results/sarb031/v2_10x10_desarrollo.csv --output-dir results/sarb031/figuras_10x10_desarrollo
uv run python scripts/report_figures.py --results results/sarb031/v2_12x12_training_referencias.csv --output-dir results/sarb031/figuras_12x12_entrenamiento

# Comprobar sin volver a evaluar.
uv run python scripts/scale_study.py check results/sarb031/estudio
```

Los tres CSV nuevos se generaron desde el commit `8ccb90b` sin cambios pendientes, como registran sus metadatos.

## 5. Límites

- **Escala con factores mezclados.** 6 × 6 tiene dos personas y otros límites de pasos. La comparación entre tamaños no aísla el efecto del tamaño.
- **Sesgo de certificación.** Los casos generados se aceptaron porque la térmica los resolvió, así que su 100 de éxito no prueba que resuelva cualquier ubicación.
- **Pocos casos por celda.** Familias y terciles tienen entre 2 y 28 casos. Son descripciones y no pruebas de significancia.
- **DQN de desarrollo.** No hay modelos 12 × 12 todavía. `sensors_dqn` se evalúa en escenarios que vio al entrenar, y `v2_pilot` es un piloto de integración. Ningún checkpoint se evaluó en otro perfil.
- **Aleatoria correlacionada.** Con una misma semilla repite la misma secuencia de acciones en todos los casos (ver `docs/FIGURAS.md`).
- **Pendiente para SARB-021.** Repetir las tablas 2 a 6 con las tres semillas DQN finales sobre la prueba, sin juntar entrenamientos distintos en una sola curva.
