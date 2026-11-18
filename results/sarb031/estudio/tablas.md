# Estudio de escala, reparto de rescates y dificultad

Archivo generado por `scripts/scale_study.py` (SARB-031). No se edita a mano: `check` lo regenera desde los CSV y detecta cualquier diferencia.

Trazas reproducidas antes de generar: sí.

```powershell
uv run python scripts/scale_study.py analyze --results results/sarb031/v2_6x6_desarrollo.csv results/sarb020/v2_10x10_piloto_desarrollo.csv results/sarb031/v2_10x10_desarrollo.csv results/sarb031/v2_12x12_training_referencias.csv results/sarb020/v2_12x12_validation_referencias.csv --output-dir results/sarb031/estudio
```

Rasgos de cada caso, calculados del escenario antes de la misión: **distancia** media de las personas a la base y **separación** media entre pares de personas, ambas divididas por `ancho + alto − 2`; **personas en zona de daño**, las que empiezan en una celda de 40 °C o más. Pasos y daño se promedian solo entre misiones exitosas; las proporciones llevan su denominador.

## 1. Conjuntos analizados

| Conjunto | Perfil | Casos | Episodios | Estrategias | CSV | SHA-256 (LF) |
|---|---|---:|---:|---|---|---|
| 6 × 6 · desarrollo · escenarios fijos | 6 × 6, 2 personas | 8 | 64 | DQN sensors_dqn · semilla 0, Ruta corta, Ruta térmica, Aleatoria | `results/sarb031/v2_6x6_desarrollo.csv` | `b193e5cb35345173…` |
| 10 × 10 · desarrollo · escenarios fijos | 10 × 10, 3 personas | 2 | 16 | DQN v2_pilot · semilla 0, Ruta corta, Ruta térmica, Aleatoria | `results/sarb020/v2_10x10_piloto_desarrollo.csv` | `acd79efd73256bbd…` |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | 10 × 10, 3 personas | 30 | 240 | DQN v2_pilot · semilla 0, Ruta corta, Ruta térmica, Aleatoria | `results/sarb031/v2_10x10_desarrollo.csv` | `53da24ca5fa6db93…` |
| 12 × 12 · entrenamiento · v2_12x12_v1 | 12 × 12, 3 personas | 60 | 420 | Ruta corta, Ruta térmica, Aleatoria | `results/sarb031/v2_12x12_training_referencias.csv` | `f212324ce77c9189…` |
| 12 × 12 · validación · v2_12x12_v1 | 12 × 12, 3 personas | 20 | 140 | Ruta corta, Ruta térmica, Aleatoria | `results/sarb020/v2_12x12_validation_referencias.csv` | `d648b305482dd822…` |

## 2. Escala: resultados por perfil

Cada fila es un conjunto evaluado por separado; los perfiles no se mezclan. Los estados expandidos y el cómputo solo aplican a las referencias que planifican. El cómputo se mide en la máquina que evaluó y no es tiempo simulado.

