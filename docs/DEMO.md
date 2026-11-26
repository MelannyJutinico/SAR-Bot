# Guion de demostración de SAR-Bot

El inicio vigente usa **el agente neuronal de asignación y riesgo**, no el DQN antiguo de movimientos. Se trabaja en el mismo proyecto y en `main`; no hay una nueva etiqueta de versión.

## Preparar

1. Cerrar la ventana anterior y abrir `run.bat` desde la raíz actualizada.
2. Comprobar que diga **Red neuronal de rescate**. El mapa inicial es Centro de coordinación.
3. Empezar en **Solo ejecutar** para usar la red congelada y reproducir las cifras conocidas.
4. Tener abiertos el [informe](INFORME.md), las [tablas verificadas](../results/assignment/report.md) y esta guía.

## Guion de 5–8 minutos

| Paso | Qué mostrar y explicar |
|---|---|
| Problema | Dos robots, tres personas, una carga por robot y daño acumulado según temperatura y tiempo. |
| Qué aprende | Una red 16–64–32–1 puntúa repartos y riesgo. Dijkstra prepara atributos y A* calcula caminos. La red se entrena con ejemplos de un estimador experto. |
| Misión principal | Pulsar Ver misión y controles e iniciar. El caso inicial rescata 3/3 en **62 pasos**, daño total **42**. Señalar los objetivos de los robots, cargas y entregas. |
| Posiciones nuevas | Volver a preparación, colocar las tres personas, validar y preparar una misión nueva. No prometer que cualquier posición sea rescatable. |
| Aprender | Activar Aprender, completar una misión y esperar el guardado. Mostrar experiencias y actualizaciones; cerrar y abrir otra ejecución, activar Aprender y recuperar los contadores. |
| Comparar | Comparar las cuatro estrategias sobre el mismo caso; mirar entregas y finalización antes que pasos y daño. Ver recorrido reproduce cada fila y no entrena. |
| Evidencia | Nueva prueba: **40/40**, 120/120 personas. Frente a la misma red sin entrenar: 41,20 frente a 43,625 pasos y 13,825 frente a 15,625 de daño. Explicar el papel común del planificador. |

## Cómo explicar la red

La red no memoriza una secuencia de movimientos del mapa. Recibe dieciséis atributos por alternativa: distancias, exposición prevista, carga, integridad y trabajo pendiente. Produce un coste; se elige el reparto y régimen con menor predicción. Hay como máximo doce alternativas al principio de una misión de tres personas.

El entrenamiento es **supervisado**, con etiquetas de un estimador de coste programado. No llamarlo DQN ni aprendizaje por refuerzo. El DQN anterior se conserva como experimento fallido: se quedaba dando vueltas y no generalizó. Se replanteó qué debía aprender el modelo.

El planificador aporta gran parte de la capacidad de rescate. Por eso se comparó la red entrenada con su propia inicialización y con otras cinco inicializaciones sin entrenar, usando siempre el mismo planificador. La mejora de aprendizaje se mide en las decisiones y sus costes; no se atribuye todo el funcionamiento a la red.

En 2400 preguntas sintéticas nuevas, la entrenada eligió un coste experto mínimo en 99,625 %; su inicialización obtuvo 37,375 %. Esa cifra mide coincidencia con el criterio experto, no tasa de éxito de rescate ni optimalidad global.

## Aprendizaje persistente

Cada misión nueva terminada aporta estados observados y ejemplos de alternativas con etiquetas expertas. Se entrena una copia candidata con memoria de ensayo. Antes de promover sus pesos, se compara contra los anteriores en controles de entrenamiento. Si empeora, se conserva la red anterior y se guardan las experiencias.

Se comprobaron dos procesos independientes: 3/3 personas en 12 y 16 pasos, dos misiones, 28 pasos observados, 40 ejemplos y 128 actualizaciones aceptadas. Los parámetros cambiaron y el resultado de controles se mantuvo. No afirmar que cada misión mejora el rendimiento. Al reiniciar se debe elegir Aprender para recuperar la sesión; Solo ejecutar usa la red base.

Las posiciones reservadas no se usan para aprender. Las comparaciones usan la base congelada y no promueven una sesión adaptada automáticamente.

## Comandos y respaldo

```powershell
.\run.bat
.\run.bat --learn --scenario scenarios/partitions/v2_12x12/training/hub_training_01_easy.json
uv run --locked python scripts/report_assignment.py --check
```

La primera misión conocida es un ejemplo de desarrollo, no una posición reservada elegida después de prueba. Las cuarenta ubicaciones nuevas se evaluaron tras congelar el modelo. Si falla una posición en vivo, mostrar el fallo y compararlo con las referencias; no sustituirlo por un recorrido programado atribuido a la red.

Respaldo visual: [rescate real del agente actual](images/neural-rescue.png). Las tablas conservan acciones reproducibles. No hace falta entrenar desde cero ni repetir la prueba durante la exposición.
