# Evaluación del agente neuronal de asignación y riesgo

Tablas generadas por `scripts/report_assignment.py`. Se verificaron todas las acciones en un motor nuevo antes de generar.

**Casos:** 40 ubicaciones reservadas nuevas, dos edificios conocidos, 360 episodios. Una red entrenada (semilla 7), seis inicializaciones sin entrenar y dos referencias.

**Modelo congelado:** `499c8c17f383cdc9f72b29fa4da7fe7d2a4a68e2fd5fa69ee23d7d470ab599ae`. Protocolo conservado antes de prueba en el commit `c2bf859`.

## Rescates reales

| Controlador | Éxitos | Personas entregadas | Pasos medios en éxitos | Daño medio en éxitos |
|---|---:|---:|---:|---:|
| Red entrenada (semilla 7) | 40/40 | 120/120 | 41.20 | 13.83 |
| Red sin entrenar · semilla 0 | 39/40 | 119/120 | 42.95 | 23.05 |
| Red sin entrenar · semilla 1 | 40/40 | 120/120 | 43.35 | 14.50 |
| Red sin entrenar · semilla 2 | 40/40 | 120/120 | 42.90 | 24.33 |
| Red sin entrenar · semilla 3 | 37/40 | 116/120 | 38.32 | 27.08 |
| Red sin entrenar · semilla 4 | 38/40 | 118/120 | 40.34 | 26.66 |
| Red sin entrenar · semilla 7 | 40/40 | 120/120 | 43.63 | 15.63 |
| Referencia térmica | 40/40 | 120/120 | 44.28 | 13.80 |
| Referencia de ruta corta | 33/40 | 109/120 | 37.27 | 44.18 |

El planificador A* y las restricciones factibles son comunes a las redes entrenada y sin entrenar. Los rescates completos por sí solos no prueban que el entrenamiento explique la capacidad básica de navegación. Las seis inicializaciones no son seis réplicas de entrenamiento.

## Comparaciones emparejadas

Solo se comparan pasos y daño en las mismas misiones exitosas para ambos controladores. Δ = red entrenada menos referencia; un valor negativo reduce el coste.

| Referencia | Éxitos comunes | Δ pasos | Δ daño |
|---|---:|---:|---:|
| Red sin entrenar · semilla 7 | 40 | -2.43 | -1.80 |
| Referencia térmica | 40 | -3.08 | 0.03 |
| Referencia de ruta corta | 33 | 1.21 | -29.06 |

## Qué aprendió la red

Se plantearon las mismas 2400 preguntas sintéticas de asignación y riesgo a todas las redes, usando únicamente las posiciones reservadas después de congelar. La coincidencia se mide frente al estimador de coste programado que proporciona las etiquetas. No es una prueba de rescate óptimo ni una recompensa obtenida por DQN.

| Red | Preguntas | Elección con coste experto mínimo | Arrepentimiento medio (coste / 100) |
|---|---:|---:|---:|
| Red entrenada (semilla 7) | 2400 | 99.62% | 0.000137 |
| Red sin entrenar · semilla 0 | 2400 | 28.71% | 0.290406 |
| Red sin entrenar · semilla 1 | 2400 | 38.38% | 0.098417 |
| Red sin entrenar · semilla 2 | 2400 | 29.62% | 0.312585 |
| Red sin entrenar · semilla 3 | 2400 | 33.21% | 0.511171 |
| Red sin entrenar · semilla 4 | 2400 | 37.62% | 0.413106 |
| Red sin entrenar · semilla 7 | 2400 | 37.38% | 0.078135 |

## Límites

- Aprendizaje supervisado de un estimador experto: no es aprendizaje por refuerzo desde cero ni navegación aprendida de extremo a extremo.
- Una semilla de entrenamiento, dos geometrías conocidas y selección repetida sobre validación. Las 40 posiciones nuevas no se usaron para ajustar la red después de prueba.
- Los casos se admitieron por certificación de referencias: sus tasas están favorecidas por construcción. No se promete rescatar cualquier colocación del profesor.
- Las preguntas sintéticas y los episodios comparten mapas y posiciones. Se informan conteos y pares; no intervalos que supongan independencia.
- El aprendizaje de sesión usa memoria, etiquetas del mismo experto y controles de entrenamiento; sus actualizaciones pueden rechazarse. Las cifras anteriores usan el modelo base congelado.

## Fuentes verificadas

- CSV (SHA-256 normalizado LF): `e837fb1556391a53d635d6d377c3eab20cf938fe9fb118632f0ccf697d655871`.
- Trazas (SHA-256 normalizado LF): `75c0bfefe4d9caf311728fce1b7bbf4a4e4d69fc6f0f013f90554f9fab6f339c`.
- Protocolo (JSON canónico): `6d7d20700da29cfdb50ebc68555a4b8984885a668b2e38f36a22ea5a6068103d`.

Regenerar: `.venv\Scripts\python.exe scripts/report_assignment.py`. No entrena ni vuelve a ejecutar las políticas; reproduce acciones guardadas.
