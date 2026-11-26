# Alcance y protocolo de entrega (SARB-002)

## Alcance de cierre acordado el 26 de noviembre de 2026

El usuario autorizó cerrar una versión presentable antes de las 17:00 de Bogotá. Este acuerdo de equipo sustituye, para esta entrega, los objetivos anteriores de tres semillas y aprendizaje en cada movimiento; no constituye confirmación del profesor.

- Conservar simulador, editor, dos robots, tres personas, mapas 12 × 12 y cuatro estrategias.
- Limitar la nueva investigación de aprendizaje hasta las 13:10 y elegir el modelo con validación; admitir resultados parciales y fallos medidos.
- Publicar un modelo de una semilla de entrenamiento. Declarar esta limitación, sin calcular variabilidad entre semillas ni presentar configuraciones distintas como réplicas independientes.
- Implementar aprendizaje adicional al finalizar cada misión nueva del modo de aprendizaje, con modelo, memoria y progreso persistentes entre ejecuciones. Evaluación y comparación usan checkpoints fijos; reproducir una traza no entrena.
- Congelar configuración, modelo y hashes antes de evaluar los cuarenta casos reservados; ejecutar las referencias con cinco semillas aleatorias por caso. Registrar un protocolo explícito de una semilla antes de abrir resultados.
- Completar resultados, gráficas, informe técnico, guion, ejemplos de respaldo, comprobación en el computador disponible y publicación reproducible.
- Cerrar funcionalidades y pruebas hacia las 16:30, conservando treinta minutos de margen. No exigir instalación documentada en cuatro computadores para cerrar esta versión.

Los requisitos del profesor de las secciones siguientes siguen sin confirmación registrada. El backlog original se conserva como historial; sus criterios de tres semillas y aprendizaje en cada paso no se usan para afirmar que esta versión incumple el alcance reducido acordado.

**Responsable:** persona 4 con todo el equipo. **Revisa:** persona 1. **Preparado el:** 18 de noviembre de 2026.

**Estado:** borrador para la reunión con el profesor. Hasta que el profesor responda, ninguna fila de la sección 1 está confirmada. Las secciones 2 y 3 son decisiones del equipo y no se presentan como requisitos del curso.

## 1. Requisitos confirmados por el profesor

En el repositorio no hay ninguna confirmación registrada. Según la propuesta original, el profesor valora agentes que actúen sobre una simulación, con una tarea observable y decisiones con consecuencias. Esa propuesta no es una rúbrica (ver `docs/CONTEXTO.md` y `README_EQUIPO.md`, sección 2).

Al recibir cada respuesta se completa esta tabla con la fecha y el medio (clase, correo o foro). No se marca nada como confirmado por deducción.

| Tema | Respuesta del profesor | Fecha | Medio | Registró |
|---|---|---|---|---|
| Entregables (código, informe, presentación, video) | Pendiente | | | |
| Fecha y hora de entrega | Pendiente | | | |
| Duración de la exposición y formato de la demostración | Pendiente | | | |
| Criterios de evaluación o rúbrica | Pendiente | | | |
| Formato y extensión del informe | Pendiente | | | |
| Escala final: 12 × 12 o hito 10 × 10 | Pendiente | | | |
| Aprendizaje por refuerzo (DQN) como requisito o como elección del equipo | Pendiente | | | |
| Aceptación de resultados negativos del aprendizaje | Pendiente | | | |

## 2. Decisiones del equipo

Están tomadas y ya implementadas o en el backlog. Se presentan al profesor para validarlas, no como exigencias suyas.

