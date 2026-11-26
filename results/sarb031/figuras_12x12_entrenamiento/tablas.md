# Tablas generadas desde los resultados conservados

Archivo generado por `scripts/report_figures.py` (SARB-022). No se edita a mano: para cambiarlo se regenera, y `--check` detecta cualquier diferencia con lo que producen las fuentes.

**Datos:** Entrenamiento · manifiesto v2_12x12_v1 · perfil 12 × 12 con 3 personas · 60 casos distintos · 420 episodios.

## Fuentes

| Archivo | SHA-256 (LF) |
|---|---|
| `results/sarb031/v2_12x12_training_referencias.csv` | `f212324ce77c9189119d0243199a002d6c663504a9cb00feccdf0d62cd41da6e` |
| `results/sarb031/v2_12x12_training_referencias.traces.jsonl` | `22d4ddc1acfa7933e3296cac2f76cf96c4ed35c6f9373b0565e284e40d7968e7` |

Trazas reproducidas en un motor nuevo antes de generar: sí.
Recompensa del retorno: `5266a757e55e81226866a44a5d11abe2ecf3d075f81ba259a31d7d6c370e53ef`.

Para regenerar:

```powershell
uv run python scripts/report_figures.py --results results/sarb031/v2_12x12_training_referencias.csv --output-dir results/sarb031/figuras_12x12_entrenamiento
```

## 1. Resultado por estrategia

| Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Ruta corta | 60 | 60 | 55/60 | 175/180 | 5 | 0 | 35,2 | 43,7 |
| Ruta térmica | 60 | 60 | 60/60 | 180/180 | 0 | 0 | 38,5 | 12,7 |
| Aleatoria · 5 semillas | 300 | 60 | 2/300 | 182/900 | 179 | 119 | 174,0 | 44,5 |

## 2. Por edificio

| Edificio | Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Centro de coordinación (hub) | Ruta corta | 30 | 30 | 30/30 | 90/90 | 0 | 0 | 39,0 | 37,1 |
| Centro de coordinación (hub) | Ruta térmica | 30 | 30 | 30/30 | 90/90 | 0 | 0 | 40,2 | 23,2 |
| Centro de coordinación (hub) | Aleatoria · 5 semillas | 150 | 30 | 0/150 | 100/450 | 90 | 60 | — | — |
| Desvío térmico (detour) | Ruta corta | 30 | 30 | 25/30 | 85/90 | 5 | 0 | 30,6 | 51,6 |
| Desvío térmico (detour) | Ruta térmica | 30 | 30 | 30/30 | 90/90 | 0 | 0 | 36,8 | 2,2 |
| Desvío térmico (detour) | Aleatoria · 5 semillas | 150 | 30 | 2/150 | 82/450 | 89 | 59 | 174,0 | 44,5 |

## 3. Por familia de dificultad

Las familias describen distancia y exposición inicial al generar los casos; no predicen el desempeño de DQN.

| Familia | Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fácil | Ruta corta | 20 | 20 | 20/20 | 60/60 | 0 | 0 | 15,7 | 0,3 |
| Fácil | Ruta térmica | 20 | 20 | 20/20 | 60/60 | 0 | 0 | 15,7 | 0,0 |
| Fácil | Aleatoria · 5 semillas | 100 | 20 | 2/100 | 119/300 | 59 | 39 | 174,0 | 44,5 |
| Intermedio | Ruta corta | 20 | 20 | 18/20 | 58/60 | 2 | 0 | 36,6 | 43,5 |
| Intermedio | Ruta térmica | 20 | 20 | 20/20 | 60/60 | 0 | 0 | 42,0 | 12,0 |
| Intermedio | Aleatoria · 5 semillas | 100 | 20 | 0/100 | 56/300 | 60 | 40 | — | — |
| Exigente | Ruta corta | 20 | 20 | 17/20 | 57/60 | 3 | 0 | 56,6 | 94,9 |
| Exigente | Ruta térmica | 20 | 20 | 20/20 | 60/60 | 0 | 0 | 57,9 | 26,1 |
| Exigente | Aleatoria · 5 semillas | 100 | 20 | 0/100 | 7/300 | 60 | 40 | — | — |

## 4. Comparaciones emparejadas

Solo series con un episodio por caso. Pasos y daño se comparan sobre los casos en que ambas tuvieron éxito; las diferencias son B − A. Las columnas «B por debajo» cuentan los casos emparejados en que B usó menos pasos o recibió menos daño (menos / igual / más).

| A | B | Casos compartidos | Éxito en ambas | Solo A | Solo B | Ninguna | Pasos A | Pasos B | Δ pasos | B por debajo en pasos | Daño A | Daño B | Δ daño | B por debajo en daño |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Ruta corta | Ruta térmica | 60 | 55 | 0 | 5 | 0 | 35,2 | 36,9 | +1,7 | 5/36/14 | 43,7 | 13,5 | -30,2 | 34/21/0 |

## 5. Variación entre semillas

### Aleatoria por semilla de acciones

| Semilla | Éxitos | Personas entregadas | Destruidos | Límite de pasos |
|---|---:|---:|---:|---:|
| 0 | 0/60 | 16/180 | 60 | 0 |
| 1 | 1/60 | 41/180 | 59 | 0 |
| 2 | 1/60 | 65/180 | 0 | 59 |
| 3 | 0/60 | 16/180 | 60 | 0 |
| 4 | 0/60 | 44/180 | 0 | 60 |

## 6. Límites de lectura

- Hay 60 casos distintos. En una estrategia determinista cada caso vale 1,7 puntos de su tasa de éxito: diferencias de uno o dos casos no son una tendencia.
- Estrategias, semillas DQN y semillas aleatorias se evalúan sobre los mismos casos. Los episodios están emparejados y no son muestras independientes; por eso se informan conteos, casos emparejados y variación entre semillas, sin intervalos de confianza que supongan independencia.
- Pasos y daño se promedian solo entre misiones exitosas. Un fracaso temprano con poco daño no es un mejor resultado.
- Los casos de `v2_12x12_v1` entraron porque una referencia los resolvió al certificarlos: la tasa de éxito de las referencias está favorecida por construcción (`docs/PARTICIONES_V2.md`).
- Partición «Entrenamiento»: no es la evaluación final reservada (SARB-021).
