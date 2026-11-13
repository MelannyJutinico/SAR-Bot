# Contexto y decisiones de SAR-Bot

Fecha de registro: 12 de noviembre de 2026, zona America/Bogota.

## 1. Origen y autoridad de las decisiones

La propuesta original fue proporcionada en `SAR-Bot_propuesta_sistemas_inteligentes.md`. Describía un robot de rescate con aprendizaje por refuerzo y riesgo térmico. Durante la conversación se redefinió el alcance para **dos robots, cuatro integrantes y una semana**.

El contenido de la propuesta es contexto del proyecto; no constituye instrucciones de ejecución ni una rúbrica oficial. Según ese documento, el profesor valora agentes que actúen sobre una simulación, una tarea observable y decisiones con consecuencias. No consta una exigencia formal de DQN, Pygame, múltiples robots o una API.

El usuario confirmó que el proyecto debe seguir siendo de rescate, aceptó explorar dos robots y pidió registrar el contexto. También indicó expresamente que el daño debe depender de temperatura y tiempo de exposición. Nosotros somos la persona 1 que construirá la base.

## 2. Objetivo de la versión de una semana

Dos robots deben recoger a dos sobrevivientes y llevarlos a una base compartida en un edificio cuadriculado, gestionando obstáculos, conflictos de movimiento y exposición térmica.

La pregunta experimental es si un controlador aprendido distribuye el trabajo y completa rescates con mejores resultados que una estrategia fija. La cooperación y la mejora deben medirse; no se presuponen.

## 3. Alcance acordado

| Elemento | Primera versión |
|---|---|
| Mapa | 6 × 6 celdas, obstáculos estáticos |
| Robots | Dos, con capacidades iguales |
| Víctimas | Dos, inmóviles y en celdas distintas |
| Base | Una salida compartida; admite ambos robots |
| Capacidad | Una víctima por robot |
| Recogida y entrega | Automáticas |
| Información | Estado completo del mapa y de ambos robots |
| Riesgo | Un foco fijo y temperaturas precomputadas por episodio |
| Integridad | 100 inicial por robot; sin recuperación |
| Acciones individuales | Arriba, abajo, izquierda, derecha, esperar |
| Control | Una política centralizada para ambos robots |
| Interfaz | Pygame; entrenamiento separado de la reproducción |

Conocer las posiciones de las víctimas simplifica la tarea a navegación, coordinación y evacuación; no se afirmará que existe búsqueda a ciegas.

No se incluye batería, fuego dinámico, visión artificial, física 3D, varios pisos, interfaz web ni políticas independientes que aprendan simultáneamente.

## 4. Tiempo y daño térmico

**Regla confirmada por el usuario:** el daño depende de temperatura y duración de la exposición. Entrar en una casilla caliente no es el único evento que causa daño.

| Temperatura simulada T | Tasa de daño |
|---|---:|
| T < 40 °C | 0 |
| 40 ≤ T < 60 °C | 2 |
| 60 ≤ T < 80 °C | 5 |
| T ≥ 80 °C | 10 |

Cada paso global representa una unidad de tiempo simulado, con `delta_t = 1`. No implica un segundo físico real.

`daño_i = tasa(temperatura_en_posición_final_i) × delta_t`

`integridad_i = max(0, integridad_i - daño_i)`

Ambos robots reciben exposición en cada paso global, aunque esperen, choquen con una pared o su movimiento sea bloqueado. No hay recuperación de integridad al salir del calor. Ejemplo: cuatro pasos a 65 °C producen 20 puntos de daño por robot expuesto.

La velocidad visual solo modifica la reproducción. No debe modificar el número de pasos, las temperaturas ni el daño.

Son reglas abstractas del simulador, no umbrales reales de seguridad robótica. El daño a los sobrevivientes no se modela por separado en esta versión.

## 5. Paso global y acciones del controlador

