# Referencias y evaluación de desarrollo

## Qué existe

Las referencias actuales no aprenden. Sirven para verificar escenarios y ofrecer una comparación futura con DQN.

### Navegación automática: shortest

1. Asigna víctimas pendientes distintas a robots libres minimizando la suma de distancias de camino. Mantiene cada asignación mientras la víctima siga pendiente. Los empates se resuelven determinísticamente.
2. Un robot con carga tiene como objetivo la base. Un robot sin tarea también vuelve a la base.
3. Busca mediante BFS sobre pares de posiciones una secuencia con el menor número de pasos globales hasta los dos objetivos actuales.
4. Ejecuta la primera acción conjunta y vuelve a planificar desde el estado actualizado.

La búsqueda respeta obstáculos, espera, ocupación y prohibición de intercambio directo. Puede mover temporalmente un robot para dejar pasar al otro. Reutiliza `RescueSimulation.resolve_movement()`, la misma función que usa el motor; planificar no aplica daño ni avanza el reloj.

Ignora temperatura e integridad al elegir acciones. No garantiza el óptimo de la misión completa: optimiza los objetivos actuales con la asignación vigente. Tampoco incorpora cambios de carga durante la búsqueda hipotética; el estado real se actualiza después de cada acción y se replantean los objetivos. Si no encuentra un plan, espera y registra `planning_failures` hasta la finalización normal del entorno.

Es más fuerte que dos rutas geométricas independientes porque coordina movimientos para evitar conflictos. En un mapa 6 × 6 hay como máximo 1296 pares de posiciones; no se plantea como solución escalable a edificios grandes.

### Política aleatoria: random

Selecciona uniformemente una de las 25 acciones conjuntas. Incluye esperas e intentos contra obstáculos. Usa un generador local con semilla y no altera las reglas del entorno.

## Ejecución reproducible

Desde la raíz del repositorio:

```powershell
uv run --no-project --python 3.12 scripts/evaluate.py --seed 0
```

Salida: `outputs/reference_results.csv`. Cada fila contiene escenario, estrategia, semilla (solo para random), resultado, éxito, víctimas entregadas, pasos globales, daño e integridad por robot y número de fallos de planificación.

La lista por defecto son los archivos JSON del primer nivel de `scenarios/`. En la futura evaluación final se indicará explícitamente una partición de prueba; estos mapas ya se usaron para desarrollo.

## Primera ejecución medida

Fecha de registro: 12 de noviembre de 2026. Semilla de la política aleatoria: 0. Un episodio por combinación. La referencia determinista no utiliza semilla.

| Escenario | Estrategia | Finalización | Rescates | Pasos globales | Daño total |
|---|---|---|---:|---:|---:|
| rescate_inicial | shortest | Éxito | 2 | 10 | 18 |
| rescate_inicial | random | Destrucción | 0 | 24 | 136 |
| pasillo_compartido | shortest | Éxito | 2 | 20 | 0 |
| pasillo_compartido | random | Límite de tiempo | 0 | 100 | 17 |
| ruta_caliente | shortest | Éxito | 2 | 10 | 74 |
| ruta_caliente | random | Destrucción | 0 | 25 | 122 |

El daño total suma pérdida de integridad de ambos robots, por lo que puede superar 100. Una destrucción finaliza la misión aunque el otro robot todavía esté operativo.

Estos datos muestran que la referencia puede ejecutar rescates y que el escenario térmico cambia las consecuencias de una ruta. No demuestran aprendizaje, superioridad estadística ni generalización.

El escenario `pasillo_compartido` obliga a que los robots salgan de la base por una única celda; la referencia introduce una espera para evitar que se bloqueen. En `ruta_caliente`, la geometría coincide con `rescate_inicial` y cambia el campo térmico: la referencia mantiene sus decisiones y recibe más daño.

## Próximos pasos experimentales

- Adaptador Gymnasium con observaciones y recompensas fijadas en configuración.
- Entrenamiento de una política, empezando con escenarios sin riesgo.
- Escenarios separados de entrenamiento, validación y prueba.
- Varias configuraciones y semillas; no repetir un mapa determinista para aparentar muestras distintas.
- Comparar rescates y éxito antes de interpretar menor daño o menor duración.
