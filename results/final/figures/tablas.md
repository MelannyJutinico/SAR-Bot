# Tablas generadas desde los resultados conservados

Archivo generado por `scripts/report_figures.py` (SARB-022). No se edita a mano: para cambiarlo se regenera, y `--check` detecta cualquier diferencia con lo que producen las fuentes.

**Datos:** Prueba final · manifiesto v2_12x12_v1 · perfil 12 × 12 con 3 personas · 40 casos distintos · 320 episodios.

## Fuentes

| Archivo | SHA-256 (LF) |
|---|---|
| `results/final/test.csv` | `938e462623c223bd471a6a4d6a0010a1b886a66babe23044110466245cedb66d` |
| `results/final/test.traces.jsonl` | `7ae3553a6df3775b3fbcbb9a9e4a2848f51218fcf473255e66bb0b7e9baad329` |
| `artifacts/final/evaluations.jsonl` | `87fdf326cc2db5bf0a0d86fc8071d59f56766095120696442747db3f69543fae` |
| `artifacts/final/metadata.json` | `71acb37f9725f9087156cbcf96b20d9df92210ad7bc73d37af63fc9e82c3d095` |
| `artifacts/final/model.zip` | `0c68363d8471d52bba84ce4e1235fee70aaf4fcd592e3c254c43b365318d1bc5` |

Trazas reproducidas en un motor nuevo antes de generar: sí.
Recompensa del retorno: `554f0aea65f79fbe07a0227b62aae26ff3bcbe67ba836ddb97a5f16ac10ac6da`.

Para regenerar:

```powershell
uv run python scripts/report_figures.py --results results/final/test.csv --training artifacts/final --output-dir results/final/figures
```

## 1. Resultado por estrategia

| Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DQN final · semilla 0 | 40 | 40 | 0/40 | 16/120 | 1 | 39 | — | — |
| Ruta corta | 40 | 40 | 33/40 | 112/120 | 7 | 0 | 32,6 | 38,1 |
| Ruta térmica | 40 | 40 | 40/40 | 120/120 | 0 | 0 | 39,1 | 12,2 |
| Aleatoria · 5 semillas | 200 | 40 | 2/200 | 133/600 | 119 | 79 | 164,0 | 23,0 |

## 2. Por edificio

| Edificio | Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Centro de coordinación (hub) | DQN final · semilla 0 | 20 | 20 | 0/20 | 7/60 | 0 | 20 | — | — |
| Centro de coordinación (hub) | Ruta corta | 20 | 20 | 20/20 | 60/60 | 0 | 0 | 35,4 | 38,1 |
| Centro de coordinación (hub) | Ruta térmica | 20 | 20 | 20/20 | 60/60 | 0 | 0 | 39,4 | 22,1 |
| Centro de coordinación (hub) | Aleatoria · 5 semillas | 100 | 20 | 2/100 | 76/300 | 59 | 39 | 164,0 | 23,0 |
| Desvío térmico (detour) | DQN final · semilla 0 | 20 | 20 | 0/20 | 9/60 | 1 | 19 | — | — |
| Desvío térmico (detour) | Ruta corta | 20 | 20 | 13/20 | 52/60 | 7 | 0 | 28,3 | 37,9 |
| Desvío térmico (detour) | Ruta térmica | 20 | 20 | 20/20 | 60/60 | 0 | 0 | 38,9 | 2,3 |
| Desvío térmico (detour) | Aleatoria · 5 semillas | 100 | 20 | 0/100 | 57/300 | 60 | 40 | — | — |

## 3. Por familia de dificultad

Las familias describen distancia y exposición inicial al generar los casos; no predicen el desempeño de DQN.

