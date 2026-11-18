# Trazas analizadas (SARB-023)

Archivo generado por `scripts/trace_story.py` desde `configs/analysis/sarb023_casos.json`. No se edita a mano. Cada episodio se reproduce en un motor nuevo y sus totales se comparan con la fila del CSV antes de describirlo.

Definiciones: un **bloqueo** es un movimiento pedido que no cambió la posición de un robot operativo (pared, borde o el otro robot); un **vaivén** es volver a la celda ocupada dos pasos antes; las rachas se listan desde 5 pasos seguidos. Las celdas siguen la notación de la interfaz (A1 arriba a la izquierda).

## Rescate eficiente de una política aprendida

Escenario de desarrollo que el modelo vio al entrenar: muestra una ejecución eficiente, no generalización.

| Dato | Valor |
|---|---|
| Escenario | `scenarios/pasillo_compartido.json` |
| Partición | development |
| Estrategia | DQN (sensors_dqn, semilla de entrenamiento 0) |
| Resultado | rescate completo, 2/2 personas, 22 de 100 pasos, daño 0 |
| Episodio | `5a5446d50cbd1498` en `results/sarb031/v2_6x6_desarrollo.csv` |

| Robot | Entregas | Esperas | Bloqueos | Vaivenes | Pasos con daño | Daño | Integridad final | Celdas distintas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 4 | 6 | 3 | 0 | 0 | 100 | 6 |
| 2 | 1 | 0 | 2 | 0 | 0 | 0 | 100 | 12 |

| Persona | Robot | Recogida (paso) | Entrega (paso) | Duración |
|---|---:|---:|---:|---:|
| 1 | 1 | 5 | 12 | 7 |
| 2 | 2 | 11 | 22 | 11 |

Cronología observable:

- Robot 1 recoge a la persona 1 en F1.
- Robot 2 recoge a la persona 2 en F6.
- Robot 1 entrega a la persona 1 en la base.
- Robot 1 no logra moverse 5 veces seguidas entre los pasos 13 y 17 (en A1).
- Robot 2 entrega a la persona 2 en la base.
- Termina en el paso 22: rescate completo.

## Caso térmico: la ruta corta cruza el calor

Caso de la partición de entrenamiento de 12 × 12 evaluado solo con referencias.

| Dato | Valor |
|---|---|
| Escenario | `scenarios/partitions/v2_12x12/training/detour_training_14_intermediate.json` |
| Partición | training (v2_12x12_v1) |
| Estrategia | Ruta corta |
| Resultado | robot destruido, 2/3 personas, 45 de 300 pasos, daño 190 |
| Episodio | `0e624a17a55916d7` en `results/sarb031/v2_12x12_training_referencias.csv` |

| Robot | Entregas | Esperas | Bloqueos | Vaivenes | Pasos con daño | Daño | Integridad final | Celdas distintas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 0 | 0 | 2 | 21 | 100 | 0 | 27 |
| 2 | 1 | 0 | 0 | 3 | 17 | 90 | 10 | 23 |

| Persona | Robot | Recogida (paso) | Entrega (paso) | Duración |
|---|---:|---:|---:|---:|
| 1 | 1 | 10 | 28 | 18 |
| 2 | 2 | 17 | 28 | 11 |

Cronología observable:

- Robot 2 recibe 44 de daño entre los pasos 3 y 10 (8 pasos, hasta 90 °C, celdas E7, F7, G7, H7, I7, J7, J6, K6).
- Robot 1 recibe 9 de daño entre los pasos 5 y 7 (3 pasos, hasta 72 °C, celdas E7, F7, F6).
- Robot 1 recibe 2 de daño en el paso 9 (54 °C, celda G5).
- Robot 1 recoge a la persona 1 en H5.
- Robot 1 recibe 24 de daño entre los pasos 11 y 15 (5 pasos, hasta 90 °C, celdas H6, H7, G7, F7, E7).
- Robot 2 recibe 2 de daño en el paso 16 (50 °C, celda K6).
- Robot 2 recoge a la persona 2 en L6.
- Robot 2 recibe 44 de daño entre los pasos 18 y 25 (8 pasos, hasta 90 °C, celdas L7, K7, J7, I7, H7, G7, F7, E7).
- Robot 1 entrega a la persona 1 en la base.
- Robot 2 entrega a la persona 2 en la base.
- Robot 1 recibe 44 de daño entre los pasos 31 y 38 (8 pasos, hasta 90 °C, celdas E7, F7, G7, H7, I7, J7, J6, J5).
- Robot 1 recoge a la persona 3 en L5.
- Robot 1 recibe 21 de daño entre los pasos 42 y 45 (4 pasos, hasta 86 °C, celdas L7, K7, J7, I7).
- Robot 1 queda destruido en I7 a 68 °C, cargando a la persona 3.
- Termina en el paso 45: robot destruido; robot 1 lleva a la persona 3.