| Decisión | Dónde consta |
|---|---|
| Rescate en un edificio 2D con **dos robots** de capacidades iguales y control **centralizado** (una acción conjunta de 25 combinaciones) | `docs/CONTEXTO.md`, `docs/CONTRATOS_V2.md` |
| **Tres personas** inmóviles; cada robot lleva una a la vez, así que hacen falta varios viajes | `README_EQUIPO.md`, sección 1 |
| **Varios focos de calor estáticos**; el daño depende de la temperatura y del tiempo de exposición (regla pedida por quien dirigió la base) | `docs/CONTEXTO.md`, sección 4 |
| **Edificios preparados** por el equipo; el usuario solo coloca a las personas con el editor | `BACKLOG.md`, meta de cierre |
| Objetivo de escala **12 × 12**, partiendo del hito integrado de 10 × 10 | `BACKLOG.md`, sección 1 |
| Política aprendida con **DQN** comparada con ruta corta, ruta térmica y aleatoria | `docs/APRENDIZAJE.md`, `docs/METRICAS.md` |
| Interfaz **Pygame**; el entrenamiento está separado de la reproducción | `docs/INTERFAZ.md` |
| **Aprendizaje continuo** con memoria persistente entre ejecuciones, incorporado al alcance por el equipo | `BACKLOG.md`, SARB-033 a SARB-035 |
| Fuera de alcance: batería, plazos de supervivencia, fuego dinámico, visión artificial, varios pisos, más robots, física 3D y aplicación web | `README_EQUIPO.md`, sección 6 |

## 3. Protocolo de evaluación adoptado por el equipo

- **Primero el rescate completo.** Se informan éxitos, personas entregadas, daño y pasos. Pasos y daño se comparan solo entre misiones exitosas, y una misión fallida con poco daño no cuenta como mejor (`docs/METRICAS.md`).
- **Mismos casos para todas las estrategias.** DQN y las tres referencias se evalúan sobre escenarios congelados idénticos; cada fila se puede reproducir desde su traza (SARB-020).
- **Particiones congeladas antes de entrenar.** El perfil 12 × 12 tiene 60 casos de entrenamiento, 20 de validación y 40 de prueba (`docs/PARTICIONES_V2.md`). La prueba se abre una sola vez, con modelos congelados de tres semillas (SARB-019 y SARB-021).
- **Resultados negativos admitidos.** No se garantiza que DQN supere a una búsqueda clásica. Si no aprende en 12 × 12, se informa así, con sus datos.
- **Límites declarados.** Sesgo de certificación de los casos, edificios conocidos, sensores calculados con el mapa completo y simplificación térmica (`docs/FIGURAS.md`, sección 6).

## 4. Preguntas para el profesor

1. ¿Qué se entrega exactamente (repositorio, informe, presentación, video) y en qué fecha y hora?
2. ¿Cuánto dura la exposición? ¿El profesor quiere colocar las personas él mismo durante la demostración?
3. ¿Hay rúbrica o criterios de evaluación? ¿Qué peso tienen el funcionamiento, la formulación, el aprendizaje y el análisis?
4. ¿Qué formato y extensión debe tener el informe?
5. ¿Es aceptable el objetivo de 12 × 12 o prefiere asegurar el hito de 10 × 10? (ver sección 5)
6. ¿El aprendizaje por refuerzo es un requisito del curso o una elección válida del equipo? ¿Es aceptable presentar un aprendizaje parcial con su análisis frente a las referencias?
7. ¿Se considera parte del alcance el aprendizaje continuo entre ejecuciones, o basta con modelos entrenados y congelados?
8. ¿Hay restricciones del computador de presentación (sistema, red, tiempo de instalación)?

## 5. Escala: 12 × 12 o 10 × 10

El backlog fija 12 × 12 como objetivo y exige registrar una reducción antes de la prueba final, sin ocultarla. Propuesta para discutir con el equipo y el profesor (no está acordada):

- Decidir antes de abrir la prueba final (SARB-021) y registrar la decisión aquí, con su fecha.
- Si se mantiene 12 × 12, la evaluación final usa el manifiesto congelado `v2_12x12_v1` tal como está.
- Si se reduce a 10 × 10, se crea un manifiesto propio del perfil 10 × 10 con `scripts/build_partitions.py` y otro `manifest_id`. El conjunto `v2_10x10_dev_v1` de SARB-031 es de desarrollo y no puede usarse como prueba.
- En cualquier caso no se añaden batería ni fuego dinámico, y un checkpoint de un perfil no se evalúa como si fuera de otro.

## 6. Registro de la reunión

| Campo | Valor |
|---|---|
| Fecha y medio | Pendiente |
| Asistentes | Pendiente |
| Respuestas | Completar la sección 1 |
| Cambios de alcance acordados | Pendiente |
| Acciones y responsables | Pendiente |

Cuando la sección 1 tenga respuestas, se actualizan `BACKLOG.md` (si cambia el alcance), el informe (SARB-025) y el guion de la demostración (SARB-026).
