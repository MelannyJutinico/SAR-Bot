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

La observación original (modo `full`) tiene `2 × ancho × alto + 25` valores float32 entre 0 y 1; 97 para 6 × 6. El modo recomendado `sensors` añade otros 60, descritos al final. Orden original:

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

## Separación de escenarios para las próximas comprobaciones

`configs/scenario_splits.json` registra seis escenarios de entrenamiento, dos de validación y dos de prueba. Son configuraciones distintas, no copias idénticas con otro nombre. La viabilidad de los mapas nuevos se verificó con una misión completa de la referencia, sin consultar DQN.

Los mapas de validación y prueba no participan en este segundo entrenamiento ni en su selección de checkpoint. Se comprobarán después de congelar el modelo. Si sus fallos se usan para ajustar futuros experimentos, deberán considerarse datos de desarrollo y reservarse nuevos casos para una prueba final independiente.

```powershell
uv run --extra rl python scripts/evaluate_dqn.py --model artifacts/initial_dqn/model.zip --split validation --output outputs/validation.csv
uv run --extra rl python scripts/evaluate_dqn.py --model artifacts/initial_dqn/model.zip --split test --output outputs/test.csv
```

Estos comandos son ejemplos de uso; no implica que se haya evaluado ya cada modelo sobre esas particiones. Cada comparación genera un CSV y un archivo `.metadata.json` con partición, hashes de modelo y escenarios, recompensas y semilla. Dos casos de prueba solo constituyen una comprobación inicial; no permiten una conclusión estadística de generalización.

## Tercer experimento: sensores locales explícitos

El segundo experimento completó cinco de los seis controles con su mejor checkpoint: aprendió el paso compartido cercano, pero todavía entregó una sola víctima en el pasillo largo. Algunos checkpoints resolvieron el pasillo a costa de perder otras tareas. La exploración por etapas no bastó para consolidarlas.

Se añadió un modo opcional `observation_mode="sensors"`. Conserva los 97 valores originales y añade 60: por cada robot y cada una de las cinco acciones, informa legalidad frente a paredes, ocupación por el compañero, temperatura de la celda resultante y distancia de camino hasta base y ambas víctimas. Las distancias ignoran calor y se normalizan por el número de celdas; no son acciones del planificador ni un plan de rescate conjunto.

Esto evita que la red tenga que aprender primero a indexar la matriz del edificio para reconocer riesgos inmediatos. DQN sigue eligiendo las 25 acciones conjuntas y aprendiendo sus consecuencias. El motor, la exposición y los objetivos de misión no cambian.

El modo completo original sigue disponible y los modelos previos continúan cargando con sus 97 entradas. Los comandos de evaluación y reproducción identifican el esquema por las dimensiones de entrada del modelo. El modelo con sensores usa 157 entradas para 6 × 6.

`configs/dqn_sensors.json` entrena desde cero (no usa pesos de otra dimensión): 15000 pasos de rescates cercanos, 50000 de cooperación y 90000 térmicos. Mantiene la penalización de daño −2 y la exploración por etapa. Usa únicamente la partición de entrenamiento.

```powershell
uv run --extra rl python scripts/train.py --config configs/dqn_sensors.json --run-dir outputs/dqn-sensors
```

No se han usado los resultados de validación o prueba para diseñar este cambio.

### Resultado del tercer experimento

Se entrenaron 155000 pasos desde cero con semilla 0. El mejor checkpoint se obtuvo a los 60000; el último volvió a perder tareas térmicas. Se recargó el checkpoint seleccionado y resolvió los seis controles: warmup en 3 pasos, navegación en 11, paso cercano en 6, rescate inicial en 13, ruta caliente en 10 y pasillo largo en 22.

Después de fijar el modelo se ejecutaron las particiones nuevas: completó los dos casos de validación y los dos de prueba. No se modificaron pesos, hiperparámetros o selección usando esos resultados. Se conserva la evidencia y sus hashes en `artifacts/sensors_dqn/`.

El pasillo largo ahora queda resuelto con un único controlador que también completa las otras cinco tareas. La optimización térmica no está lograda: mantiene 18 y 74 puntos de daño en los dos mapas térmicos originales. Los cambios de inicialización, sensores, tasa de aprendizaje y muestreo no se aislaron en ablaciones; no puede atribuirse toda la mejora exclusivamente a los sensores.

Los diez casos evaluados usan mapa conocido y distancias calculadas a partir del mapa; no se evalúa exploración a ciegas. Una sola semilla y dos configuraciones de prueba no bastan para generalización amplia.

## Fuentes técnicas

- [Gymnasium: API del entorno](https://gymnasium.farama.org/api/env/)
- [Stable-Baselines3: entornos personalizados](https://stable-baselines3.readthedocs.io/en/master/guide/custom_env.html)
- [Stable-Baselines3: DQN](https://stable-baselines3.readthedocs.io/en/master/modules/dqn.html)