| Conjunto | Estrategia | Distancia media | Límite de pasos | Éxitos | Personas entregadas | Pasos medios (éxitos) | Daño medio (éxitos) | Estados expandidos (mediana) | Cómputo por episodio (mediana, ms) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 × 6 · desarrollo · escenarios fijos | DQN sensors_dqn · semilla 0 | 0,46 | 100 | 8/8 | 16/16 | 12,2 | 15,4 | — | 11,2 |
| 6 × 6 · desarrollo · escenarios fijos | Ruta corta | 0,46 | 100 | 8/8 | 16/16 | 10,6 | 14,5 | 12 | 4,5 |
| 6 × 6 · desarrollo · escenarios fijos | Ruta térmica | 0,46 | 100 | 8/8 | 16/16 | 16,1 | 9,2 | 239 | 24,9 |
| 6 × 6 · desarrollo · escenarios fijos | Aleatoria · 5 semillas | 0,46 | 100 | 2/40 | 11/80 | 26,0 | 0,0 | — | 16,5 |
| 10 × 10 · desarrollo · escenarios fijos | DQN v2_pilot · semilla 0 | 0,35 | 160 | 1/2 | 3/6 | 6,0 | 0,0 | — | 256,7 |
| 10 × 10 · desarrollo · escenarios fijos | Ruta corta | 0,35 | 160 | 2/2 | 6/6 | 32,0 | 53,5 | 692 | 101,3 |
| 10 × 10 · desarrollo · escenarios fijos | Ruta térmica | 0,35 | 160 | 2/2 | 6/6 | 34,0 | 32,0 | 3374 | 376,7 |
| 10 × 10 · desarrollo · escenarios fijos | Aleatoria · 5 semillas | 0,35 | 160 | 2/10 | 10/30 | 57,0 | 0,0 | — | 44,0 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | DQN v2_pilot · semilla 0 | 0,39 | 240 | 0/30 | 9/90 | — | — | — | 302,6 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Ruta corta | 0,39 | 240 | 26/30 | 84/90 | 31,8 | 55,1 | 554 | 63,5 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Ruta térmica | 0,39 | 240 | 30/30 | 90/90 | 38,5 | 33,9 | 2660 | 269,2 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Aleatoria · 5 semillas | 0,39 | 240 | 3/150 | 91/450 | 46,0 | 0,0 | — | 48,0 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Ruta corta | 0,35 | 290 | 55/60 | 175/180 | 35,2 | 43,7 | 889 | 118,8 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Ruta térmica | 0,35 | 290 | 60/60 | 180/180 | 38,5 | 12,7 | 1588 | 227,2 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Aleatoria · 5 semillas | 0,35 | 290 | 2/300 | 182/900 | 174,0 | 44,5 | — | 159,9 |
| 12 × 12 · validación · v2_12x12_v1 | Ruta corta | 0,37 | 290 | 17/20 | 57/60 | 34,8 | 38,0 | 788 | 122,5 |
| 12 × 12 · validación · v2_12x12_v1 | Ruta térmica | 0,37 | 290 | 20/20 | 60/60 | 41,0 | 10,1 | 2247 | 262,0 |
| 12 × 12 · validación · v2_12x12_v1 | Aleatoria · 5 semillas | 0,37 | 290 | 0/100 | 55/300 | — | — | — | 107,2 |

## 3. Dificultad por edificio y familia

Referencias deterministas en los casos de tres personas, juntando los conjuntos de un mismo edificio (por ejemplo, entrenamiento y validación). Las diferencias emparejadas usan solo los casos que ambas referencias resolvieron.

| Edificio | Familia | Casos | Distancia | Separación | Personas en zona de daño (media) | Corta: éxitos | Corta: pasos | Corta: daño | Térmica: éxitos | Térmica: pasos | Térmica: daño | Emparejados | Δ pasos (térmica − corta) | Δ daño (térmica − corta) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 × 10 · Edificio de 10 × 10 (building10) | Fácil | 10 | 0,15 | 0,16 | 0,0 | 10/10 | 12,4 | 1,8 | 10/10 | 12,4 | 1,8 | 10 | +0,0 | +0,0 |
| 10 × 10 · Edificio de 10 × 10 (building10) | Intermedio | 10 | 0,38 | 0,38 | 0,9 | 10/10 | 35,4 | 67,8 | 10/10 | 40,4 | 34,3 | 10 | +5,0 | -33,5 |
| 10 × 10 · Edificio de 10 × 10 (building10) | Exigente | 10 | 0,64 | 0,32 | 1,0 | 6/10 | 58,3 | 122,7 | 10/10 | 62,6 | 65,7 | 6 | +3,2 | -58,3 |
| 12 × 12 · Desvío térmico (detour) | Fácil | 14 | 0,16 | 0,23 | 0,0 | 14/14 | 16,0 | 0,0 | 14/14 | 16,0 | 0,0 | 14 | +0,0 | +0,0 |
| 12 × 12 · Desvío térmico (detour) | Intermedio | 13 | 0,34 | 0,38 | 0,5 | 10/13 | 31,7 | 62,2 | 13/13 | 41,6 | 3,5 | 10 | +5,0 | -57,6 |
| 12 × 12 · Desvío térmico (detour) | Exigente | 13 | 0,53 | 0,30 | 0,5 | 8/13 | 51,8 | 126,1 | 13/13 | 55,5 | 2,5 | 8 | +3,2 | -124,8 |
| 12 × 12 · Centro de coordinación (hub) | Fácil | 14 | 0,16 | 0,17 | 0,0 | 14/14 | 16,0 | 1,4 | 14/14 | 16,0 | 0,9 | 14 | +0,0 | -0,6 |
| 12 × 12 · Centro de coordinación (hub) | Intermedio | 13 | 0,39 | 0,38 | 0,5 | 13/13 | 43,6 | 31,3 | 13/13 | 46,5 | 19,9 | 13 | +2,9 | -11,4 |
| 12 × 12 · Centro de coordinación (hub) | Exigente | 13 | 0,57 | 0,33 | 1,8 | 13/13 | 60,2 | 76,2 | 13/13 | 62,6 | 47,1 | 13 | +2,5 | -29,1 |