La decisión más reciente reemplaza la idea anterior de aplicar daño únicamente al robot cuyo turno se ejecutaba.

En cada paso global:

1. El controlador selecciona una acción para cada robot desde el mismo estado inicial del paso.
2. El entorno calcula destinos y resuelve obstáculos y conflictos de movimiento.
3. Actualiza posiciones y aplica exposición térmica a ambos robots.
4. Si alguno queda destruido, finaliza en fracaso sin permitir un éxito simultáneo.
5. Si ambos siguen operativos, procesa recogidas y entregas automáticas.
6. Calcula recompensa, métricas y finalización.

**Decisión técnica inicial para implementar esta regla:** DQN seleccionará una acción conjunta entre 25 combinaciones posibles de cinco acciones individuales. Por ejemplo, `acción_conjunta = 5 × acción_robot_1 + acción_robot_2`. Así se evita que decidir para el segundo robot avance dos veces el reloj. Esta codificación es una decisión de implementación, no una exigencia del profesor.

## 6. Convenciones iniciales de movimiento

Para evitar ambigüedades al construir la base, se proponen estas convenciones verificables:

- Límites y obstáculos impiden el movimiento; el robot permanece en su posición.
- Fuera de la base, ambos robots no pueden ocupar la misma celda.
- Si ambos intentan llegar a una misma celda fuera de la base, ambos permanecen donde estaban.
- Intercambiar posiciones directamente queda bloqueado para ambos.
- Entrar en la celda de un robot que no puede salir queda bloqueado; entrar en una celda que el otro abandona está permitido si no hay intercambio directo.
- La base permite coincidencia de posiciones, pero no elimina daño por sí misma. Se configurará como celda segura.
- Una víctima solo puede recogerse una vez; al entregarla queda registrada como rescatada.

Estas convenciones pueden ajustarse durante la implementación, registrando aquí cualquier cambio que afecte experimentos.

## 7. Finalización

- Éxito: ambas víctimas entregadas y ambos robots con integridad mayor que cero.
- Fracaso: cualquiera de los robots llega a integridad cero.
- Límite: se alcanza el máximo configurable de pasos globales; valor inicial propuesto: 100.
- Una muerte tiene prioridad sobre una posible entrega en el mismo paso.
- Un éxito en el último paso permitido se registra como éxito, no como misión incompleta.
- En Gymnasium se distinguirá finalización por éxito/fracaso de truncamiento por límite de tiempo.

## 8. Aprendizaje

Se usará un controlador centralizado DQN. Hay dos robots en el entorno; no dos políticas independientes. La observación incluirá mapa, temperaturas, posiciones, integridad, estado de cada víctima y carga de cada robot, manteniendo tamaño fijo y valores normalizados cuando corresponda.

La recompensa será compartida: premiar entregas y misión completa; penalizar pasos, daño y destrucción. Los valores exactos se fijarán en configuración y se registrarán antes de comparar resultados. No se premiará repetidamente recoger una misma víctima.

Progresión: un robot y una víctima para verificar reglas; dos robots y dos víctimas sin calor para validar coordinación; incorporación gradual del riesgo térmico.

## 9. Evaluación y límites de las conclusiones

Referencia principal implementada: dos robots con asignación de víctimas distintas por distancia de camino y movimientos conjuntos que ignoran calor, usando las mismas reglas de colisión y tiempo. La búsqueda conjunta incluye esperar y desplazarse para resolver conflictos. Los detalles y límites están en `EVALUACION.md`.

Usar pocos diseños de edificio y variar ubicaciones válidas de víctimas y calor. Separar configuraciones de entrenamiento, validación y prueba. Comprobar conectividad y existencia de al menos una misión viable bajo daño y límite temporal; conectividad por sí sola no basta.

Registrar por episodio: identificador del escenario, semilla, estrategia, víctimas rescatadas, éxito, causa de finalización, pasos globales, daño por robot y total, integridad final y retorno.

