# Tablas generadas desde los resultados conservados

Archivo generado por `scripts/report_figures.py` (SARB-022). No se edita a mano: para cambiarlo se regenera, y `--check` detecta cualquier diferencia con lo que producen las fuentes.

**Datos:** Validación · manifiesto v2_12x12_v1 · perfil 12 × 12 con 3 personas · 20 casos distintos · 40 episodios.

## Fuentes

| Archivo | SHA-256 (LF) |
|---|---|
| `results/online/comparison.csv` | `4213e7ad850fbc10c933b0f2ea00734ce14ce29534f4b17cdf4d53dbcfe0c7c9` |
| `results/online/comparison.traces.jsonl` | `af3bebf763f6154aa9ce157175259858b003945735317002176b4cb6ba07cb6b` |

Trazas reproducidas en un motor nuevo antes de generar: sí.
Recompensa del retorno: `554f0aea65f79fbe07a0227b62aae26ff3bcbe67ba836ddb97a5f16ac10ac6da`.

Para regenerar:

```powershell
uv run python scripts/report_figures.py --results results/online/comparison.csv --output-dir results/online/figures
```

## 1. Resultado por estrategia

| Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DQN final · semilla 0 | 20 | 20 | 3/20 | 18/60 | 0 | 17 | 211,7 | 0,0 |
| DQN session_after · semilla 0 | 20 | 20 | 0/20 | 3/60 | 0 | 20 | — | — |

## 2. Por edificio

| Edificio | Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Centro de coordinación (hub) | DQN final · semilla 0 | 10 | 10 | 1/10 | 7/30 | 0 | 9 | 126,0 | 0,0 |
| Centro de coordinación (hub) | DQN session_after · semilla 0 | 10 | 10 | 0/10 | 0/30 | 0 | 10 | — | — |
| Desvío térmico (detour) | DQN final · semilla 0 | 10 | 10 | 2/10 | 11/30 | 0 | 8 | 254,5 | 0,0 |
| Desvío térmico (detour) | DQN session_after · semilla 0 | 10 | 10 | 0/10 | 3/30 | 0 | 10 | — | — |

## 3. Por familia de dificultad

Las familias describen distancia y exposición inicial al generar los casos; no predicen el desempeño de DQN.

| Familia | Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fácil | DQN final · semilla 0 | 8 | 8 | 3/8 | 16/24 | 0 | 5 | 211,7 | 0,0 |
| Fácil | DQN session_after · semilla 0 | 8 | 8 | 0/8 | 3/24 | 0 | 8 | — | — |
| Intermedio | DQN final · semilla 0 | 6 | 6 | 0/6 | 2/18 | 0 | 6 | — | — |
| Intermedio | DQN session_after · semilla 0 | 6 | 6 | 0/6 | 0/18 | 0 | 6 | — | — |
| Exigente | DQN final · semilla 0 | 6 | 6 | 0/6 | 0/18 | 0 | 6 | — | — |
| Exigente | DQN session_after · semilla 0 | 6 | 6 | 0/6 | 0/18 | 0 | 6 | — | — |

## 4. Comparaciones emparejadas

Solo series con un episodio por caso. Pasos y daño se comparan sobre los casos en que ambas tuvieron éxito; las diferencias son B − A. Las columnas «B por debajo» cuentan los casos emparejados en que B usó menos pasos o recibió menos daño (menos / igual / más).

| A | B | Casos compartidos | Éxito en ambas | Solo A | Solo B | Ninguna | Pasos A | Pasos B | Δ pasos | B por debajo en pasos | Daño A | Daño B | Δ daño | B por debajo en daño |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DQN final · semilla 0 | DQN session_after · semilla 0 | 20 | 0 | 3 | 0 | 17 | — | — | — | 0/0/0 | — | — | — | 0/0/0 |

## 5. Variación entre semillas

### DQN por semilla de entrenamiento

| Modelo | Semilla | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| final | 0 | 20 | 20 | 3/20 | 18/60 | 0 | 17 | 211,7 | 0,0 |
| session_after | 0 | 20 | 20 | 0/20 | 3/60 | 0 | 20 | — | — |

Éxitos por semilla: 3/20, 0/20 (mínimo 0, máximo 3). Con 2 semillas se informan todas y su rango; no se calcula un intervalo de confianza.

Casos según cuántas semillas los resuelven: 2 de 2: 0, 1 de 2: 3, 0 de 2: 17.

## 6. Límites de lectura

- Hay 20 casos distintos. En una estrategia determinista cada caso vale 5 puntos de su tasa de éxito: diferencias de uno o dos casos no son una tendencia.
- Estrategias, semillas DQN y semillas aleatorias se evalúan sobre los mismos casos. Los episodios están emparejados y no son muestras independientes; por eso se informan conteos, casos emparejados y variación entre semillas, sin intervalos de confianza que supongan independencia.
- Pasos y daño se promedian solo entre misiones exitosas. Un fracaso temprano con poco daño no es un mejor resultado.
- Los casos de `v2_12x12_v1` entraron porque una referencia los resolvió al certificarlos: la tasa de éxito de las referencias está favorecida por construcción (`docs/PARTICIONES_V2.md`).
- Partición «Validación»: no es la evaluación final reservada (SARB-021).
