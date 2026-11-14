# SAR-Bot — guía para incorporarse al equipo

**Asignatura:** Sistemas Inteligentes · **Equipo:** cuatro personas · **Actualización:** 13 de noviembre de 2026.

Este documento permite continuar el proyecto sin haber participado en las conversaciones iniciales. Explica el propósito, la base entregada, las limitaciones y cómo repartir el trabajo. Las tareas ejecutables y sus criterios de aceptación están en [BACKLOG.md](BACKLOG.md).

## 1. Qué queremos presentar

Una aplicación de rescate en un edificio 2D donde **dos robots controlados por una política aprendida** recogen a tres sobrevivientes y los llevan a una base, considerando obstáculos, coordinación y exposición al calor. La ampliación V2 comienza con un hito de 10 × 10 y tiene como objetivo edificios de 12 × 12.

La ampliación principal será que **el profesor pueda colocar a las tres personas con clics antes de iniciar la misión**, dentro de un edificio preparado por el equipo. Luego podrá observar el rescate y comparar DQN con estrategias programadas, manteniendo exactamente el mismo escenario. Como cada robot carga una persona, hacen falta viajes adicionales y decisiones sobre el reparto del trabajo.

La pregunta del trabajo es: **¿qué tan bien responde un controlador aprendido a distintas ubicaciones de sobrevivientes y cómo equilibra rescates, pasos y daño térmico frente a referencias clásicas?**

El objetivo académico es formular un problema secuencial, entrenar una política, mostrar sus decisiones y evaluarlas con datos. No se exige que una red supere a un planificador en todos los mapas para poder realizar un análisis válido.

## 2. Qué sabemos de las expectativas del profesor

Según la propuesta original, el profesor mostró interés en agentes que envían acciones a un entorno simulado y realizan una tarea observable. La propuesta no contiene una rúbrica formal. DQN, dos robots, Pygame y el editor son decisiones del equipo; debemos validar el alcance y los entregables con el profesor, sin atribuirle requisitos que no haya confirmado.

La simulación es académica. Las temperaturas y daños son reglas de juego, no una predicción física de un incendio ni una validación de seguridad robótica.

## 3. Estado real al recibir la base

| Componente | Estado |
|---|---|
| Motor 2D con dos robots, paredes y rescates | Implementado |
| Base V2 de 10 × 10, tres personas y varios focos | Implementada; referencias completan la misión |
| Contratos para escenarios editados, firmas y serialización | Disponibles en `docs/CONTRATOS_V2.md` |
| Temperatura y exposición acumulada por paso global | Implementadas |
| Referencias aleatoria, geométrica y térmica | Implementadas |
| Gymnasium, recompensas, entrenamiento y checkpoints DQN | Implementados |
| Modelo con sensores V1 guardado y cargable | Disponible para 6 × 6 y dos personas |
| Modelo V2 | Piloto de integración; aún no resuelve el edificio grande |
| Interfaz Pygame con controles, calor, rutas e indicadores | Implementada como primera versión |
| Pruebas de motor, aprendizaje, reproducción y controles | Ampliadas para V2; conservar la suite completa al integrar |
| Editor para colocar sobrevivientes con clics | Pendiente |
| Entrenamiento con muchas combinaciones de ubicaciones | Pendiente |
| Aprendizaje continuo con memoria y modelo persistentes entre ejecuciones | Solicitado; pendiente en SARB-033 a SARB-035 |
| Certificación general de viabilidad térmica de posiciones nuevas | Pendiente |
| Selección final sobre validación y evaluación con varias semillas | Pendientes |
| Gráficas finales, informe, presentación y versión de entrega | Pendientes |

**Base publicada:** el 13 de noviembre de 2026 se subieron los commits de la base V2 a `feature/simulation-core` y se verificó la rama en GitHub. Usar esa rama para obtener motor, interfaz y modelos; no asumir que `main` contiene la misma versión. SARB-001 conserva la revisión del equipo y SARB-003 la comprobación de instalación en los otros computadores.

## 4. Qué demuestran los modelos disponibles

El modelo V1 está en `artifacts/sensors_dqn/model.zip`. Se entrenó desde cero con una semilla, durante 155000 pasos; se seleccionó el checkpoint de 60000 mediante controles de desarrollo. Los siguientes datos son históricos de 6 × 6 y dos personas, no resultados del nuevo alcance:

- Completa los seis escenarios de control actuales.
- Completó dos configuraciones de validación y dos de prueba que se consultaron después de fijar ese checkpoint.
- En el pasillo compartido entrega ambas víctimas en 22 pasos y sin daño; la referencia geométrica necesita 20 pasos.
- En el escenario más caliente recibe 74 puntos de daño, igual que la ruta corta. La referencia térmica recibe 34 y tarda 35 pasos.

