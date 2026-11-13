# Piloto V2: 10 × 10, tres personas

Este checkpoint prueba el contrato de aprendizaje ampliado. **No es un modelo validado para el edificio grande ni para ubicaciones arbitrarias.**

- Configuración: `configs/dqn_v2_pilot.json`.
- Perfil: 10 × 10, tres personas, sensores, 302 entradas y 25 acciones.
- Semilla 0, 90000 pasos de entrenamiento.
- Checkpoint seleccionado: 65000 pasos nuevos.
- Guía de distancia acotada a 40; se conserva la escala histórica de V1 cuando no se configura esa cota.

| Escenario | Resultado DQN recargado | Rescates | Pasos | Daño |
|---|---|---:|---:|---:|
| Rescate cercano de tres personas | Éxito | 3/3 | 6 | 0 |
| Edificio con habitaciones y dos focos | Límite de tiempo | 0/3 | 240 | 0 |

Ambos casos se usaron en entrenamiento y selección. No son una prueba reservada. Las referencias sí completan el edificio: ruta corta en 58 pasos con daño total 107 y térmica en 62 con daño 64. DQN necesita un currículo más gradual y ubicaciones variadas antes de considerarlo una solución del nuevo alcance.

Para reproducir el caso que ya aprendió:

```powershell
uv run --extra ui --extra rl python scripts/ui.py --scenario scenarios/v2/warmup_10x10.json --strategy dqn --model artifacts/v2_pilot/model.zip
```

Para mostrar la misión grande resuelta mediante una referencia:

```powershell
uv run --extra ui --extra rl python scripts/ui.py --scenario scenarios/v2/building_10x10.json --strategy thermal
```

El modo se identifica en pantalla; no se sustituye DQN silenciosamente. `metadata.json`, `evaluations.jsonl`, `comparison.csv` y `summary.json` conservan configuración, evolución, fallos y hash del modelo.
