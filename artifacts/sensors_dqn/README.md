# Controlador recomendado: DQN con sensores

- Configuración: `configs/dqn_sensors.json`.
- Entrenamiento desde cero, semilla 0, 155000 pasos.
- Checkpoint seleccionado: 60000 pasos, mediante seis controles de entrenamiento.
- Observación: 157 valores, mapa completo y sensores locales.
- Pruebas posteriores al cierre del modelo: dos configuraciones de validación y dos de prueba.

El checkpoint cargado completa las diez misiones evaluadas. En el pasillo largo rescata a ambas víctimas en 22 pasos sin daño. No demuestra superioridad térmica: en el mapa más caliente mantiene 74 puntos de daño, frente a 34 de la referencia térmica.

Una semilla y dos casos de prueba son evidencia inicial limitada, no una estimación estadística de generalización. Los mapas de prueba no se usaron para cambiar este modelo; si se usan para ajustar otro experimento, se deberán reservar nuevos casos para la prueba final.

Desde la raíz del proyecto:

```powershell
uv sync --extra rl --python 3.12
uv run --extra rl python scripts/demo.py --strategy dqn --model artifacts/sensors_dqn/model.zip --scenario scenarios/pasillo_compartido.json
uv run --extra rl python scripts/evaluate_dqn.py --model artifacts/sensors_dqn/model.zip --split test --output outputs/reproduce_test.csv
```

`comparison.csv`, `validation.csv` y `test.csv` incluyen DQN y las tres referencias. Sus archivos de metadatos registran partición, modelo, entradas y recompensas. `summary.json` contiene el hash del ZIP, checkpoint elegido, resultado del último checkpoint y conteos por partición. `evaluations.jsonl` conserva la evolución completa de los controles, incluidos los fallos.

El último checkpoint de entrenamiento fue peor y no reemplaza este archivo. Los experimentos anteriores siguen disponibles en sus propios directorios.
