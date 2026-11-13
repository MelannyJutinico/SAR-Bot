# Base V2: contratos para continuar el proyecto

## Alcance y estado

La base admite edificios de tamaño configurable y una cantidad positiva de sobrevivientes, manteniendo **dos robots con capacidad individual de una persona**. El hito integrado usa **10 × 10, tres personas, dos focos térmicos y pasos globales simultáneos**. El objetivo siguiente del equipo es diseñar y validar edificios de 12 × 12 con el mismo número de personas.

Se entregan motor, datos serializables, fábrica de estrategias, referencias con planes reutilizables, adaptación de Gymnasium, perfiles de modelo y representación básica de tres personas en Pygame. El editor, los conjuntos variados finales, las vistas de análisis y los experimentos amplios siguen siendo trabajo del equipo.

El modelo V1 de 6 × 6 se conserva. Un modelo no se vuelve compatible con otro tamaño o cantidad de personas por cambiar el archivo del mapa.

## 1. Escenario inmutable

```python
from sar_bot.core import Scenario

template = Scenario.load("scenarios/v2/building_10x10.json")
custom = template.with_victims([(1, 0), (0, 1), (1, 1)], name="mision_profesor")
assert template.victims != custom.victims
assert template.temperatures == custom.temperatures
```

Coordenadas internas `(x, y)`, origen arriba a la izquierda. En la interfaz, A1 corresponde a `(0, 0)`. Los identificadores de personas comienzan en cero; las etiquetas visibles comienzan en uno.

### Operaciones disponibles

| Operación | Contrato |
|---|---|
| `Scenario.load(path)` | Lee JSON histórico o V2 y valida estructura y conectividad |
| `Scenario.from_dict(data)` | Construye el mismo objeto desde un diccionario |
| `scenario.with_victims(positions, name=...)` | Crea otra configuración; conserva geometría y temperatura |
| `scenario.to_dict()` | Exporta JSON V2 con la matriz térmica exacta, focos y firma |
| `scenario.save(path)` | Guarda sin sobrescribir un archivo existente por defecto |
| `scenario.save(path, overwrite=True)` | Reemplazo solicitado explícitamente por el programa llamador |
| `scenario.fingerprint()` | Firma de dimensiones, base, paredes, temperaturas, posiciones y límite |
| `scenario.configuration_id` | Firma exacta para ejecutar y reproducir, distinguiendo el orden de las etiquetas |
| `scenario.victim_count` | Cantidad de personas configuradas |

`ValueError` indica datos inválidos; `FileNotFoundError` y `FileExistsError` conservan su significado en operaciones de archivos. Las posiciones deben ser enteros y no se aceptan booleanos como coordenadas. Se rechazan personas duplicadas, paredes, base, límites y desconexión.

La firma física ignora nombre y orden de etiquetas de personas para detectar duplicados entre particiones. No representa el estado de una misión en curso. Al importar un `scenario_id` almacenado se comprueba que coincida con el contenido; para editar utilizar `with_victims()` y volver a exportar, sin conservar una firma vieja.

Para invalidar episodios pendientes, usar **`configuration_id` junto con una generación de preparación**, no solo la firma física: intercambiar etiquetas mantiene el mismo caso físico, pero cambia el orden observado por DQN. Ambos identificadores se exportan y validan por separado.

**Validez estructural no garantiza rescate térmicamente viable.** La certificación con trayectoria testigo, los casos no certificados y sus mensajes siguen asignados a persona 2. No validar posiciones usando el éxito de DQN.

## 2. Varios focos de calor

Una plantilla nueva puede especificar:

```json
{
  "heat": {
    "ambient": 25,
    "combine": "max",
    "sources": [
      {"focus": [6, 3], "peak": 100, "falloff": 18},
      {"focus": [2, 7], "peak": 95, "falloff": 20}
    ]
  }
}
```

Ese fragmento pertenece a un escenario completo; no es un archivo de misión por sí solo. Se usa `T(x,y) = max(ambiente, pico_i − caída_i × distancia_Manhattan_i)` entre todos los focos. No se suman temperaturas. La matriz permanece fija durante el episodio y todavía no hay atenuación por paredes.

Los archivos antiguos con un solo `focus`, `peak` y `falloff` dentro de `heat` continúan funcionando. Un archivo exportado por `to_dict()` utiliza una matriz `temperatures` explícita para conservar exactamente el campo; sus `heat_sources` son metadatos de los focos. No se permite mezclar `heat` y `temperatures` en el mismo archivo.

## 3. Motor y estado público

