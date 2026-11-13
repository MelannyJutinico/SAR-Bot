# Interfaz inicial de SAR-Bot

## Abrir la aplicación

Desde la raíz del repositorio:

```powershell
uv sync --extra ui --extra rl --python 3.12
uv run --extra ui --extra rl python scripts/ui.py
```

La aplicación abre el pasillo compartido con el checkpoint recomendado en `artifacts/sensors_dqn/model.zip`. La misión comienza pausada. La carga inicial del modelo puede tomar unos segundos; la ventana indica que está preparando la misión.

La ventana inicial se ajusta al escritorio y se puede redimensionar, conservando las proporciones de la presentación. No se necesita volver a entrenar.

## Controles

| Control | Comportamiento |
|---|---|
| Escenario | Cambia el edificio y reinicia la misión |
| Estrategia | DQN, ruta más corta, ruta térmica o acciones aleatorias |
| Iniciar / Pausar / Continuar | Reproduce o detiene la misión |
| Un paso | Avanza exactamente un paso global y deja la reproducción pausada |
| Reiniciar | Regresa al estado inicial, sin cambiar el escenario ni la semilla |
| Repetir misión | Reinicia y vuelve a reproducir después de finalizar |
| Velocidad | De 1 a 12 pasos simulados por segundo de reproducción |
| Mapa de calor | Muestra u oculta el coloreado y las temperaturas de las celdas |
| Mostrar recorridos | Muestra u oculta las trayectorias de ambos robots |
| Cursor sobre una celda | Informa temperatura y daño por paso de exposición |

Atajos: espacio para iniciar/pausar, N para un paso, R para reiniciar, H para calor, T para recorridos, + y − para velocidad. Escape cierra el selector abierto. El cierre de la ventana termina la aplicación.

## Qué representa

- Robots 1 y 2: círculos cian y violeta. Ambos pueden compartir la base.
- Personas pendientes: figura dorada en la celda. Al recogerlas aparece una insignia dorada junto al robot.
- Base: celda con borde verde.
- Obstáculos: celdas grises con trama diagonal.
- Foco térmico: marca dorada en la celda de mayor temperatura, cuando hay calor elevado.
- Paneles: rescates entregados, pasos globales, daño total, integridad, temperatura y carga de cada robot.

La leyenda usa los mismos umbrales del motor: daño 0, 2, 5 o 10 por paso. El daño se calcula para ambos robots, incluso cuando esperan. La velocidad visual no lo modifica.

El indicador de personas rescatadas aumenta al entregarlas en la base, no al recogerlas. La interfaz distingue misión completada, destrucción y límite de tiempo.

## Arquitectura

`prepare_episode()` ejecuta la estrategia seleccionada sobre `RescueSimulation` y conserva estados inmutables de cada paso real. La preparación ocurre en un trabajador para evitar bloquear la ventana durante la inferencia o la planificación. Al cambiar la configuración se descarta cualquier resultado anterior pendiente.

`Playback` solo selecciona qué estado se muestra. Pygame no recalcula movimiento, daño o rescates. Pausar y reiniciar no alteran los resultados del episodio; la política aleatoria usa una semilla fija para permitir repetirla.

Esta primera versión reproduce una misión preparada. No entrena en vivo ni permite editar el mapa durante el episodio. Las gráficas de entrenamiento y comparación permanecen fuera de esta ventana; son ampliaciones posibles para el integrante encargado de visualización.

## Parámetros de arranque

```powershell
uv run --extra ui --extra rl python scripts/ui.py --scenario scenarios/ruta_caliente.json --strategy dqn
uv run --extra ui python scripts/ui.py --strategy shortest
```

También acepta `--model` para otro checkpoint y `--seed` para la política aleatoria. Las estrategias de referencia funcionan sin el extra `rl`; si se selecciona DQN sin sus dependencias, la interfaz informa el problema.

## Verificación sin abrir ventanas

```powershell
uv run --extra ui --extra rl python scripts/ui.py --headless --steps 22 --screenshot outputs/ui-success.png
uv run --extra ui --extra rl python -m unittest discover -s tests -v
```

`--headless` usa el controlador de vídeo dummy de SDL, prepara la misma misión y guarda una captura con Pygame. No automatiza otras aplicaciones del equipo.

Se comprobaron pausa, avance manual, reinicio, repetición, cambios de escenario y estrategia, preparación en segundo plano, toggles, velocidad y finalización. También se verificó que cambiar la velocidad no cambia el daño ni el resultado.

La suite completa pasó 54 pruebas. Se revisaron visualmente capturas reales de Pygame al inicio, durante exposición térmica y tras completar el pasillo en 22 pasos. La captura compartida en el README se generó con el escenario caliente en el paso 5.
