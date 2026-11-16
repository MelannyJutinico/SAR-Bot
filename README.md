# SAR-Bot

Simulación académica de rescate cooperativo: dos robots deben evacuar a dos sobrevivientes en un edificio 2D con riesgo térmico acumulativo.

**Asignatura:** Sistemas Inteligentes. **Equipo:** cuatro personas. **Plazo objetivo:** una semana.

## Estado del proyecto

Ya está implementado el motor de simulación: plano, movimiento simultáneo de dos robots, exposición térmica, rescate, finalización y escenarios reproducibles, con pruebas de las reglas críticas. Todavía faltan el adaptador de Gymnasium, el entrenamiento DQN, la estrategia de referencia, la visualización y la evaluación. No hay una política entrenada ni resultados experimentales.

- [Contexto, alcance y reglas acordadas](docs/CONTEXTO.md)
- [Plan de trabajo y base de la persona 1](docs/PLAN_DE_TRABAJO.md)
- [Diseño técnico de la base implementada](docs/DISENO.md)

Nosotros asumimos el rol de **persona 1**: construir la base integrada, implementar el aprendizaje y orientar la integración para que las otras tres personas continúen el entorno, la visualización y la evaluación.

## Objetivo

Investigar si un controlador aprendido puede coordinar dos robots para completar rescates, equilibrando duración de la misión y daño térmico. Se comparará con una estrategia programada bajo las mismas condiciones.

## Tecnología prevista

Python 3.11 o superior, NumPy, Gymnasium, Stable-Baselines3 con DQN y Pygame. Las versiones están fijadas en [pyproject.toml](pyproject.toml) y se verificaron juntas en Windows con Python 3.11.9 (torch 2.15.0 CPU).

## Principio térmico

El daño depende de la **temperatura y el tiempo de exposición**, incluso cuando el robot espera. Ambos robots acumulan exposición en cada paso global. La velocidad de reproducción de la interfaz no modifica el tiempo simulado.

## Desarrollo

Instalación en un entorno virtual (desde la raíz del repositorio):

```bash
python -m venv .venv
```

En Windows, activar con `.venv\Scripts\activate`; en Linux o macOS, con `source .venv/bin/activate`. Luego:

```bash
python -m pip install -e ".[dev]"
```

```bash
python -m pytest
```

Todavía no hay comandos de entrenamiento ni de demostración. Los cambios se trabajan en ramas `feature/…` y se integran sobre una versión ejecutable común.