## 4. Separación entre personas

Los casos de cada perfil se dividen en terciles de separación. El reparto indica cuántas personas entregó cada robot (mayor–menor). Cada robot lleva una persona a la vez, así que con tres personas todo éxito incluye al menos un segundo viaje.

| Perfil | Separación entre personas | Casos | Estrategia | Éxitos | Personas entregadas | Pasos medios (éxitos) | Daño medio (éxitos) | Esperas por episodio | Reparto de entregas en éxitos |
|---|---|---:|---|---:|---:|---:|---:|---:|---|
| 10 × 10 | baja (< 0,19) | 10 | Ruta corta | 9/10 | 29/30 | 12,7 | 2,0 | 0,9 | 2–1: 9 |
| 10 × 10 | baja (< 0,19) | 10 | Ruta térmica | 10/10 | 30/30 | 17,5 | 13,4 | 1,2 | 2–1: 10 |
| 10 × 10 | media (≥ 0,19 y < 0,37) | 8 | Ruta corta | 8/8 | 24/24 | 43,8 | 86,5 | 0,8 | 2–1: 8 |
| 10 × 10 | media (≥ 0,19 y < 0,37) | 8 | Ruta térmica | 8/8 | 24/24 | 44,8 | 41,9 | 1,8 | 2–1: 8 |
| 10 × 10 | alta (≥ 0,37) | 12 | Ruta corta | 9/12 | 31/36 | 40,4 | 80,2 | 1,0 | 2–1: 9 |
| 10 × 10 | alta (≥ 0,37) | 12 | Ruta térmica | 12/12 | 36/36 | 51,8 | 45,8 | 3,5 | 2–1: 12 |
| 12 × 12 | baja (< 0,24) | 26 | Ruta corta | 24/26 | 76/78 | 25,0 | 18,6 | 0,9 | 2–1: 24 |
| 12 × 12 | baja (< 0,24) | 26 | Ruta térmica | 26/26 | 78/78 | 27,6 | 5,9 | 1,5 | 2–1: 26 |
| 12 × 12 | media (≥ 0,24 y < 0,36) | 26 | Ruta corta | 22/26 | 74/78 | 35,0 | 45,5 | 1,2 | 2–1: 22 |
| 12 × 12 | media (≥ 0,24 y < 0,36) | 26 | Ruta térmica | 26/26 | 78/78 | 41,7 | 13,5 | 1,2 | 2–1: 26 |
| 12 × 12 | alta (≥ 0,36) | 28 | Ruta corta | 26/28 | 82/84 | 44,5 | 61,6 | 0,8 | 2–1: 26 |
| 12 × 12 | alta (≥ 0,36) | 28 | Ruta térmica | 28/28 | 84/84 | 47,5 | 16,4 | 1,6 | 2–1: 28 |

## 5. Exposición térmica inicial

Casos según cuántas personas empiezan en zona de daño. Las columnas emparejadas comparan la ruta corta y la térmica en los mismos casos resueltos por ambas.

| Perfil | Personas en zona de daño | Casos | Corta: éxitos | Corta: destruidos | Térmica: éxitos | Térmica: destruidos | Emparejados | Daño corta (emparejados) | Daño térmica (emparejados) | Pasos extra de la térmica |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 × 10 | 0 | 15 | 13/15 | 2 | 15/15 | 0 | 13 | 15,4 | 9,7 | +0,2 |
| 10 × 10 | 1 | 11 | 10/11 | 1 | 11/11 | 0 | 10 | 96,5 | 43,1 | +4,8 |
| 10 × 10 | 2 | 4 | 3/4 | 1 | 4/4 | 0 | 3 | 89,0 | 63,3 | +6,0 |
| 12 × 12 | 0 | 53 | 48/53 | 5 | 53/53 | 0 | 48 | 29,5 | 2,5 | +1,4 |
| 12 × 12 | 1 | 14 | 12/14 | 2 | 14/14 | 0 | 12 | 55,1 | 30,2 | +2,0 |
| 12 × 12 | 2 | 11 | 10/11 | 1 | 11/11 | 0 | 10 | 81,5 | 36,1 | +4,3 |
| 12 × 12 | 3 | 2 | 2/2 | 0 | 2/2 | 0 | 2 | 78,5 | 48,0 | +6,5 |

