# Entorno de aprendizaje

## Instalación

```powershell
uv sync --extra rl --python 3.12
uv run --extra rl python -m unittest discover -s tests -v
```

`uv.lock` fija versiones resueltas. PyTorch usa el índice oficial CPU. La simulación y las referencias siguen funcionando sin instalar el extra `rl`.

## Contrato Gymnasium

`RescueEnv` recibe una lista de escenarios con las mismas dimensiones. `reset(seed=…)` selecciona uno mediante un generador reproducible. `reset(options={"scenario_index": i})` permite seleccionar un escenario explícito.

El espacio de acción es `Discrete(25)` con la codificación conjunta existente. El adaptador llama una sola vez al motor por acción, conserva la exposición simultánea y distingue `terminated` de `truncated`.

La observación tiene `2 × ancho × alto + 25` valores float32 entre 0 y 1; 97 para 6 × 6. Orden:

1. Paredes, por filas.
2. Temperaturas por filas, recortadas al intervalo [0, 200] y divididas por 200. Esto normaliza la observación; el motor sigue usando la temperatura original.
3. Coordenadas normalizadas de base, víctima 0, víctima 1, robot 0 y robot 1.
4. Integridad de ambos robots dividida por 100.
5. Carga de cada robot, con tres indicadores: ninguna, víctima 0 o víctima 1.
6. Estado de cada víctima, con tres indicadores: pendiente, transportada o entregada.
7. Fracción de pasos consumidos del límite del escenario.

## Recompensas iniciales

| Componente | Valor |
|---|---:|
| Paso global | −1 |
| Nueva recogida | +5 |
| Entrega de una víctima | +50 |
| Misión completa | +100 |
| Destrucción | −100 |
| Límite de tiempo | −20 |
| Punto de integridad perdido, sumado entre robots | −1 |

Se añade una guía potencial `2 × (gamma × Phi(siguiente) − Phi(actual))`, con gamma 0.99. `Phi` es el negativo del mínimo trabajo restante en distancias de camino, ignorando calor y conflictos. Considera carga actual, retorno y posibles asignaciones de víctimas pendientes. No decide las acciones ni incorpora trayectorias de la referencia al entrenamiento.

El potencial se hace cero en estados terminales reales. En truncamiento se conserva para que el aprendizaje pueda tratar correctamente el límite de tiempo. El descuento de DQN debe coincidir con el descuento de esta recompensa.

`info["reward_terms"]` permite auditar cada componente. La tasa de rescate real continúa siendo la métrica principal; mejorar retorno no demuestra por sí solo una mejor política.

## Validación actual

Se verificaron los contratos oficiales con `gymnasium.utils.env_checker.check_env` y `stable_baselines3.common.env_checker.check_env`, además de observaciones, recompensas de entrega, exposición, semilla y finalización.

También existe una prueba que entrena DQN durante 32 pasos, guarda el modelo, vuelve a cargarlo y verifica que conserve sus predicciones. Comprueba integración; no convergencia.

## Entrenamiento por etapas

```powershell
uv run --extra rl python scripts/train.py --run-dir outputs/dqn-initial
uv run --extra rl python scripts/evaluate_dqn.py --model outputs/dqn-initial/best_model.zip
```

`configs/dqn_initial.json` fija semilla, recompensas, arquitectura, hiperparámetros, escenarios y duración de cada etapa: 12000 pasos de rescate cercano sin calor, 30000 de navegación y 40000 con mezcla de escenarios térmicos. Se comparte el modelo y la memoria de experiencias entre etapas. El entrenamiento usa CPU y un hilo de PyTorch.

El directorio de ejecución debe estar vacío. Guarda metadatos, hashes y copias de los escenarios, registros de episodios, evaluaciones periódicas, modelos por etapa, modelo final y mejor modelo de desarrollo. El mejor se elige por número de misiones completas, después víctimas entregadas y finalmente retorno. El modelo sin entrenar también se evalúa antes del primer paso de aprendizaje.

**Los cuatro escenarios de evaluación inicial también aparecen en el entrenamiento.** Estos controles sirven para diagnosticar si aprende la tarea y para seleccionar un checkpoint; no constituyen prueba reservada. No se deben publicar como evidencia de generalización.

La comparación carga las recompensas de `metadata.json` junto al modelo, si existe; permite indicar otro archivo con `--metadata`. Sin metadatos usa `RewardConfig` predeterminado. Las métricas de misión siempre proceden del motor.

Los resultados reales del primer entrenamiento se registrarán al terminar la ejecución.

## Reproducir un controlador guardado

```powershell
uv run --extra rl python scripts/demo.py --strategy dqn --model outputs/dqn-initial/best_model.zip
```

Se puede agregar `--scenario escenarios/archivo.json` con la ruta real correspondiente (por ejemplo `scenarios/ruta_caliente.json`) o `--json`. La política actúa sobre la observación actual del motor, sin usar la referencia de caminos. La carga comprueba dimensiones del modelo y espacio de acciones. El entrenamiento de rescate cercano usa un mapa de 6 × 6 para mantener el mismo tamaño de observación en todas las etapas.

## Fuentes técnicas

- [Gymnasium: API del entorno](https://gymnasium.farama.org/api/env/)
- [Stable-Baselines3: entornos personalizados](https://stable-baselines3.readthedocs.io/en/master/guide/custom_env.html)
- [Stable-Baselines3: DQN](https://stable-baselines3.readthedocs.io/en/master/modules/dqn.html)
