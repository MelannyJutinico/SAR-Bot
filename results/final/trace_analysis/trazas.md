# Trazas analizadas (SARB-023)

Archivo generado por `scripts/trace_story.py` desde `configs/analysis/final_casos.json`. No se edita a mano. Cada episodio se reproduce en un motor nuevo y sus totales se comparan con la fila del CSV antes de describirlo.

Definiciones: un **bloqueo** es un movimiento pedido que no cambió la posición de un robot operativo (pared, borde o el otro robot); un **vaivén** es volver a la celda ocupada dos pasos antes; las rachas se listan desde 5 pasos seguidos. Las celdas siguen la notación de la interfaz (A1 arriba a la izquierda).

## Mismo caso reservado: entregas parciales frente a rescate completo

| Dato | Valor |
|---|---|
| Escenario | `scenarios/partitions/v2_12x12/test/detour_test_01_easy.json` |
| Partición | test (v2_12x12_v1) |
| Estrategia | DQN (final, semilla de entrenamiento 0) |
| Resultado | límite de pasos, 2/3 personas, 300 de 300 pasos, daño 0 |
| Episodio | `4e3c39ade1cfcb51` en `results/final/test.csv` |

| Robot | Entregas | Esperas | Bloqueos | Vaivenes | Pasos con daño | Daño | Integridad final | Celdas distintas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 0 | 194 | 0 | 0 | 100 | 16 |
| 2 | 2 | 42 | 0 | 112 | 0 | 0 | 100 | 16 |

| Persona | Robot | Recogida (paso) | Entrega (paso) | Duración |
|---|---:|---:|---:|---:|
| 1 | 2 | 2 | 4 | 2 |
| 3 | 2 | 109 | 115 | 6 |

Cronología observable:

- Robot 2 recoge a la persona 1 en B9.
- Robot 2 entrega a la persona 1 en la base.
- Robot 2 recoge a la persona 3 en D11.
- Robot 2 entrega a la persona 3 en la base.
- Termina en el paso 300: límite de pasos; sin recoger: persona 2.

## Mismo caso reservado: entregas parciales frente a rescate completo

| Dato | Valor |
|---|---|
| Escenario | `scenarios/partitions/v2_12x12/test/detour_test_01_easy.json` |
| Partición | test (v2_12x12_v1) |
| Estrategia | Ruta corta |
| Resultado | rescate completo, 3/3 personas, 18 de 300 pasos, daño 0 |
| Episodio | `b48d8390c833a7d4` en `results/final/test.csv` |

| Robot | Entregas | Esperas | Bloqueos | Vaivenes | Pasos con daño | Daño | Integridad final | Celdas distintas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 0 | 0 | 3 | 0 | 0 | 100 | 13 |
| 2 | 1 | 0 | 0 | 4 | 0 | 0 | 100 | 8 |

| Persona | Robot | Recogida (paso) | Entrega (paso) | Duración |
|---|---:|---:|---:|---:|
| 1 | 1 | 4 | 6 | 2 |
| 2 | 2 | 4 | 12 | 8 |
| 3 | 1 | 12 | 18 | 6 |

Cronología observable:

- Robot 1 recoge a la persona 1 en B9.
- Robot 2 recoge a la persona 2 en A4.
- Robot 1 entrega a la persona 1 en la base.
- Robot 1 recoge a la persona 3 en D11.
- Robot 2 entrega a la persona 2 en la base.
- Robot 1 entrega a la persona 3 en la base.
- Termina en el paso 18: rescate completo.

## Mismo caso reservado: entregas parciales frente a rescate completo

| Dato | Valor |
|---|---|
| Escenario | `scenarios/partitions/v2_12x12/test/detour_test_01_easy.json` |
| Partición | test (v2_12x12_v1) |
| Estrategia | Ruta térmica |
| Resultado | rescate completo, 3/3 personas, 18 de 300 pasos, daño 0 |
| Episodio | `172739fba5b9a7fb` en `results/final/test.csv` |

| Robot | Entregas | Esperas | Bloqueos | Vaivenes | Pasos con daño | Daño | Integridad final | Celdas distintas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 0 | 0 | 3 | 0 | 0 | 100 | 13 |
| 2 | 1 | 0 | 0 | 4 | 0 | 0 | 100 | 8 |

| Persona | Robot | Recogida (paso) | Entrega (paso) | Duración |
|---|---:|---:|---:|---:|
| 1 | 1 | 4 | 6 | 2 |
| 2 | 2 | 4 | 12 | 8 |
| 3 | 1 | 12 | 18 | 6 |

Cronología observable:

- Robot 1 recoge a la persona 1 en B9.
- Robot 2 recoge a la persona 2 en A4.
- Robot 1 entrega a la persona 1 en la base.
- Robot 1 recoge a la persona 3 en D11.
- Robot 2 entrega a la persona 2 en la base.
- Robot 1 entrega a la persona 3 en la base.
- Termina en el paso 18: rescate completo.
