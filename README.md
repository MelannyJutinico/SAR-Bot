# SAR-Bot

Simulación académica de rescate cooperativo: dos robots deben evacuar a dos sobrevivientes en un edificio 2D con riesgo térmico acumulativo.

**Asignatura:** Sistemas Inteligentes. **Equipo:** cuatro personas. **Plazo objetivo:** una semana.

## Estado del proyecto

Ya existe una primera versión del motor: dos robots, acciones conjuntas, colisiones, rescates automáticos, temperatura y daño acumulado por paso global. Incluye una demostración por consola y verificaciones de las reglas. Todavía no hay una política entrenada ni resultados de aprendizaje.

- [Contexto, alcance y reglas acordadas](docs/CONTEXTO.md)
- [Plan de trabajo y base de la persona 1](docs/PLAN_DE_TRABAJO.md)

Nosotros asumimos el rol de **persona 1**: construir la base integrada, implementar el aprendizaje y orientar la integración para que las otras tres personas continúen el entorno, la visualización y la evaluación.

## Objetivo

Investigar si un controlador aprendido puede coordinar dos robots para completar rescates, equilibrando duración de la misión y daño térmico. Se comparará con una estrategia programada bajo las mismas condiciones.

## Tecnología prevista

Python, NumPy, Gymnasium, Stable-Baselines3 con DQN y Pygame. Las versiones y los comandos de instalación se fijarán al implementar la base y verificar compatibilidad.

## Principio térmico

El daño depende de la **temperatura y el tiempo de exposición**, incluso cuando el robot espera. Ambos robots acumulan exposición en cada paso global. La velocidad de reproducción de la interfaz no modifica el tiempo simulado.

## Desarrollo

Esta etapa usa únicamente la biblioteca estándar de Python 3.11 o superior. Pygame, Gymnasium y DQN se incorporarán después. Los cambios se trabajan en ramas `feature/…`.

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

### Archivos para continuar

| Archivo | Función |
|---|---|
| `src/sar_bot/core/simulation.py` | Estado y reglas del entorno |
| `scenarios/demo.json` | Primer mapa y parámetros térmicos |
| `scripts/demo.py` | Reproducción por consola y salida JSON |
| `tests/test_simulation.py` | Verificación de reglas críticas |

`RescueSimulation.step(acción_conjunta)` avanza una unidad de tiempo para ambos robots. `snapshot()` expone datos JSON, y `reset()` reinicia el escenario estático. La acción conjunta es `5 * acción_robot_1 + acción_robot_2`, con acciones `UP=0`, `DOWN=1`, `LEFT=2`, `RIGHT=3`, `WAIT=4`.

La validación actual comprueba estructura y conectividad del mapa. La misión del escenario de demostración se verifica con una trayectoria completa. Todavía no existe un validador general de viabilidad térmica y coordinación para escenarios arbitrarios.

### Próximo hito

Construir la estrategia de referencia con búsqueda de caminos y el adaptador Gymnasium, fijar recompensas y entrenar primero sin calor. La visualización puede consumir el estado del mismo motor mientras se desarrolla el aprendizaje.