```python
from sar_bot.core import RescueSimulation
from sar_bot.agents import create_policy

simulation = RescueSimulation(custom)
policy = create_policy(simulation, "thermal")
while simulation.state.outcome == "running":
    action = policy.act(simulation.state)
    simulation.step(action)
result = simulation.snapshot()
```

La acción sigue siendo un entero entre 0 y 24: `5 × acción_robot_1 + acción_robot_2`. Un paso aplica exposición a ambos robots. No dividirlo en dos llamadas, una por robot.

`MissionState` contiene dos robots, personas entregadas, número de pasos y resultado. La misión solo se completa al entregar todas las personas configuradas. Con tres personas es necesario que al menos un robot realice otro viaje. No hay recuperación de integridad al entregar.

`snapshot()` agrega `schema_version=2`, `scenario_id`, `victims_total` y una lista `victims` con identificador, posición y estado `pending`, `carried` o `rescued`. Mantiene los campos anteriores `steps`, `outcome`, `rescued` y `robots`.

No modificar estados para simular éxito. La interfaz dibuja los resultados del motor y los evaluadores leen sus métricas.

## 4. Contrato único de estrategias

`create_policy(simulation, strategy, model_path=None, seed=0, thermal_damage_weight=2.0)` recibe opciones adicionales como argumentos de palabra clave. Devuelve un objeto con `act(state) -> int`.

| Estrategia | Comportamiento |
|---|---|
| `shortest` | Asignación de personas disponibles y planificación conjunta por pasos |
| `thermal` | Asignación y planificación conjunta con costo de exposición |
| `random` | Acciones conjuntas uniformes con semilla local |
| `dqn` | Política cargada de `model_path`; requiere extra `rl` |

Crear una política por episodio. No compartir entre simulaciones su estado de asignaciones o caché. No sustituir una política que falla por otra sin informarlo.

Las referencias ahora usan A* conjunto con una cota inferior de distancias y conservan el plan mientras no cambien objetivos o posiciones previstas. El costo geométrico es un paso; el térmico añade exposición ponderada de ambos robots. Son planes óptimos para los objetivos actuales, no para todas las asignaciones futuras ni una certificación general de misión.

`replans` y `total_expanded` permiten estudiar costo de planificación. Los evaluadores exportan esos contadores y la cantidad total de víctimas. Al modificar la implementación del planificador, repetir comparaciones: las tablas históricas conservan el algoritmo y código con que se obtuvieron.

## 5. Preparación para la interfaz

```python
from sar_bot.ui.playback import prepare_episode, Playback

episode = prepare_episode(custom, "thermal")
assert episode.scenario_id == custom.fingerprint()
playback = Playback(episode, speed=3)
```

`prepare_episode` acepta un `Scenario`, una ruta de texto o `Path`. Al pasar un objeto editado no se requieren archivos temporales. Devuelve escenario, estados inmutables y acciones. La cantidad de estados es la de acciones más uno.

Persona 3 debe guardar `configuration_id` y descartar preparaciones anteriores al editar o cambiar de estrategia. La reproducción conserva su contrato de pausa, paso, reinicio y velocidad. `Episode.configuration_id` identifica la configuración exacta; `Episode.scenario_id` agrupa el caso físico para deduplicar datos.

Pygame ya dibuja tres tarjetas de personas y escala iconos para el mapa de 10 × 10. No hay editor ni selector automático de modelos por perfil: esos son módulos pendientes, no funciones construidas en esta base.

## 6. Perfil del aprendizaje

Dentro de un entorno Gymnasium deben coincidir ancho, alto y cantidad de personas entre escenarios. Pueden variar posiciones, obstáculos y temperatura, con sus datos y reglas correctamente registrados. No mezclar 10 × 10 y 12 × 12 dentro del mismo perfil sin diseñar otro esquema de observación.

| Perfil | Observación completa | Con sensores |
|---|---:|---:|
| V1: 6 × 6, dos personas | 97 | 157 |
| V2 inicial: 10 × 10, tres personas | 232 | 302 |
| Objetivo: 12 × 12, tres personas | 320 | 390 |

Fórmulas: completa `2WH + 11 + 7N`; sensores añade `40 + 10N`. El orden histórico se mantiene para N=2. Los estados de carga crecen a N+1 posibilidades por robot y las distancias de los sensores incluyen base y cada persona.

Para probar posiciones editadas sin alterar la plantilla:

