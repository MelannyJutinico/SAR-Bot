# Tablas generadas desde los resultados conservados

Archivo generado por `scripts/report_figures.py` (SARB-022). No se edita a mano: para cambiarlo se regenera, y `--check` detecta cualquier diferencia con lo que producen las fuentes.

**Datos:** Desarrollo · conjunto v2_10x10_dev_v1 · perfil 10 × 10 con 3 personas · 30 casos distintos · 240 episodios.

## Fuentes

| Archivo | SHA-256 (LF) |
|---|---|
| `results/sarb031/v2_10x10_desarrollo.csv` | `53da24ca5fa6db9321bf3055ee234a70144a7b813ec0104d8baec5a8451eed87` |
| `results/sarb031/v2_10x10_desarrollo.traces.jsonl` | `de361a678f0a3bf9dcdbfd8fe02e424f6261c95eefaab45c989809368b6467f6` |

Trazas reproducidas en un motor nuevo antes de generar: sí.
Recompensa del retorno: `5266a757e55e81226866a44a5d11abe2ecf3d075f81ba259a31d7d6c370e53ef`.

Para regenerar:

```powershell
uv run python scripts/report_figures.py --results results/sarb031/v2_10x10_desarrollo.csv --output-dir results/sarb031/figuras_10x10_desarrollo
```

## 1. Resultado por estrategia

| Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DQN v2_pilot · semilla 0 | 30 | 30 | 0/30 | 9/90 | 0 | 30 | — | — |
| Ruta corta | 30 | 30 | 26/30 | 84/90 | 4 | 0 | 31,8 | 55,1 |
| Ruta térmica | 30 | 30 | 30/30 | 90/90 | 0 | 0 | 38,5 | 33,9 |
| Aleatoria · 5 semillas | 150 | 30 | 3/150 | 91/450 | 147 | 0 | 46,0 | 0,0 |

## 2. Por edificio

| Edificio | Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| building10 | DQN v2_pilot · semilla 0 | 30 | 30 | 0/30 | 9/90 | 0 | 30 | — | — |
| building10 | Ruta corta | 30 | 30 | 26/30 | 84/90 | 4 | 0 | 31,8 | 55,1 |
| building10 | Ruta térmica | 30 | 30 | 30/30 | 90/90 | 0 | 0 | 38,5 | 33,9 |
| building10 | Aleatoria · 5 semillas | 150 | 30 | 3/150 | 91/450 | 147 | 0 | 46,0 | 0,0 |

## 3. Por familia de dificultad

Las familias describen distancia y exposición inicial al generar los casos; no predicen el desempeño de DQN.

| Familia | Estrategia | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fácil | DQN v2_pilot · semilla 0 | 10 | 10 | 0/10 | 9/30 | 0 | 10 | — | — |
| Fácil | Ruta corta | 10 | 10 | 10/10 | 30/30 | 0 | 0 | 12,4 | 1,8 |
| Fácil | Ruta térmica | 10 | 10 | 10/10 | 30/30 | 0 | 0 | 12,4 | 1,8 |
| Fácil | Aleatoria · 5 semillas | 50 | 10 | 3/50 | 61/150 | 47 | 0 | 46,0 | 0,0 |
| Intermedio | DQN v2_pilot · semilla 0 | 10 | 10 | 0/10 | 0/30 | 0 | 10 | — | — |
| Intermedio | Ruta corta | 10 | 10 | 10/10 | 30/30 | 0 | 0 | 35,4 | 67,8 |
| Intermedio | Ruta térmica | 10 | 10 | 10/10 | 30/30 | 0 | 0 | 40,4 | 34,3 |
| Intermedio | Aleatoria · 5 semillas | 50 | 10 | 0/50 | 30/150 | 50 | 0 | — | — |
| Exigente | DQN v2_pilot · semilla 0 | 10 | 10 | 0/10 | 0/30 | 0 | 10 | — | — |
| Exigente | Ruta corta | 10 | 10 | 6/10 | 24/30 | 4 | 0 | 58,3 | 122,7 |
| Exigente | Ruta térmica | 10 | 10 | 10/10 | 30/30 | 0 | 0 | 62,6 | 65,7 |
| Exigente | Aleatoria · 5 semillas | 50 | 10 | 0/50 | 0/150 | 50 | 0 | — | — |

## 4. Comparaciones emparejadas

Solo series con un episodio por caso. Pasos y daño se comparan sobre los casos en que ambas tuvieron éxito; las diferencias son B − A. Las columnas «B por debajo» cuentan los casos emparejados en que B usó menos pasos o recibió menos daño (menos / igual / más).

| A | B | Casos compartidos | Éxito en ambas | Solo A | Solo B | Ninguna | Pasos A | Pasos B | Δ pasos | B por debajo en pasos | Daño A | Daño B | Δ daño | B por debajo en daño |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DQN v2_pilot · semilla 0 | Ruta corta | 30 | 0 | 0 | 26 | 4 | — | — | — | 0/0/0 | — | — | — | 0/0/0 |
| DQN v2_pilot · semilla 0 | Ruta térmica | 30 | 0 | 0 | 30 | 0 | — | — | — | 0/0/0 | — | — | — | 0/0/0 |
| Ruta corta | Ruta térmica | 30 | 26 | 0 | 4 | 0 | 31,8 | 34,5 | +2,7 | 2/14/10 | 55,1 | 28,7 | -26,3 | 16/10/0 |

## 5. Variación entre semillas

### DQN por semilla de entrenamiento

| Modelo | Semilla | Episodios | Casos | Éxitos | Personas entregadas | Destruidos | Límite de pasos | Pasos medios (éxitos) | Daño medio (éxitos) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v2_pilot | 0 | 30 | 30 | 0/30 | 9/90 | 0 | 30 | — | — |

### Aleatoria por semilla de acciones

| Semilla | Éxitos | Personas entregadas | Destruidos | Límite de pasos |
|---|---:|---:|---:|---:|
| 0 | 0/30 | 17/90 | 30 | 0 |
| 1 | 0/30 | 26/90 | 30 | 0 |
| 2 | 0/30 | 0/90 | 30 | 0 |
| 3 | 0/30 | 19/90 | 30 | 0 |
| 4 | 3/30 | 29/90 | 27 | 0 |

## 6. Límites de lectura

- Hay 30 casos distintos. En una estrategia determinista cada caso vale 3,3 puntos de su tasa de éxito: diferencias de uno o dos casos no son una tendencia.
- Estrategias, semillas DQN y semillas aleatorias se evalúan sobre los mismos casos. Los episodios están emparejados y no son muestras independientes; por eso se informan conteos, casos emparejados y variación entre semillas, sin intervalos de confianza que supongan independencia.
- Pasos y daño se promedian solo entre misiones exitosas. Un fracaso temprano con poco daño no es un mejor resultado.
- Los casos de `v2_10x10_dev_v1` entraron porque una referencia los resolvió al certificarlos: la tasa de éxito de las referencias está favorecida por construcción (`docs/PARTICIONES_V2.md`).
- Partición «Desarrollo»: no es la evaluación final reservada (SARB-021).
