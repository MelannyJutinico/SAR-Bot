# SAR-Bot

Simulación académica de rescate cooperativo: dos robots deben evacuar a dos sobrevivientes en un edificio 2D con riesgo térmico acumulativo.

**Asignatura:** Sistemas Inteligentes. **Equipo:** cuatro personas. **Plazo objetivo:** una semana.

## Estado del proyecto

Ya existe el motor, navegación de referencia, evaluación CSV y un entorno Gymnasium con entrenamiento DQN reproducible. Se ejecutó un primer entrenamiento de 82000 pasos y se conserva un checkpoint cargable. Completa los cuatro escenarios del currículo, pero falla en el pasillo compartido e iguala el daño de la referencia en los mapas térmicos: todavía no demuestra generalización ni mejor gestión del calor. La interfaz Pygame sigue pendiente.

- [Contexto, alcance y reglas acordadas](docs/CONTEXTO.md)
- [Plan de trabajo y base de la persona 1](docs/PLAN_DE_TRABAJO.md)
- [Referencias y primeros resultados de desarrollo](docs/EVALUACION.md)
- [Instalación, observaciones, recompensas y entrenamiento](docs/APRENDIZAJE.md)

Nosotros asumimos el rol de **persona 1**: construir la base integrada, implementar el aprendizaje y orientar la integración para que las otras tres personas continúen el entorno, la visualización y la evaluación.

## Objetivo

Investigar si un controlador aprendido puede coordinar dos robots para completar rescates, equilibrando duración de la misión y daño térmico. Se comparará con una estrategia programada bajo las mismas condiciones.

## Tecnología prevista

Python, NumPy, Gymnasium y Stable-Baselines3 con DQN. Las versiones están fijadas en `uv.lock`, con PyTorch CPU. Pygame se incorporará como interfaz.

## Principio térmico

El daño depende de la **temperatura y el tiempo de exposición**, incluso cuando el robot espera. Ambos robots acumulan exposición en cada paso global. La velocidad de reproducción de la interfaz no modifica el tiempo simulado.

## Desarrollo

El motor y las referencias usan únicamente la biblioteca estándar de Python 3.11 o superior. El aprendizaje requiere el extra `rl`. Los cambios se trabajan en ramas `feature/…`.

### Ejecutar el agente ya entrenado

```powershell
uv sync --extra rl --python 3.12
uv run --extra rl python scripts/demo.py --strategy dqn --model artifacts/initial_dqn/model.zip
```

Para comparar el modelo cargado con las referencias:

```powershell
uv run --extra rl python scripts/evaluate_dqn.py --model artifacts/initial_dqn/model.zip
```

El modelo incluido es el mejor checkpoint de desarrollo, a los 42000 pasos; no el último checkpoint, que empeoró en el escenario más caliente. Sus metadatos y resultados están en `artifacts/initial_dqn/`. Es una primera semilla de entrenamiento y no una entrega final validada.

### Entrenar y verificar

```powershell
uv run --extra rl python -m unittest discover -s tests -v
uv run --extra rl python scripts/train.py --run-dir outputs/nuevo-experimento
```

El directorio del experimento debe estar vacío. El entrenamiento usa `configs/dqn_initial.json`, registra episodios y evaluaciones, y guarda modelos por etapa, final y mejor. No hace falta entrenar para ejecutar el checkpoint incluido.

### Ejecutar solo el motor y las referencias

Con Python disponible:

```powershell
python scripts/demo.py
python scripts/demo.py --json
python -m unittest discover -s tests -v
```

Si Python está administrado por `uv`, ejecutar desde la raíz del repositorio:

```powershell
uv run --no-project --python 3.12 scripts/demo.py
uv run --no-project --python 3.12 -m unittest discover -s tests -v
```

La demostración usa una secuencia programada para `scenarios/demo.json`: rescata a las dos víctimas en diez pasos globales; los robots terminan con integridad 82 y 100. **No es una política aprendida ni una referencia general de navegación.**

Para usar navegación automática y calcular rutas a partir del mapa:

```powershell
uv run --no-project --python 3.12 scripts/demo.py --strategy shortest
uv run --no-project --python 3.12 scripts/demo.py --strategy shortest --scenario scenarios/pasillo_compartido.json
uv run --no-project --python 3.12 scripts/demo.py --strategy random --seed 0
```

`shortest` asigna víctimas distintas y busca movimientos conjuntos para llegar a los objetivos actuales en el menor número de pasos, sin considerar temperatura. Puede esperar o apartar un robot para evitar bloqueos; no garantiza completar cualquier misión. `random` selecciona entre las 25 acciones conjuntas usando una semilla reproducible. La demostración devuelve código de salida 1 si la misión fracasa o agota el tiempo.

Para evaluar todas las referencias sobre los tres escenarios actuales:

```powershell
uv run --no-project --python 3.12 scripts/evaluate.py
```

El CSV se guarda en `outputs/reference_results.csv`, excluido de Git porque puede regenerarse. Se pueden indicar `--scenarios`, `--strategy`, `--seed` y `--output`. Esta ejecución produce un episodio por escenario y estrategia; no es una evaluación estadística ni un conjunto de prueba reservado.

### Archivos para continuar

| Archivo | Función |
|---|---|
| `src/sar_bot/core/simulation.py` | Estado y reglas del entorno |
| `scenarios/demo.json` | Primer mapa y parámetros térmicos |
| `scripts/demo.py` | Reproducción por consola y salida JSON |
| `tests/test_simulation.py` | Verificación de reglas críticas |
| `src/sar_bot/agents/reference.py` | Asignación, navegación conjunta y política aleatoria |
| `scripts/evaluate.py` | Ejecución de referencias y exportación CSV |
| `tests/test_reference.py` | Verificación de navegación y evaluación |
| `src/sar_bot/env/rescue_env.py` | Observaciones y recompensa de Gymnasium |
| `scripts/train.py` | Entrenamiento por etapas y checkpoints |
| `scripts/evaluate_dqn.py` | Comparación de una política guardada con referencias |
| `configs/dqn_initial.json` | Configuración reproducible del primer experimento |
| `artifacts/initial_dqn/` | Modelo seleccionado, metadatos y resultados medidos |

`RescueSimulation.step(acción_conjunta)` avanza una unidad de tiempo para ambos robots. `snapshot()` expone datos JSON, y `reset()` reinicia el escenario estático. La acción conjunta es `5 * acción_robot_1 + acción_robot_2`, con acciones `UP=0`, `DOWN=1`, `LEFT=2`, `RIGHT=3`, `WAIT=4`.

La validación actual comprueba estructura y conectividad del mapa. La misión del escenario de demostración se verifica con una trayectoria completa. Todavía no existe un validador general de viabilidad térmica y coordinación para escenarios arbitrarios.

### Próximo hito

Mejorar exploración y variedad de escenarios, separar entrenamiento/validación/prueba y comprobar adaptación térmica. La visualización Pygame puede consumir el mismo motor y `DQNPolicy`, sin replicar reglas.
