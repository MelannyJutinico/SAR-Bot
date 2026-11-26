# Primer controlador DQN

Checkpoint de desarrollo entrenado por el proyecto. No es una política final validada.

- Semilla de entrenamiento: 0.
- Pasos totales de la ejecución: 82000.
- Checkpoint seleccionado: 42000, al terminar navegación.
- Configuración: `metadata.json` y `configs/dqn_initial.json`.
- Evidencia de selección, incluido modelo sin entrenar: `evaluations.jsonl`.
- Comparación con referencias y comprobación adicional del pasillo: `comparison.csv`.
- Resumen, último checkpoint y SHA-256 del modelo: `summary.json`.

Completa los cuatro escenarios del currículo, igualando a la referencia en tiempo y daño. Falla en el pasillo compartido. Estos resultados no demuestran generalización ni superioridad térmica.

Desde la raíz del proyecto:

```powershell
uv sync --extra rl --python 3.12
uv run --extra rl python scripts/demo.py --strategy dqn --model artifacts/initial_dqn/model.zip
```

No hace falta volver a entrenar para reproducir este modelo. El ZIP fue generado por Stable-Baselines3.