```python
from sar_bot.env import RescueEnv

env = RescueEnv([template], observation_mode="sensors")
observation, info = env.reset(seed=7, options={
    "scenario_index": 0,
    "victim_positions": [(1, 0), (0, 1), (1, 1)]
})
```

El conteo debe coincidir con el perfil. `env.profile` describe dimensiones, personas, modo y espacio de observación. El entrenador guarda ese perfil en metadatos y en el modelo. La carga comprueba el perfil cuando está disponible; los checkpoints V1 históricos se reconocen por su esquema anterior.

La guía de distancia ahora evita enumerar factorialmente órdenes de rescate. Como cada robot debe volver a base después de cargar una persona, basta considerar las primeras asignaciones y los viajes posteriores desde base. Se mantiene el cálculo anterior para los casos V1.

### Guía acotada para mapas grandes

`RewardConfig.potential_bound` vale cero por defecto y conserva la escala histórica. El piloto V2 utiliza 40. Una escala fija por edificio acota el potencial sin cambiarlo arbitrariamente entre pasos. Con shaping=2, gamma=0.99 y paso=−1, esperar sin eventos en una celda segura no produce recompensa positiva por la guía.

El primer diagnóstico sin esa cota podía acumular retorno positivo sin entregar personas en el edificio grande. Se corrigió y se conserva la necesidad de medir rescates reales, no solo retorno. El ajuste no sustituye el trabajo posterior sobre currículo, ubicaciones variadas y riesgo térmico.

## 7. Comandos V2

```powershell
# Demostración completa con referencia térmica.
uv run --extra ui --extra rl python scripts/ui.py --scenario scenarios/v2/building_10x10.json --strategy thermal

# Comparación de las referencias en el edificio grande.
uv run --no-project --python 3.12 scripts/evaluate.py --scenarios scenarios/v2/building_10x10.json --output outputs/v2_reference.csv

# Entrenamiento piloto reproducible. Elegir un directorio nuevo para cada ejecución.
uv run --extra rl python scripts/train.py --config configs/dqn_v2_pilot.json --run-dir outputs/mi-piloto-v2 --seed 0
```

Las referencias ya completaron tres rescates: geométrica en 58 pasos con 107 puntos de daño total; térmica en 62 con 64. El daño total suma dos robots y puede superar 100 sin que uno se destruya.

El piloto de aprendizaje es una comprobación de integración. Se ejecutaron 90000 pasos con la guía acotada y se seleccionó el checkpoint de 65000. Recargado desde archivo, rescata a las tres personas cercanas en seis pasos y sin daño, pero entrega cero personas en el edificio grande antes del límite de 240 pasos. Ambos casos participaron en entrenamiento y selección; no hay prueba reservada V2.

El modelo y la evidencia están en `artifacts/v2_pilot/`. No se considera un modelo final entrenado para ubicaciones arbitrarias ni una validación del edificio grande. El primer diagnóstico sin cota se conserva en `outputs/dqn-v2-pilot/` localmente; el experimento acotado en `outputs/dqn-v2-bounded/`. Sus configuraciones y escalas son distintas, por lo que no deben compararse retornos como si fueran idénticos.

## 8. Entrega por módulo

| Responsable | Base disponible | Trabajo que debe continuar |
|---|---|---|
| Persona 1 | Motor generalizado, perfiles, entrenamiento, fábrica y episodios | Currículo, estabilidad, modelos por perfil e integración |
| Persona 2 | `Scenario`, focos, firmas, cambio de personas y serialización | Edificios 12 × 12, calibración térmica, certificación y generación variada |
| Persona 3 | Reproducción visual V2 y entrada `Scenario` | Editor de tres personas, preparación/ejecución/análisis, registro de modelos y comparación |
| Persona 4 | Evaluación común, firmas y métricas | Particiones nuevas, experimentos, trazas, gráficas y defensa académica |

Cambiar estos contratos requiere revisión de los módulos consumidores. Ampliar edificios y personas exige nuevos datos y entrenamiento; no cambia automáticamente la capacidad de un checkpoint ya guardado.

## 9. Verificación de la base

La comprobación completa pasó 72 pruebas, conservando las reglas V1 y verificando tres rescates, varios focos, guardado/carga, firmas, perfiles 10 × 10 y 12 × 12, modelos serializados y controles visuales. Se volvió a cargar el checkpoint V1 y conservó el resultado del pasillo: dos rescates en 22 pasos y daño cero.

La interfaz V2 se renderizó y revisó con una misión real. La captura en `docs/images/ui-v2.png` muestra la referencia térmica durante el paso 25; no es una predicción del piloto DQN.