| Familia | Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fácil | DQN final · semilla 0 | 12 | 12 | 0/12 | 12/36 | 0 | 12 | — | — |
| Fácil | Ruta corta | 12 | 12 | 12/12 | 36/36 | 0 | 0 | 13,2 | 0,0 |
| Fácil | Ruta térmica | 12 | 12 | 12/12 | 36/36 | 0 | 0 | 13,2 | 0,0 |
| Fácil | Aleatoria · 5 semillas | 60 | 12 | 2/60 | 84/180 | 35 | 23 | 164,0 | 23,0 |
| Intermedio | DQN final · semilla 0 | 14 | 14 | 0/14 | 4/42 | 0 | 14 | — | — |
| Intermedio | Ruta corta | 14 | 14 | 13/14 | 41/42 | 1 | 0 | 37,2 | 41,8 |
| Intermedio | Ruta térmica | 14 | 14 | 14/14 | 42/42 | 0 | 0 | 39,3 | 10,8 |
| Intermedio | Aleatoria · 5 semillas | 70 | 14 | 0/70 | 45/210 | 42 | 28 | — | — |
| Exigente | DQN final · semilla 0 | 14 | 14 | 0/14 | 0/42 | 1 | 13 | — | — |
| Exigente | Ruta corta | 14 | 14 | 8/14 | 35/42 | 6 | 0 | 54,2 | 89,0 |
| Exigente | Ruta térmica | 14 | 14 | 14/14 | 42/42 | 0 | 0 | 61,1 | 24,0 |
| Exigente | Aleatoria · 5 semillas | 70 | 14 | 0/70 | 4/210 | 42 | 28 | — | — |

## 4. Comparaciones emparejadas

Solo series con un episodio por caso. Pasos y daño se comparan sobre los casos en que ambas tuvieron éxito; las diferencias son B − A. Las columnas «B por debajo» cuentan los casos emparejados en que B usó menos pasos o recibió menos daño (menos / igual / más).

| A | B | Casos compartidos | Éxito en ambas | Solo A | Solo B | Ninguna | Pasos A | Pasos B | Δ pasos | B por debajo en pasos | Daño A | Daño B | Δ daño | B por debajo en daño |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DQN final · semilla 0 | Ruta corta | 40 | 0 | 0 | 33 | 7 | — | — | — | 0/0/0 | — | — | — | 0/0/0 |
| DQN final · semilla 0 | Ruta térmica | 40 | 0 | 0 | 40 | 0 | — | — | — | 0/0/0 | — | — | — | 0/0/0 |
| Ruta corta | Ruta térmica | 40 | 33 | 0 | 7 | 0 | 32,6 | 35,5 | +2,9 | 1/22/10 | 38,1 | 14,1 | -24,0 | 18/15/0 |

## 5. Variación entre semillas

### DQN por semilla de entrenamiento

| Modelo | Semilla | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| final | 0 | 40 | 40 | 0/40 | 16/120 | 1 | 39 | — | — |

### Aleatoria por semilla de acciones

| Semilla | Éxitos | Personas entregadas | Destruidos | Límite de pasos |
|---|---:|---:|---:|---:|
| 0 | 0/40 | 16/120 | 40 | 0 |
| 1 | 0/40 | 26/120 | 40 | 0 |
| 2 | 1/40 | 44/120 | 0 | 39 |
| 3 | 1/40 | 13/120 | 39 | 0 |
| 4 | 0/40 | 34/120 | 0 | 40 |

## 6. Límites de lectura

- Hay 40 casos distintos. En una estrategia determinista cada caso vale 2,5 puntos de su tasa de éxito: diferencias de uno o dos casos no son una tendencia.
- Estrategias, semillas DQN y semillas aleatorias se evalúan sobre los mismos casos. Los episodios están emparejados y no son muestras independientes; por eso se informan conteos, casos emparejados y variación entre semillas, sin intervalos de confianza que supongan independencia.
- Pasos y daño se promedian solo entre misiones exitosas. Un fracaso temprano con poco daño no es un mejor resultado.
- Los casos de `v2_12x12_v1` entraron porque una referencia los resolvió al certificarlos: la tasa de éxito de las referencias está favorecida por construcción (`docs/PARTICIONES_V2.md`).