Estos resultados son un punto de partida, no una garantía para cualquier ubicación que el profesor elija. No demuestran superioridad térmica ni generalización amplia. Tampoco constituyen tres semillas de una misma configuración: existen tres experimentos distintos, cada uno con semilla 0.

Los casos de prueba actuales ya se han observado. Para el nuevo desarrollo deben considerarse antecedentes de desarrollo y reservarse configuraciones nuevas para una prueba final. Conservaremos sus archivos y resultados históricos.

En V2, la ruta corta entrega tres personas en 58 pasos con daño total 107 y la térmica en 62 con daño 64. El total suma los dos robots. El piloto DQN aprende el escenario cercano, pero no domina ese edificio. Se necesita ampliar el currículo y la variedad; no basta con cargar el checkpoint V1 en el nuevo mapa.

## 5. Reglas que todos debemos comprender

| Regla | Definición |
|---|---|
| Edificio | Hito integrado de 10 × 10; objetivo de entrega 12 × 12, según validación del alcance |
| Robots y personas | Dos robots, tres personas; una persona por robot |
| Inicio | Ambos robots parten de una base compartida y segura |
| Recogida y entrega | Automáticas al alcanzar la persona o la base |
| Información del controlador | Mapa y posiciones conocidos, integridad, carga, estado de víctimas y sensores |
| Decisión | Una política centralizada elige una acción conjunta para ambos robots |
| Acciones individuales | Arriba, abajo, izquierda, derecha o esperar |
| Acciones conjuntas | 25 combinaciones; `5 × acción_robot_1 + acción_robot_2` |
| Colisiones | Sin coincidencia fuera de la base ni intercambio directo de posiciones |
| Calor | Campo fijo durante el episodio; no hay propagación de fuego |
| Integridad | Empieza en 100 por robot; no se recupera |
| Éxito | Todas las personas entregadas y ambos robots operativos |
| Fracaso | Destrucción de cualquiera de los robots |
| Límite | Máximo de pasos del escenario; se distingue de la destrucción |

En cada paso global se resuelven ambos movimientos, se aplica daño a ambos robots y se procesan los rescates. Una destrucción tiene prioridad sobre una posible entrega. Las reglas completas están en [CONTEXTO.md](docs/CONTEXTO.md).

### Exposición térmica

| Temperatura T | Daño por paso y robot expuesto |
|---|---:|
| T < 40 °C | 0 |
| 40 ≤ T < 60 °C | 2 |
| 60 ≤ T < 80 °C | 5 |
| T ≥ 80 °C | 10 |

Esperar o intentar atravesar un obstáculo también consume un paso. Cuatro pasos a 65 °C producen 20 puntos de daño. Cambiar la velocidad de la interfaz no cambia el resultado ni la exposición.

**Hay dos robots y una política centralizada.** No presentaremos el sistema como dos políticas independientes ni como búsqueda a ciegas. Las distancias de camino de los sensores se calculan usando el mapa conocido; no son una trayectoria experta suministrada al agente.

## 6. Alcance de la versión que vamos a terminar

1. Elegir edificios preparados, partiendo de 10 × 10 y avanzando al objetivo de 12 × 12.
2. Colocar exactamente tres personas en celdas válidas antes de iniciar.
3. Informar errores estructurales y el resultado de comprobar viabilidad térmica.
4. Ejecutar el controlador aprendido y las tres referencias en el mismo escenario.
5. Mostrar rescates, integridad, temperatura, daño, pasos, trayectorias y motivo de finalización.
6. Guardar el escenario y sus resultados para poder repetir la comparación.
7. Presentar un entrenamiento con ubicaciones variables y una evaluación final reproducible.
8. Ofrecer un modo de aprendizaje continuo: cada misión nueva aporta experiencia y conserva modelo y memoria para la siguiente ejecución. Mantener un modo de evaluación con modelo congelado para comparaciones.

El aprendizaje continuo todavía no está implementado. SARB-033 a SARB-035 detallan persistencia, integración visual y medición; reproducir una misión ya calculada no cuenta como continuar aprendiendo. La actualización corresponde al controlador compartido de ambos robots, no a dos redes independientes, y no garantiza mejorar después de cada misión.

Inicialmente el editor no cambia paredes, base, incendio ni cantidad de robots o personas. Las ediciones ocurren antes de preparar la misión: cambiar una ubicación invalida la reproducción anterior.

El motor ya permite configurar el número de personas, pero cada entorno y modelo tienen un perfil fijo de dimensiones y cantidad. No mezclar mapas 10 × 10 y 12 × 12 dentro del mismo modelo actual. La versión 6 × 6 se usa como regresión e historia de desarrollo.

