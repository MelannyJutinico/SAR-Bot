# Edificios, calor y generación V2

Este documento describe datos de desarrollo de Persona 2. No son particiones finales de entrenamiento, validación o prueba y no se agregan a `configs/scenario_splits.json`.

## Plantillas 12 × 12

### Centro de coordinación

`scenarios/v2/coordination_hub_12x12.json` divide el edificio mediante dos barreras que forman cuatro sectores, con tres puertas por barrera. La base está en el sector superior izquierdo y las tres personas de ejemplo exigente ocupan los otros sectores. Los dos robots comparten cruces y uno debe realizar un segundo viaje. Las rutas alternativas permiten apartarse o usar otra puerta cuando coinciden.

### Desvío térmico

`scenarios/v2/thermal_detour_12x12.json` usa dos separaciones verticales con puertas superiores, centrales e inferiores. Las puertas centrales forman el camino geométrico corto; dos focos convierten ese eje en una ruta de exposición alta. Las puertas de los extremos permiten rodeos más largos y seguros.

## Familias de dificultad

Los ejemplos reproducibles están en `configs/v2_scenario_families.json`.

- `easy`: distancia Manhattan media normalizada hasta 0,20 y como máximo una persona inicialmente en celda de daño. Son rescates cercanos y de baja exposición.
- `intermediate`: caso que no alcanza los extremos anteriores; introduce más distancia, puertas o sectores sin combinar todavía todos los factores.
- `demanding`: distancia media normalizada desde 0,50, o desde 0,35 con al menos dos personas en celdas de daño. Favorece segundos viajes largos y exposición relevante.

La etiqueta describe propiedades de la configuración, no predice el rendimiento de DQN. Cada ejemplo del manifiesto se valida con `Scenario` y tiene certificado positivo de `certify_viability()`.

## Calibración térmica

| Edificio | Ambiente | Foco 1 | Foco 2 | Combinación |
|---|---:|---|---|---|
| Centro de coordinación | 25 | `(7,3)`, pico 88, caída 16 | `(8,9)`, pico 86, caída 15 | máximo |
| Desvío térmico | 25 | `(6,6)`, pico 90, caída 18 | `(9,6)`, pico 86, caída 18 | máximo |

La temperatura es estática y usa distancia Manhattan. Las paredes no atenúan calor. Se conservan exactamente los umbrales 40/60/80 y la base permanece a 25. Estos valores son una abstracción académica para estudiar decisiones secuenciales, no CFD, propagación de incendios ni una predicción de seguridad.

En las configuraciones medidas, la referencia geométrica elige pasos centrales más cortos y recibe más daño; la referencia térmica utiliza rodeos. La medición incluye recogidas, regresos y el viaje adicional requerido por la tercera persona.

## Generación reproducible

`generate_configurations()` recibe plantilla, semilla, cantidad, máximo de intentos, familias y presupuesto opcional de certificación. Solo cambia las tres posiciones mediante `Scenario.with_victims()`; conserva dimensiones, base, paredes, matriz térmica, focos, ambiente y límite.

La semilla controla un `random.Random` local. Los candidatos se clasifican con distancia Manhattan normalizada y cantidad de celdas de daño. `scenario_id` elimina casos físicos repetidos aunque cambie el orden de etiquetas; `configuration_id` conserva el orden exacto. Los casos certificados se aceptan, los `not_certified` se devuelven por separado y el procedimiento siempre termina por cantidad o máximo de intentos.

El filtro positivo favorece necesariamente a las referencias `thermal` y `shortest` usadas por el certificador. Por tanto, estos casos no sirven para afirmar eficacia universal de esas referencias. SARB-009 deberá construir y congelar particiones nuevas sin reutilizar automáticamente estos ejemplos de desarrollo.
