# Tablas generadas desde los resultados conservados

Archivo generado por `scripts/report_figures.py` (SARB-022). No se edita a mano: para cambiarlo se regenera, y `--check` detecta cualquier diferencia con lo que producen las fuentes.

**Datos:** Validación · manifiesto v2_12x12_v1 · perfil 12 × 12 con 3 personas · 20 casos distintos · 160 episodios.

## Fuentes

| Archivo | SHA-256 (LF) |
|---|---|
| `results/sarb017/selected_validation.csv` | `d3255b28f803e4c25cebc1bc8cd05609d724ad72f3d90db39255836f855e7aad` |
| `results/sarb017/selected_validation.traces.jsonl` | `ba54692649dc49507e0c60bc00118bb4a46edc65a0b9c6e36b3e9edadd0a6e21` |
| `artifacts/v2_12x12/evaluations.jsonl` | `aa2059a7658ddce53b95e586ada8474eedf104653db96cd262fdcb5a7947c9a6` |
| `artifacts/v2_12x12/metadata.json` | `c1fd67b76603ce880aa9ae0a3b41fe151321d269cbfdddaec63905892e036f9a` |
| `artifacts/v2_12x12/model.zip` | `1fc205d8369c7fd6c2ea38bf41d563d31dad0a4f16d0226bd20b9daa0df3302a` |

Trazas reproducidas en un motor nuevo antes de generar: sí.
Recompensa del retorno: `554f0aea65f79fbe07a0227b62aae26ff3bcbe67ba836ddb97a5f16ac10ac6da`.

Para regenerar:

```powershell
uv run python scripts/report_figures.py --results results/sarb017/selected_validation.csv --training artifacts/v2_12x12 --output-dir results/sarb017/selected_validation_figures
```

## 1. Resultado por estrategia

| Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DQN v2_12x12 · semilla 0 | 20 | 20 | 2/20 | 10/60 | 6 | 12 | 89,5 | 1,0 |
| Ruta corta | 20 | 20 | 17/20 | 57/60 | 3 | 0 | 34,8 | 38,0 |
| Ruta térmica | 20 | 20 | 20/20 | 60/60 | 0 | 0 | 41,0 | 10,1 |
| Aleatoria · 5 semillas | 100 | 20 | 0/100 | 55/300 | 60 | 40 | — | — |

## 2. Por edificio

| Edificio | Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Centro de coordinación (hub) | DQN v2_12x12 · semilla 0 | 10 | 10 | 1/10 | 5/30 | 3 | 6 | 39,0 | 2,0 |
| Centro de coordinación (hub) | Ruta corta | 10 | 10 | 10/10 | 30/30 | 0 | 0 | 40,2 | 30,5 |
| Centro de coordinación (hub) | Ruta térmica | 10 | 10 | 10/10 | 30/30 | 0 | 0 | 43,7 | 18,8 |
| Centro de coordinación (hub) | Aleatoria · 5 semillas | 50 | 10 | 0/50 | 33/150 | 30 | 20 | — | — |
| Desvío térmico (detour) | DQN v2_12x12 · semilla 0 | 10 | 10 | 1/10 | 5/30 | 3 | 6 | 140,0 | 0,0 |
| Desvío térmico (detour) | Ruta corta | 10 | 10 | 7/10 | 27/30 | 3 | 0 | 27,1 | 48,7 |
| Desvío térmico (detour) | Ruta térmica | 10 | 10 | 10/10 | 30/30 | 0 | 0 | 38,2 | 1,3 |
| Desvío térmico (detour) | Aleatoria · 5 semillas | 50 | 10 | 0/50 | 22/150 | 30 | 20 | — | — |

## 3. Por familia de dificultad

Las familias describen distancia y exposición inicial al generar los casos; no predicen el desempeño de DQN.