El validador no debe rechazar ubicaciones porque DQN falle en ellas. Una referencia que encuentra un rescate completo demuestra viabilidad; una referencia que falla no demuestra imposibilidad. Si no se logra certificar un caso dentro del presupuesto de búsqueda, se mostrará como no certificado y podrá explorarse con esa advertencia. Un error estructural sí impide iniciar.

### Fuera del alcance de esta entrega

Batería, plazos de supervivencia, fuego dinámico, visión artificial, varios pisos, más robots, física 3D, aplicación web y edición completa del edificio. Son posibles extensiones; no son requisitos del backlog de entrega. El aprendizaje continuo sí se incorporó al alcance por decisión del equipo.

## 7. Instalar y ejecutar la base

La configuración comprobada usa Windows y Python 3.12. El proyecto declara Python 3.11 o superior, pero la comprobación documentada se hizo con 3.12. Se necesita Git y `uv`; la primera instalación requiere red para las dependencias. PyTorch se instala en su variante CPU.

Si falta `uv`, seguir su [guía oficial de instalación](https://docs.astral.sh/uv/getting-started/installation/). Después de instalarlo, abrir una terminal nueva y comprobar `uv --version`.

Para obtener la base publicada:

```powershell
git clone https://github.com/MelannyJutinico/SAR-Bot.git
cd SAR-Bot
git switch feature/simulation-core
uv sync --locked --extra ui --extra rl --python 3.12
uv run --locked --extra ui --extra rl python scripts/ui.py --scenario scenarios/v2/building_10x10.json --strategy thermal
```

Si ya tienen un clon, revisar `git status` y conservar sus cambios antes de cambiar de rama o actualizar. No ejecutar operaciones para descartar trabajo propio. La persona 1 comunicará la rama estable o etiqueta definitiva cuando exista.

### Primera comprobación de cada integrante

1. Abrir V2 con la referencia térmica y comprobar tres rescates, 62 pasos y daño total 64.
2. Comparar con ruta corta en el mismo edificio: tres rescates, 58 pasos y daño total 107.
3. Ejecutar también la versión V1, seleccionando el pasillo compartido y DQN con su modelo 6 × 6: dos rescates, 22 pasos y daño cero.
4. Leer los contratos V2 antes de crear el editor o nuevos conjuntos de posiciones.
5. Ejecutar las pruebas y compartir resultado, versión de Python y commit utilizado.

```powershell
uv run --locked --extra ui --extra rl python -m unittest discover -s tests -v
```

No hay que volver a entrenar para abrir la interfaz. Tampoco hay que activar manualmente el entorno virtual al usar estos comandos de `uv`.

### Comandos técnicos disponibles hoy

```powershell
# Comparación histórica V1 sobre su conjunto de desarrollo.
uv run --extra rl python scripts/evaluate_dqn.py --model artifacts/sensors_dqn/model.zip --split training --output outputs/comparison.csv

# Entrenamiento piloto V2 en un directorio nuevo.
uv run --extra rl python scripts/train.py --config configs/dqn_v2_pilot.json --run-dir outputs/experimento-equipo-01 --seed 0

# Captura sin abrir una ventana.
uv run --extra ui --extra rl python scripts/ui.py --headless --steps 22 --screenshot outputs/ui-success.png
```

El entrenador recibe la semilla desde el JSON y permite sobrescribirla con `--seed`. Para el piloto V2 usar `configs/dqn_v2_pilot.json` y un directorio nuevo. La API de reinicio ya admite posiciones personalizadas, pero los conjuntos variados finales, selección sobre validación y evaluación de varias semillas siguen en el backlog.

### Si algo no abre

| Síntoma | Qué revisar |
|---|---|
| No existe `scripts/ui.py` o el modelo | Rama incorrecta o base todavía sin publicar |
| `uv` no se reconoce | Instalación y terminal nueva |
| Falta Pygame o una dependencia de DQN | Sincronizar con los extras `ui` y `rl` |
| Cambió el esquema de observaciones | Modelo y entorno deben ser compatibles; no modificar dimensiones sin versionar |
| Falló un entrenamiento porque el directorio no está vacío | Usar un directorio nuevo; conservar el experimento anterior |
| La misión termina sin rescatar | Distinguir fallo de la política de error de software; guardar escenario y traza |

## 8. Dónde trabajar

| Ruta actual | Función | Responsable principal sugerido |
|---|---|---|
| `src/sar_bot/core/simulation.py` | Estado y reglas del motor | Persona 2, revisión de persona 1 |
| `src/sar_bot/env/rescue_env.py` | Observaciones y recompensas | Persona 1 |
| `src/sar_bot/agents/` | DQN y referencias | Personas 1 y 4 |
| `docs/CONTRATOS_V2.md` | Contratos entre escenarios, políticas, episodios y perfiles | Todos |
| `src/sar_bot/training.py`, `scripts/train.py` | Entrenamiento y exploración | Persona 1 |
| `src/sar_bot/ui/app.py` | Presentación y controles | Persona 3 |
| `src/sar_bot/ui/playback.py` | Preparación del episodio y reproducción | Persona 3, revisión de persona 1 |
| `scripts/evaluate_dqn.py`, `src/sar_bot/evaluation.py` | Comparaciones y métricas | Persona 4 |
| `scenarios/`, `configs/` | Edificios, configuraciones y particiones | Personas 2 y 4 |
| `tests/` | Verificación de reglas e integración | Cada autor sobre su cambio |
| `artifacts/` | Checkpoints y evidencia seleccionada | Personas 1 y 4 |
| `docs/` | Diseño, resultados e instrucciones | Todo el equipo, coordinación de persona 4 |

La interfaz prepara un episodio en segundo plano y reproduce sus estados. El motor es la única fuente de reglas: no calcular daño ni resolver colisiones otra vez en Pygame. El editor deberá enviar una configuración al motor y reiniciar la preparación, no modificar imágenes de una misión ya calculada.

## 9. Reparto de trabajo desde ahora

| Integrante | Responsabilidad de cierre |
|---|---|
| Persona 1: responsable de la base | Integración, contrato de escenarios, entrenamiento dinámico, modelos y revisión técnica |
| Persona 2 | Validadores, viabilidad, escenarios, generación de ubicaciones y serialización |
| Persona 3 | Editor visual, interacción, comparación en pantalla y claridad de la demostración |
| Persona 4 | Particiones, protocolo experimental, ejecuciones, gráficas, informe y presentación |

La persona 1 puede asumir mayor complejidad técnica; las otras tres tienen entregables técnicos propios. Todos deben comprender el aprendizaje y poder explicar el proyecto. El [backlog](BACKLOG.md) indica dependencias y quién revisa cada tarea.

## 10. Cómo colaborar sin romper la base

- Usar ramas `feature/editor-personas`, `feature/validacion-escenarios`, `feature/evaluacion-final` o equivalentes sobre la base estable comunicada.
- Una persona es autora principal de cada tarea. Coordinar antes de editar el mismo módulo.
- Hacer commits pequeños y descriptivos. Al cerrar una tarea, compartir commit o PR, evidencia y limitaciones.
- Integrar cambios diariamente sobre una versión que arranque; no acumular cuatro implementaciones aisladas hasta el último día.
- Conservar modelos y datos históricos. No sobrescribir un experimento ni cambiar una función de recompensa sin registrar su configuración.
- Usar la semilla y configuración guardadas para reproducir fallos. Los pasos simulados no son el tiempo de cómputo ni la velocidad visual.
- No subir `.venv/`, cachés, credenciales ni todas las ejecuciones de `outputs/`. Publicar artefactos seleccionados con metadatos y resultados.
- Reservar los casos de prueba final y fijar el modelo antes de abrir sus resultados. Si esos resultados se usan para entrenar o ajustar, reservar otros casos nuevos.

## 11. Cómo se verá una buena entrega

El profesor podrá elegir un edificio, ubicar personas, ejecutar el rescate y comparar estrategias. El equipo mostrará resultados de configuraciones reservadas, explicará una decisión entre distancia y calor y analizará al menos un fallo real.

La entrega contendrá código reproducible, interfaz, modelo guardado, escenarios exportados, resultados y gráficas medidos, informe técnico, presentación y un respaldo de la demostración. Las mejoras que no se logren se reportarán como límites; no se ocultarán casos ni se inventarán métricas.

**Comenzar por SARB-001 a SARB-004.** Después, personas 2 y 3 pueden construir validación y editor en paralelo, persona 1 adaptar el aprendizaje y persona 4 fijar el protocolo experimental. Cerrar todo el backlog P0 y P1 define la meta de entrega del equipo, no una garantía de calificación del profesor.

## 12. Lectura de apoyo

- [Backlog de entrega](BACKLOG.md): fuente principal para tareas pendientes.
- [README técnico](README.md): comandos y mapa del repositorio.
- [Contexto y reglas](docs/CONTEXTO.md).
- [Contratos V2](docs/CONTRATOS_V2.md).
- [Aprendizaje y experimentos](docs/APRENDIZAJE.md).
- [Resultados y límites medidos](docs/EVALUACION.md).
- [Interfaz actual](docs/INTERFAZ.md).
- [Plan y responsabilidades](docs/PLAN_DE_TRABAJO.md).
