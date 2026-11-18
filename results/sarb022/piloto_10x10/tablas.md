# Tablas generadas desde los resultados conservados

Archivo generado por `scripts/report_figures.py` (SARB-022). No se edita a mano: para cambiarlo se regenera, y `--check` detecta cualquier diferencia con lo que producen las fuentes.

**Datos:** Desarrollo · perfil 10 × 10 con 3 personas · 2 casos distintos · 16 episodios.

## Fuentes

| Archivo | SHA-256 (LF) |
|---|---|
| `results/sarb020/v2_10x10_piloto_desarrollo.csv` | `acd79efd73256bbdab5dcc1f8d72b3212266b812ae1a51499872e0dd18a993e3` |
| `results/sarb020/v2_10x10_piloto_desarrollo.traces.jsonl` | `0b9bae3612aa4bac7dfe7b0a6bbf2b0aee648a11ffb57c5a226193bcc137aa1c` |
| `artifacts/v2_pilot/evaluations.jsonl` | `e236194a45c94c7820bd23eba402703592b8b771f2cab898491b82f5de094345` |
| `artifacts/v2_pilot/metadata.json` | `4268599954620639d84e433fb4ba6592c9f08385704df627e9797b658ffa53d1` |
| `artifacts/v2_pilot/model.zip` | `77af198aee3cdd7b7134ca994a7bb6923b579f91ffe36b24124539f233999f2e` |

Trazas reproducidas en un motor nuevo antes de generar: sí.
Recompensa del retorno: `5266a757e55e81226866a44a5d11abe2ecf3d075f81ba259a31d7d6c370e53ef`.

Para regenerar:

```powershell
uv run python scripts/report_figures.py --results results/sarb020/v2_10x10_piloto_desarrollo.csv --training artifacts/v2_pilot --output-dir results/sarb022/piloto_10x10
```

## 1. Resultado por estrategia

| Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DQN v2_pilot · semilla 0 | 2 | 2 | 1/2 | 3/6 | 0 | 1 | 6,0 | 0,0 |
| Ruta corta | 2 | 2 | 2/2 | 6/6 | 0 | 0 | 32,0 | 53,5 |
| Ruta térmica | 2 | 2 | 2/2 | 6/6 | 0 | 0 | 34,0 | 32,0 |
| Aleatoria · 5 semillas | 10 | 2 | 2/10 | 10/30 | 5 | 3 | 57,0 | 0,0 |

## 2. Por escenario

| Escenario | Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| warmup_10x10 | DQN v2_pilot · semilla 0 | 1 | 1 | 1/1 | 3/3 | 0 | 0 | 6,0 | 0,0 |
| warmup_10x10 | Ruta corta | 1 | 1 | 1/1 | 3/3 | 0 | 0 | 6,0 | 0,0 |
| warmup_10x10 | Ruta térmica | 1 | 1 | 1/1 | 3/3 | 0 | 0 | 6,0 | 0,0 |
| warmup_10x10 | Aleatoria · 5 semillas | 5 | 1 | 2/5 | 10/15 | 0 | 3 | 57,0 | 0,0 |
| building_10x10 | DQN v2_pilot · semilla 0 | 1 | 1 | 0/1 | 0/3 | 0 | 1 | — | — |
| building_10x10 | Ruta corta | 1 | 1 | 1/1 | 3/3 | 0 | 0 | 58,0 | 107,0 |
| building_10x10 | Ruta térmica | 1 | 1 | 1/1 | 3/3 | 0 | 0 | 62,0 | 64,0 |
| building_10x10 | Aleatoria · 5 semillas | 5 | 1 | 0/5 | 0/15 | 5 | 0 | — | — |

## 3. Por familia de dificultad

Los escenarios de esta evaluación no tienen familia registrada.

## 4. Comparaciones emparejadas

Solo series con un episodio por caso. Pasos y daño se comparan sobre los casos en que ambas tuvieron éxito; las diferencias son B − A. Las columnas «B por debajo» cuentan los casos emparejados en que B usó menos pasos o recibió menos daño (menos / igual / más).

| A | B | Casos compartidos | Éxito en ambas | Solo A | Solo B | Ninguna | Pasos A | Pasos B | Δ pasos | B por debajo en pasos | Daño A | Daño B | Δ daño | B por debajo en daño |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DQN v2_pilot · semilla 0 | Ruta corta | 2 | 1 | 0 | 1 | 0 | 6,0 | 6,0 | +0,0 | 0/1/0 | 0,0 | 0,0 | +0,0 | 0/1/0 |
| DQN v2_pilot · semilla 0 | Ruta térmica | 2 | 1 | 0 | 1 | 0 | 6,0 | 6,0 | +0,0 | 0/1/0 | 0,0 | 0,0 | +0,0 | 0/1/0 |
| Ruta corta | Ruta térmica | 2 | 2 | 0 | 0 | 0 | 32,0 | 34,0 | +2,0 | 0/1/1 | 53,5 | 32,0 | -21,5 | 1/1/0 |

## 5. Variación entre semillas

### DQN por semilla de entrenamiento

| Modelo | Semilla | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v2_pilot | 0 | 2 | 2 | 1/2 | 3/6 | 0 | 1 | 6,0 | 0,0 |

### Aleatoria por semilla de acciones

| Semilla | Éxitos | Personas entregadas | Destruidos | Límite de pasos |
|---|---:|---:|---:|---:|
| 0 | 0/2 | 2/6 | 1 | 1 |
| 1 | 1/2 | 3/6 | 1 | 0 |
| 2 | 0/2 | 0/6 | 1 | 1 |
| 3 | 1/2 | 3/6 | 1 | 0 |
| 4 | 0/2 | 2/6 | 1 | 1 |

## 6. Límites de lectura

- Hay 2 casos distintos. En una estrategia determinista cada caso vale 50 puntos de su tasa de éxito: diferencias de uno o dos casos no son una tendencia.
- Estrategias, semillas DQN y semillas aleatorias se evalúan sobre los mismos casos. Los episodios están emparejados y no son muestras independientes; por eso se informan conteos, casos emparejados y variación entre semillas, sin intervalos de confianza que supongan independencia.
- Pasos y daño se promedian solo entre misiones exitosas. Un fracaso temprano con poco daño no es un mejor resultado.
- Partición «Desarrollo»: no es la evaluación final reservada (SARB-021).