| Familia | Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fácil | DQN v2_12x12 · semilla 0 | 8 | 8 | 2/8 | 10/24 | 1 | 5 | 89,5 | 1,0 |
| Fácil | Ruta corta | 8 | 8 | 8/8 | 24/24 | 0 | 0 | 16,8 | 1,8 |
| Fácil | Ruta térmica | 8 | 8 | 8/8 | 24/24 | 0 | 0 | 16,8 | 1,5 |
| Fácil | Aleatoria · 5 semillas | 40 | 8 | 0/40 | 43/120 | 24 | 16 | — | — |
| Intermedio | DQN v2_12x12 · semilla 0 | 6 | 6 | 0/6 | 0/18 | 2 | 4 | — | — |
| Intermedio | Ruta corta | 6 | 6 | 5/6 | 17/18 | 1 | 0 | 45,0 | 49,2 |
| Intermedio | Ruta térmica | 6 | 6 | 6/6 | 18/18 | 0 | 0 | 51,2 | 10,8 |
| Intermedio | Aleatoria · 5 semillas | 30 | 6 | 0/30 | 10/90 | 18 | 12 | — | — |
| Exigente | DQN v2_12x12 · semilla 0 | 6 | 6 | 0/6 | 0/18 | 3 | 3 | — | — |
| Exigente | Ruta corta | 6 | 6 | 4/6 | 16/18 | 2 | 0 | 58,2 | 96,5 |
| Exigente | Ruta térmica | 6 | 6 | 6/6 | 18/18 | 0 | 0 | 63,0 | 20,7 |
| Exigente | Aleatoria · 5 semillas | 30 | 6 | 0/30 | 2/90 | 18 | 12 | — | — |

## 4. Comparaciones emparejadas

Solo series con un episodio por caso. Pasos y daño se comparan sobre los casos en que ambas tuvieron éxito; las diferencias son B − A. Las columnas «B por debajo» cuentan los casos emparejados en que B usó menos pasos o recibió menos daño (menos / igual / más).

| A | B | Casos compartidos | Éxito en ambas | Solo A | Solo B | Ninguna | Pasos A | Pasos B | Δ pasos | B por debajo en pasos | Daño A | Daño B | Δ daño | B por debajo en daño |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DQN v2_12x12 · semilla 0 | Ruta corta | 20 | 2 | 0 | 15 | 3 | 89,5 | 17,0 | -72,5 | 2/0/0 | 1,0 | 1,0 | +0,0 | 0/2/0 |
| DQN v2_12x12 · semilla 0 | Ruta térmica | 20 | 2 | 0 | 18 | 0 | 89,5 | 17,0 | -72,5 | 2/0/0 | 1,0 | 0,0 | -1,0 | 1/1/0 |
| Ruta corta | Ruta térmica | 20 | 17 | 0 | 3 | 0 | 34,8 | 38,1 | +3,2 | 1/10/6 | 38,0 | 11,7 | -26,3 | 9/8/0 |

## 5. Variación entre semillas

### DQN por semilla de entrenamiento

| Modelo | Semilla | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v2_12x12 | 0 | 20 | 20 | 2/20 | 10/60 | 6 | 12 | 89,5 | 1,0 |

### Aleatoria por semilla de acciones

| Semilla | Éxitos | Personas entregadas | Destruidos | Límite de pasos |
|---|---:|---:|---:|---:|
| 0 | 0/20 | 5/60 | 20 | 0 |
| 1 | 0/20 | 9/60 | 20 | 0 |
| 2 | 0/20 | 22/60 | 0 | 20 |
| 3 | 0/20 | 4/60 | 20 | 0 |
| 4 | 0/20 | 15/60 | 0 | 20 |

## 6. Límites de lectura

- Hay 20 casos distintos. En una estrategia determinista cada caso vale 5 puntos de su tasa de éxito: diferencias de uno o dos casos no son una tendencia.
- Estrategias, semillas DQN y semillas aleatorias se evalúan sobre los mismos casos. Los episodios están emparejados y no son muestras independientes; por eso se informan conteos, casos emparejados y variación entre semillas, sin intervalos de confianza que supongan independencia.
- Pasos y daño se promedian solo entre misiones exitosas. Un fracaso temprano con poco daño no es un mejor resultado.
- Los casos de `v2_12x12_v1` entraron porque una referencia los resolvió al certificarlos: la tasa de éxito de las referencias está favorecida por construcción (`docs/PARTICIONES_V2.md`).
- Partición «Validación»: no es la evaluación final reservada (SARB-021).