## Caso térmico: la ruta térmica rodea el calor

| Dato | Valor |
|---|---|
| Escenario | `scenarios/partitions/v2_12x12/training/detour_training_14_intermediate.json` |
| Partición | training (v2_12x12_v1) |
| Estrategia | Ruta térmica |
| Resultado | rescate completo, 3/3 personas, 66 de 300 pasos, daño 0 |
| Episodio | `ba20814117e0f343` en `results/sarb031/v2_12x12_training_referencias.csv` |

| Robot | Entregas | Esperas | Bloqueos | Vaivenes | Pasos con daño | Daño | Integridad final | Celdas distintas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 0 | 0 | 6 | 0 | 0 | 100 | 34 |
| 2 | 1 | 2 | 0 | 11 | 0 | 0 | 100 | 23 |

| Persona | Robot | Recogida (paso) | Entrega (paso) | Duración |
|---|---:|---:|---:|---:|
| 1 | 1 | 16 | 32 | 16 |
| 3 | 2 | 16 | 32 | 16 |
| 2 | 1 | 49 | 66 | 17 |

Cronología observable:

- Robot 1 recoge a la persona 1 en H5.
- Robot 2 recoge a la persona 3 en L5.
- Robot 1 entrega a la persona 1 en la base.
- Robot 2 entrega a la persona 3 en la base.
- Robot 1 recoge a la persona 2 en L6.
- Robot 1 entrega a la persona 2 en la base.
- Termina en el paso 66: rescate completo.

## Fallo real: piloto DQN con posiciones nuevas

Caso fácil del conjunto de desarrollo v2_10x10_dev_v1; el piloto solo se entrenó con las posiciones fijas del edificio.

| Dato | Valor |
|---|---|
| Escenario | `scenarios/development/v2_10x10/building10_dev_16_easy.json` |
| Partición | development (v2_10x10_dev_v1) |
| Estrategia | DQN (v2_pilot, semilla de entrenamiento 0) |
| Resultado | límite de pasos, 2/3 personas, 240 de 240 pasos, daño 0 |
| Episodio | `9a92bcf9dc7dddeb` en `results/sarb031/v2_10x10_desarrollo.csv` |

| Robot | Entregas | Esperas | Bloqueos | Vaivenes | Pasos con daño | Daño | Integridad final | Celdas distintas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 0 | 238 | 1 | 0 | 0 | 100 | 2 |
| 2 | 1 | 0 | 238 | 1 | 0 | 0 | 100 | 2 |

| Persona | Robot | Recogida (paso) | Entrega (paso) | Duración |
|---|---:|---:|---:|---:|
| 1 | 2 | 1 | 2 | 1 |
| 3 | 1 | 1 | 2 | 1 |

Cronología observable:

- Robot 1 recoge a la persona 3 en A2.
- Robot 2 recoge a la persona 1 en B1.
- Robot 2 entrega a la persona 1 en la base.
- Robot 1 entrega a la persona 3 en la base.
- Robot 1 no logra moverse 238 veces seguidas entre los pasos 3 y 240 (en A1).
- Robot 2 no logra moverse 238 veces seguidas entre los pasos 3 y 240 (en A1).
- Termina en el paso 240: límite de pasos; sin recoger: persona 2.

## Mismo caso con la ruta térmica

| Dato | Valor |
|---|---|
| Escenario | `scenarios/development/v2_10x10/building10_dev_16_easy.json` |
| Partición | development (v2_10x10_dev_v1) |
| Estrategia | Ruta térmica |
| Resultado | rescate completo, 3/3 personas, 8 de 240 pasos, daño 0 |
| Episodio | `2d56f9a06b479665` en `results/sarb031/v2_10x10_desarrollo.csv` |

| Robot | Entregas | Esperas | Bloqueos | Vaivenes | Pasos con daño | Daño | Integridad final | Celdas distintas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 0 | 0 | 2 | 0 | 0 | 100 | 5 |
| 2 | 1 | 2 | 0 | 3 | 0 | 0 | 100 | 3 |

| Persona | Robot | Recogida (paso) | Entrega (paso) | Duración |
|---|---:|---:|---:|---:|
| 1 | 1 | 1 | 2 | 1 |
| 3 | 2 | 1 | 2 | 1 |
| 2 | 1 | 5 | 8 | 3 |

Cronología observable:

- Robot 1 recoge a la persona 1 en B1.
- Robot 2 recoge a la persona 3 en A2.
- Robot 1 entrega a la persona 1 en la base.
- Robot 2 entrega a la persona 3 en la base.
- Robot 1 recoge a la persona 2 en A4.
- Robot 1 entrega a la persona 2 en la base.
- Termina en el paso 8: rescate completo.