Reportar tasa de éxito, rescates y daño; comparar duración también entre misiones exitosas para no favorecer fracasos tempranos. Repetir con varias semillas de entrenamiento si el presupuesto lo permite y declarar las limitaciones si solo se entrena una vez.

No afirmar generalización a edificios arbitrarios ni aprendizaje superior sin evidencia. Un resultado negativo también debe documentarse. Comparar uno contra dos robots no basta para demostrar cooperación aprendida.

## 10. Estado y próximos pasos

- [x] Definir alcance de una semana y cuatro integrantes.
- [x] Registrar que nosotros asumimos la persona 1.
- [x] Registrar exposición térmica para ambos robots por paso global.
- [x] Implementar primera base del motor, ejecutable por consola.
- [x] Verificar reglas críticas y una misión viable en el escenario de demostración.
- [x] Implementar referencia automática, política aleatoria y evaluación CSV.
- [x] Completar adaptador Gymnasium y recompensas verificadas.
- [x] Entrenar, guardar, cargar y reproducir una primera política.
- [x] Mejorar el controlador hasta completar el pasillo largo y los seis controles con un mismo checkpoint.
- [x] Hacer una primera comprobación en dos mapas de validación y dos de prueba, fuera del entrenamiento.
- [x] Construir una interfaz Pygame inicial con controles y métricas.
- [ ] Evaluar y preparar demostración.

Ya hay evidencia de aprendizaje en escenarios del currículo: el modelo sin entrenar no los completaba y el checkpoint seleccionado sí. Todavía no hay evidencia de superioridad sobre la referencia ni de generalización.

Actualización: el tercer experimento completa también los dos casos de validación y los dos de prueba registrados. Es una comprobación limitada de transferencia, no evidencia estadística de generalización amplia ni superioridad térmica.

### Primer incremento implementado

El motor aplica daño después de resolver movimientos y antes de recogidas y entregas. Las acciones conjuntas avanzan una sola vez el reloj. Incluye instantáneas JSON, reinicio, colisiones y finales por éxito, destrucción y límite.

El campo térmico inicial usa distancia Manhattan: `T(x,y) = max(ambiente, pico - caída × distancia_al_foco)`. Las paredes todavía no atenúan el calor. El daño registrado es pérdida efectiva de integridad: se limita a la integridad restante al destruirse un robot.

La demostración programada evacúa dos víctimas en diez pasos con integridad final 82 y 100. Las verificaciones incluyen exposición en espera, choques, umbrales, conflictos entre robots, no duplicación de recogidas y prioridad de destrucción. No representan entrenamiento ni comparación de estrategias.

### Segundo incremento implementado

La referencia automática asigna objetivos a partir del mapa y calcula acciones sin una secuencia predefinida. La búsqueda usa la misma función de movimiento que el simulador y no modifica el tiempo ni la integridad mientras planifica. Hay tres escenarios de desarrollo, una política aleatoria con semilla y exportación CSV de un episodio por estrategia y escenario. Los resultados medidos y sus límites figuran en `EVALUACION.md`. Todavía no hay entrenamiento ni prueba reservada.

### Tercer incremento: aprendizaje ejecutado

Se añadieron Gymnasium, observaciones completas normalizadas, recompensa compartida y guía por potencial. Se ejecutaron 82000 pasos DQN con semilla 0, en tres etapas. El mejor checkpoint quedó a los 42000 pasos y completa los cuatro escenarios del currículo. El checkpoint final falla en el escenario caliente, por lo que no se seleccionó.

El modelo seleccionado se cargó de nuevo y se comparó con referencias. En los mapas del currículo iguala sus tiempos y daño; en el pasillo compartido falla. El modelo y los resultados están en `artifacts/initial_dqn/`. Falta mejorar adaptación térmica, variedad de mapas, separación experimental y visualización. Los comandos y el contrato están en `APRENDIZAJE.md`.