## 6. Reparto de trabajo observado

Entregas por robot, esperas y bloqueos salen de las trazas reproducidas. Describen lo que ocurrió; no prueban que una estrategia coopere mejor ni explican intenciones del agente. «Segundo viaje» cuenta los éxitos en que un robot entregó a dos o más personas: con dos personas distingue un reparto 1–1 de uno 2–0, y con tres es obligatorio porque cada robot lleva una persona a la vez.

| Conjunto | Estrategia | Éxitos | Reparto de entregas en éxitos | Éxitos con segundo viaje | Esperas por episodio | Bloqueos por episodio | Fallos de planificación | Replanificaciones por episodio |
|---|---|---:|---|---:|---:|---:|---:|---:|
| 6 × 6 · desarrollo · escenarios fijos | DQN sensors_dqn · semilla 0 | 8/8 | 2–0: 1 · 1–1: 7 | 1/8 | 1,4 | 4,1 | 0 | 0,0 |
| 6 × 6 · desarrollo · escenarios fijos | Ruta corta | 8/8 | 1–1: 8 | 0/8 | 0,8 | 0,0 | 0 | 2,1 |
| 6 × 6 · desarrollo · escenarios fijos | Ruta térmica | 8/8 | 1–1: 8 | 0/8 | 1,0 | 0,0 | 0 | 2,2 |
| 6 × 6 · desarrollo · escenarios fijos | Aleatoria | 2/40 | 1–1: 2 | 0/2 | 22,7 | 36,7 | 0 | 0,0 |
| 10 × 10 · desarrollo · escenarios fijos | DQN v2_pilot · semilla 0 | 1/2 | 2–1: 1 | 1/1 | 214,5 | 14,5 | 0 | 0,0 |
| 10 × 10 · desarrollo · escenarios fijos | Ruta corta | 2/2 | 2–1: 2 | 2/2 | 0,0 | 0,0 | 0 | 4,0 |
| 10 × 10 · desarrollo · escenarios fijos | Ruta térmica | 2/2 | 2–1: 2 | 2/2 | 0,0 | 0,0 | 0 | 4,0 |
| 10 × 10 · desarrollo · escenarios fijos | Aleatoria | 2/10 | 2–1: 2 | 2/2 | 31,3 | 36,5 | 0 | 0,0 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | DQN v2_pilot · semilla 0 | 0/30 | — | 0/0 | 80,0 | 342,1 | 0 | 0,0 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Ruta corta | 26/30 | 2–1: 26 | 26/26 | 0,9 | 0,0 | 0 | 4,4 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Ruta térmica | 30/30 | 2–1: 30 | 30/30 | 2,3 | 0,0 | 0 | 4,3 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Aleatoria | 3/150 | 2–1: 3 | 3/3 | 35,1 | 41,0 | 0 | 0,0 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Ruta corta | 55/60 | 2–1: 55 | 55/55 | 1,0 | 0,0 | 0 | 4,4 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Ruta térmica | 60/60 | 2–1: 60 | 60/60 | 1,6 | 0,0 | 0 | 4,2 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Aleatoria | 2/300 | 2–1: 2 | 2/2 | 69,1 | 54,6 | 0 | 0,0 |
| 12 × 12 · validación · v2_12x12_v1 | Ruta corta | 17/20 | 2–1: 17 | 17/17 | 0,8 | 0,0 | 0 | 4,1 |
| 12 × 12 · validación · v2_12x12_v1 | Ruta térmica | 20/20 | 2–1: 20 | 20/20 | 0,8 | 0,0 | 0 | 4,0 |
| 12 × 12 · validación · v2_12x12_v1 | Aleatoria | 0/100 | — | 0/0 | 69,2 | 54,7 | 0 | 0,0 |

## 7. Cómputo de las referencias

Estados expandidos y segundos de cómputo por episodio, separados del tiempo simulado (pasos) y de la reproducción visual. Los segundos dependen de la máquina.

