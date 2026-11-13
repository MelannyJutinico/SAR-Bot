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

## Resultado del primer entrenamiento real

Se ejecutaron 82000 pasos con semilla 0 en CPU. La última evaluación quedó registrada a los 172,84 segundos desde el inicio del callback; la carga de dependencias y preparación están fuera de ese tiempo. El modelo sin entrenar no completó ninguna de las cuatro misiones del currículo.

El mejor checkpoint se obtuvo a los 42000 pasos, al terminar navegación. Se volvió a cargar del archivo y completó las cuatro misiones. La etapa térmica posterior fue inestable y no produjo un mejor checkpoint: al terminar rescató solo una víctima en `ruta_caliente`, aunque recibió daño cero. Esto muestra por qué conservar éxito y rescates como criterios de selección es necesario.

Los archivos compartibles del experimento están en `artifacts/initial_dqn/`: modelo, metadatos, evaluación temporal, comparación CSV y resumen con SHA-256. El entrenamiento completo, modelos por etapa y registros por episodio permanecen en `outputs/dqn-initial/`, fuera de Git.

El checkpoint seleccionado iguala a la referencia en los mapas del currículo; no demostró mejor gestión térmica. Falla en el pasillo compartido, que no formó parte del currículo. Una sola semilla y mapas usados para selección no permiten afirmar generalización.

Un próximo experimento debe revisar exploración al cambiar de etapa, aumentar diversidad gradualmente y separar validación y prueba. No basta con aumentar pasos: en esta ejecución entrenar más empeoró parte de la conducta.

## Reproducir un controlador guardado

```powershell
uv run --extra rl python scripts/demo.py --strategy dqn --model outputs/dqn-initial/best_model.zip
```

Se puede agregar `--scenario scenarios/ruta_caliente.json` o `--json`. La política actúa sobre la observación actual del motor, sin usar la referencia de caminos. La carga comprueba dimensiones del modelo y espacio de acciones. El entrenamiento de rescate cercano usa un mapa de 6 × 6 para mantener el mismo tamaño de observación en todas las etapas.

Para compartir el checkpoint sin copiar todo el entrenamiento, después de generar `comparison.csv`:

```powershell
uv run --extra rl python scripts/package_model.py --run-dir outputs/dqn-initial --destination artifacts/nuevo-modelo
```

El destino debe ser nuevo. El primer modelo ya está empaquetado y se puede reproducir directamente:

```powershell
uv run --extra rl python scripts/demo.py --strategy dqn --model artifacts/initial_dqn/model.zip
```

## Segundo experimento: cooperación y exploración por etapa

`configs/dqn_cooperation.json` parte del modelo inicial y añade un escenario cercano con salida compartida antes del pasillo completo. Duplica entradas de algunos mapas para aumentar su probabilidad de muestreo; cada índice sigue seleccionándose uniformemente.

Se observó que, con el progreso acumulado y la fracción anterior, la etapa térmica comenzaba ya en la exploración mínima. Las etapas nuevas permiten declarar `exploration` con probabilidades inicial y final y fracción de decaimiento. `StageExploration` convierte el progreso acumulado de SB3 a progreso local: cada etapa reinicia en 0,6 y desciende a 0,05 durante su primer 80%.

El experimento usa 20000 pasos de paso compartido cercano, 60000 de cooperación y 80000 térmicos. La penalización por daño pasa a −2. Estos cambios se estudian juntos como un experimento de desarrollo; no permiten atribuir causalmente una mejora a uno de ellos sin ablaciones.

```powershell
uv run --extra rl python scripts/train.py --config configs/dqn_cooperation.json --run-dir outputs/dqn-cooperation
```

Al inicializar desde un ZIP se conservan pesos y optimizador, pero se crea una memoria de experiencias nueva. El contador del nuevo experimento empieza en cero y los pasos previos del modelo quedan en metadatos. El modelo original y su evidencia no se sobrescriben.

Los seis mapas de control también se usan para entrenar. Este experimento busca corregir fallos conocidos, no medir generalización. La referencia térmica se usa únicamente para comparar, no para proporcionar acciones al agente.

## Fuentes técnicas

- [Gymnasium: API del entorno](https://gymnasium.farama.org/api/env/)
- [Stable-Baselines3: entornos personalizados](https://stable-baselines3.readthedocs.io/en/master/guide/custom_env.html)
- [Stable-Baselines3: DQN](https://stable-baselines3.readthedocs.io/en/master/modules/dqn.html)
