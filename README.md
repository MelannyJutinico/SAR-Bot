# SAR-Bot

Simulación académica de rescate cooperativo: dos robots deben evacuar a dos sobrevivientes en un edificio 2D con riesgo térmico acumulativo.

**Asignatura:** Sistemas Inteligentes. **Equipo:** cuatro personas. **Plazo objetivo:** una semana.

## Estado del proyecto

La base funciona de principio a fin:
- Motor de simulación con dos robots, calor y rescate.
- Escenarios reproducibles con particiones de entrenamiento, validación y prueba.
- Entorno de Gymnasium y estrategia de referencia.
- Entrenamiento DQN con guardado y carga.
- Evaluación exportada a CSV.
- Demo en Pygame.

Los hiperparámetros y la recompensa son iniciales. Todavía no hay una política seleccionada ni resultados experimentales finales.

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

Pruebas:

```bash
python -m pytest
```

Demo visual de la estrategia de referencia (Espacio pausa, N siguiente, +/- velocidad, E estrategia, Esc salir):

```bash
python scripts/play.py
```

Evaluar estrategias en validación y exportar un CSV a `outputs/`:

```bash
python scripts/evaluate.py --strategy referencia aleatoria
```

Entrenar DQN por etapas. Primero dos víctimas sin calor; el modelo se guarda en `models/<corrida>/` (unos 15 minutos):

```bash
python scripts/train.py --config configs/sin_calor.toml --timesteps 250000 --name etapa2_s0
```

Después la etapa con calor, partiendo del modelo anterior (sin ese punto de partida no aprende bien):

```bash
python scripts/train.py --config configs/base.toml --timesteps 250000 --init-model models/etapa2_s0/final_model.zip --set training.exploration_initial_eps=0.3 --name etapa3_desde2_s0
```

Comparar el modelo con la referencia y verlo en acción:

```bash
python scripts/evaluate.py --strategy referencia dqn --model models/etapa3_desde2_s0/best_model.zip
```

```bash
python scripts/play.py --strategy dqn --model models/etapa3_desde2_s0/best_model.zip
```

Los detalles de observación, recompensa, particiones y referencia están en [docs/DISENO.md](docs/DISENO.md). Los cambios se trabajan en ramas `feature/…` y se integran sobre una versión ejecutable común.
