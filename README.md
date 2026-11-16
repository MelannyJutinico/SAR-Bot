# SAR-Bot

Simulación académica de rescate cooperativo: dos robots deben evacuar a dos sobrevivientes en un edificio 2D con riesgo térmico acumulativo.

**Asignatura:** Sistemas Inteligentes. **Equipo:** cuatro personas. **Plazo objetivo:** una semana.

## Estado del proyecto

El repositorio comienza con la documentación del alcance y el plan de trabajo. Todavía no contiene el simulador, una política entrenada ni resultados experimentales.

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

La implementación aún está pendiente. No hay comandos de entrenamiento o demostración disponibles. Los cambios se trabajarán en ramas `feature/…` y se integrarán sobre una versión ejecutable común.