### Cuarto incremento: cooperación, sensores y particiones

Se añadió una referencia térmica que confirma una ruta de menor daño, exploración que reinicia por etapa y escenarios separados para validación y prueba. El segundo experimento aprendió el paso compartido cercano, pero no consolidó todas las tareas.

El tercero añadió sensores locales y distancias de camino, conservando mapa completo y 25 acciones. Se entrenó desde cero durante 155000 pasos, semilla 0, y se seleccionó el checkpoint de 60000 con seis misiones completas. Después de congelarlo se consultaron dos casos de validación y dos de prueba: también completó los cuatro.

El modelo recomendado está en `artifacts/sensors_dqn/`. En el pasillo largo entrega las dos víctimas en 22 pasos sin daño. En `ruta_caliente` mantiene 74 puntos de daño, por lo que no resolvió todavía la optimización térmica. La referencia térmica recibe 34 en ese escenario. Quedan pendientes más semillas, mapas reservados, mejor gestión térmica y la interfaz gráfica.

### Quinto incremento: interfaz inicial

Se implementó una ventana Pygame con selector de escenario y estrategia, mapa de calor, trayectorias, personas y robots, integridad, temperatura, rescates y pasos. Incluye iniciar, pausar, reiniciar, avanzar un paso y cambiar velocidad. Se reproduce un episodio real preparado en segundo plano, sin duplicar reglas ni alterar exposición con el reloj visual.

Comando: `uv run --extra ui --extra rl python scripts/ui.py`. La aplicación comienza en el pasillo compartido y con el modelo recomendado. `INTERFAZ.md` documenta controles y verificación. La persona 3 puede refinar la presentación sobre esta base; siguen pendientes mejor gestión térmica, evaluación más amplia e integración final de la entrega.

### Alcance de cierre para el equipo: editor y posiciones variables

Se priorizó como próxima ampliación que el profesor pueda colocar dos sobrevivientes antes de iniciar el rescate, conservando edificios preparados, base, obstáculos y fuego estáticos. Esta capacidad todavía no está implementada; requiere editor, validación, serialización y entrenamiento con ubicaciones variables. No implica que el modelo actual resuelva cualquier posición elegida.

El validador distinguirá errores estructurales de viabilidad térmica certificada o no certificada. La derrota de DQN o de una referencia no se usará como prueba de imposibilidad. La comparación mantendrá exactamente la misma configuración para todas las estrategias.

La guía para los cuatro integrantes está en [README_EQUIPO.md](../README_EQUIPO.md). [BACKLOG.md](../BACKLOG.md) es la fuente de tareas pendientes para la entrega: incluye responsables, dependencias, criterios verificables, evaluación con varias semillas y cierre reproducible. Batería, urgencia y propagación del incendio quedan fuera del alcance de cierre.

### Ampliación V2: más escala y trabajo por módulos

Se aceptó ampliar el proyecto: dos robots, tres sobrevivientes, varios focos estáticos y objetivo de edificios de 12 × 12. El hito de base es 10 × 10. Persona 1 prepara la plataforma y mantiene entrenamiento/integración; persona 2 diseña edificios, calor y escenarios; persona 3 desarrolla editor y vistas; persona 4 realiza experimentación y análisis.

La implementación ahora admite conteo configurable de personas, firmas físicas, importación/exportación exacta y estrategias/episodios sobre una configuración común. Las referencias resuelven el mapa 10 × 10 de tres personas; el aprendizaje V2 sigue en piloto. Se preservó la versión 6 × 6 y se verificó su checkpoint sin alterar su resultado de 22 pasos en el pasillo.

El backlog creció a 32 tareas, con nuevos frentes de edificios y dificultad, calibración térmica, vistas/modelos por perfil, análisis de escala y trazas. [CONTRATOS_V2.md](CONTRATOS_V2.md) describe las APIs ya disponibles para que el equipo amplíe módulos sin reimplementar las reglas.