| Conjunto | Familia | Referencia | Episodios | Pasos simulados (mediana) | Estados expandidos (mediana) | Estados expandidos (máximo) | Cómputo (mediana, ms) | Cómputo (máximo, ms) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 6 × 6 · desarrollo · escenarios fijos | sin familia | Ruta corta | 8 | 10 | 12 | 361 | 4,5 | 33,2 |
| 6 × 6 · desarrollo · escenarios fijos | sin familia | Ruta térmica | 8 | 14 | 239 | 1904 | 24,9 | 297,9 |
| 10 × 10 · desarrollo · escenarios fijos | Fácil | Ruta corta | 1 | 6 | 16 | 16 | 5,5 | 5,5 |
| 10 × 10 · desarrollo · escenarios fijos | Fácil | Ruta térmica | 1 | 6 | 16 | 16 | 6,8 | 6,8 |
| 10 × 10 · desarrollo · escenarios fijos | Exigente | Ruta corta | 1 | 58 | 1368 | 1368 | 197,1 | 197,1 |
| 10 × 10 · desarrollo · escenarios fijos | Exigente | Ruta térmica | 1 | 62 | 6733 | 6733 | 746,6 | 746,6 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Fácil | Ruta corta | 10 | 12 | 50 | 238 | 9,1 | 63,0 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Fácil | Ruta térmica | 10 | 12 | 50 | 942 | 10,8 | 188,8 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Intermedio | Ruta corta | 10 | 38 | 662 | 1554 | 66,7 | 210,3 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Intermedio | Ruta térmica | 10 | 42 | 2787 | 6781 | 269,2 | 545,0 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Exigente | Ruta corta | 10 | 54 | 990 | 2071 | 126,0 | 205,3 |
| 10 × 10 · desarrollo · v2_10x10_dev_v1 | Exigente | Ruta térmica | 10 | 62 | 7092 | 10674 | 694,9 | 1218,3 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Fácil | Ruta corta | 20 | 16 | 174 | 350 | 42,0 | 83,2 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Fácil | Ruta térmica | 20 | 16 | 174 | 311 | 48,6 | 95,6 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Intermedio | Ruta corta | 20 | 39 | 917 | 3528 | 139,4 | 307,3 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Intermedio | Ruta térmica | 20 | 43 | 3240 | 37172 | 438,1 | 3812,2 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Exigente | Ruta corta | 20 | 52 | 2110 | 8114 | 245,5 | 1027,0 |
| 12 × 12 · entrenamiento · v2_12x12_v1 | Exigente | Ruta térmica | 20 | 56 | 11414 | 34726 | 1370,0 | 4162,4 |
| 12 × 12 · validación · v2_12x12_v1 | Fácil | Ruta corta | 8 | 18 | 209 | 302 | 30,6 | 38,1 |
| 12 × 12 · validación · v2_12x12_v1 | Fácil | Ruta térmica | 8 | 18 | 226 | 2041 | 37,2 | 192,2 |
| 12 × 12 · validación · v2_12x12_v1 | Intermedio | Ruta corta | 6 | 44 | 2430 | 3335 | 222,8 | 306,9 |
| 12 × 12 · validación · v2_12x12_v1 | Intermedio | Ruta térmica | 6 | 52 | 4060 | 17199 | 407,6 | 1755,8 |
| 12 × 12 · validación · v2_12x12_v1 | Exigente | Ruta corta | 6 | 55 | 2498 | 4240 | 245,4 | 402,5 |
| 12 × 12 · validación · v2_12x12_v1 | Exigente | Ruta térmica | 6 | 58 | 8240 | 20525 | 816,5 | 1944,9 |

## 8. Límites

- Perfiles analizados: 6 × 6 con 2 personas, 10 × 10 con 3 personas, 12 × 12 con 3 personas. Los perfiles difieren también en cantidad de personas y límite de pasos, así que la escala no se aísla de esos factores.
- Los casos generados entraron porque una referencia los resolvió al certificarlos: el éxito de las referencias está favorecido por construcción.
- Las familias y los terciles son agrupaciones descriptivas con pocos casos por celda; no son pruebas de significancia.
- La referencia aleatoria repite la misma secuencia de acciones por semilla en todos los casos.
- Las filas DQN son modelos de desarrollo de su propio perfil. No son los modelos finales (SARB-019) y ningún checkpoint se evalúa en otro perfil.
