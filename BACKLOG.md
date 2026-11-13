# SAR-Bot — backlog para una entrega completa

**Actualización:** 13 de noviembre de 2026. **Equipo:** cuatro personas. **Horizonte orientativo:** una semana de trabajo restante.

Este backlog parte de una base funcional; no asigna como pendientes el motor, la primera interfaz o los checkpoints ya construidos. El contexto para nuevos integrantes está en [README_EQUIPO.md](README_EQUIPO.md).

## 1. Meta de cierre

Entregar una simulación en la que el profesor pueda colocar dos sobrevivientes en edificios preparados, observar a los robots, comparar estrategias sobre la misma misión y revisar evidencia de aprendizaje con ubicaciones variadas y casos reservados.

El éxito del proyecto se valorará con funcionamiento, formulación del problema, aprendizaje reproducible, calidad experimental y explicación de límites. No se garantiza que DQN supere una búsqueda clásica en cada escenario, ni que todas las ubicaciones transitables sean rescatables.

## 2. Cómo usar este backlog

- **P0:** necesario para cerrar el funcionamiento o la validez de la entrega.
- **P1:** necesario para la calidad de la entrega que queremos mostrar. Se aborda después de sus dependencias P0.
- No hay tareas opcionales escondidas entre los requisitos: la meta es cerrar las 27 tareas P0 y P1. Batería, urgencia, fuego dinámico, web y 3D quedan fuera.
- Marcar la casilla del índice solo cuando se cumplan los criterios, exista evidencia y el cambio esté integrado en la base acordada. Una rama aislada que aún no se integra no está terminada.
- Cada tarea tiene autor principal y revisor; los nombres reales se asignan entre integrantes. Las horas son esfuerzo activo orientativo, no duración garantizada de entrenamiento ni disponibilidad del profesor.
- Ante un bloqueo, registrar causa, siguiente acción y persona que puede resolverla. Continuar otras tareas independientes; no cambiar el alcance o inventar resultados para cerrar una casilla.

### Índice de seguimiento

- [ ] [SARB-001 — Publicar la base compartida](#sarb-001) · P0 · Persona 1
- [ ] [SARB-002 — Confirmar alcance y protocolo de entrega](#sarb-002) · P0 · Persona 4 + equipo
- [ ] [SARB-003 — Ejecutar la base en los cuatro equipos](#sarb-003) · P0 · Persona 4 + equipo
- [ ] [SARB-004 — Acordar el contrato de escenario editable](#sarb-004) · P0 · Persona 1 + persona 2
- [ ] [SARB-005 — Validar ubicaciones y archivos](#sarb-005) · P0 · Persona 2
- [ ] [SARB-006 — Comprobar viabilidad térmica sin falsas garantías](#sarb-006) · P0 · Persona 2
- [ ] [SARB-007 — Guardar y cargar escenarios personalizados](#sarb-007) · P0 · Persona 2
- [ ] [SARB-008 — Generar ubicaciones variables reproducibles](#sarb-008) · P0 · Persona 2
- [ ] [SARB-009 — Reservar nuevas particiones experimentales](#sarb-009) · P0 · Persona 4
- [ ] [SARB-010 — Editor visual de dos sobrevivientes](#sarb-010) · P0 · Persona 3
- [ ] [SARB-011 — Conectar editor, motor y reproducción](#sarb-011) · P0 · Persona 3 + persona 1
- [ ] [SARB-012 — Importar y exportar desde la interfaz](#sarb-012) · P0 · Persona 3
- [ ] [SARB-013 — Comparar estrategias en pantalla](#sarb-013) · P1 · Persona 3 + persona 4
- [ ] [SARB-014 — Mejorar mensajes y explicación visual](#sarb-014) · P1 · Persona 3
- [ ] [SARB-015 — Adaptar Gymnasium a ubicaciones variables](#sarb-015) · P0 · Persona 1
- [ ] [SARB-016 — Entrenar con semillas, validación y metadatos](#sarb-016) · P0 · Persona 1
- [ ] [SARB-017 — Ejecutar un piloto y diagnosticar aprendizaje](#sarb-017) · P0 · Persona 1
- [ ] [SARB-018 — Investigar la decisión entre distancia y calor](#sarb-018) · P1 · Persona 1
- [ ] [SARB-019 — Entrenar tres semillas y congelar modelos](#sarb-019) · P0 · Personas 1 y 4
- [ ] [SARB-020 — Unificar comparaciones y métricas](#sarb-020) · P0 · Persona 4
- [ ] [SARB-021 — Ejecutar la evaluación final reservada](#sarb-021) · P0 · Persona 4
- [ ] [SARB-022 — Producir gráficas y tablas finales](#sarb-022) · P1 · Persona 4
- [ ] [SARB-023 — Analizar fallos y límites con trazas](#sarb-023) · P1 · Persona 4 + persona 1
- [ ] [SARB-024 — Verificar el flujo completo de la aplicación](#sarb-024) · P0 · Personas 3 y 2
- [ ] [SARB-025 — Escribir el informe técnico final](#sarb-025) · P0 · Persona 4 + equipo
- [ ] [SARB-026 — Preparar y ensayar la demostración](#sarb-026) · P0 · Persona 4 + equipo
- [ ] [SARB-027 — Cerrar la versión reproducible de entrega](#sarb-027) · P0 · Persona 1 + equipo

## 3. Reparto y orden de trabajo

| Persona | Frente principal | Carga activa orientativa, con revisiones |
|---|---|---|
| 1 | Contratos, aprendizaje e integración | 24–32 h |
| 2 | Entorno, validación, viabilidad y generación | 16–24 h |
| 3 | Editor, interacción y presentación visual | 18–26 h |
| 4 | Protocolo, evaluación, gráficas y entrega académica | 22–30 h |

La persona 1 tiene mayor complejidad técnica y revisa integraciones; no debe absorber la implementación del editor, todos los mapas y todo el informe. Las estimaciones dependen de la experiencia del grupo y deben ajustarse al empezar. Los entrenamientos se pueden ejecutar en máquinas distintas con el mismo entorno y configuración.

### Dependencia principal

Publicación y contrato → validación y serialización → editor y generación → entrenamiento variable → selección sobre validación → congelación → prueba final → informe y demostración.

El editor puede construirse sobre datos de ejemplo mientras persona 2 desarrolla validación. Persona 4 puede preparar métricas y el informe antes de disponer del modelo final.

### Calendario de referencia

| Día | Resultado compartido esperado |
|---|---|
| 1 | Base publicada, instalación de todos, alcance y contrato acordados |
| 2 | Validación, serialización, generador inicial y editor básico |
| 3 | Editor integrado y primer entrenamiento con ubicaciones variables |
| 4 | Piloto analizado, experimento térmico acotado y vista de comparación |
| 5 | Configuración elegida, tres semillas entrenadas y modelos congelados |
| 6 | Prueba final, gráficas, análisis de fallos y verificación de aplicación |
| 7 | Informe cerrado, instalación limpia, ensayo y versión de entrega |

No usar este calendario para dar por aprobados hitos que no se cumplieron. Si el aprendizaje requiere más cómputo, registrar el presupuesto y acordar el alcance con el profesor sin falsear la evaluación.

## 4. Preparación e integración

<a id="sarb-001"></a>
### SARB-001 — Publicar la base compartida

**P0 · Responsable:** persona 1 · **Revisa:** persona 4 · **Depende de:** ninguna · **Esfuerzo:** 1 h.

Resolver la autenticación pendiente y publicar todos los commits de la base. Comunicar la rama estable real; todavía no asumir que `main` tiene el modelo o la interfaz.

**Aceptación:**
- El remoto contiene README, interfaz, checkpoint recomendado y evidencia; el commit comunicado coincide con el obtenido por otro integrante.
- Se publica la rama de trabajo o se integra mediante revisión; no se fuerza una actualización que descarte cambios ajenos.
- El equipo conoce el punto de partida, el procedimiento de ramas y quién integra.

**Evidencia:** URL del repositorio o PR y hash confirmado en un segundo clon.

<a id="sarb-002"></a>
### SARB-002 — Confirmar alcance y protocolo de entrega

**P0 · Responsable:** persona 4 con todo el equipo · **Revisa:** persona 1 · **Depende de:** ninguna · **Esfuerzo:** 1 h más disponibilidad del profesor.

Validar dos robots, control centralizado, simulación 2D, editor de personas y aprendizaje por refuerzo. Preguntar entregables, fecha, duración de exposición y criterios de evaluación.

**Aceptación:**
- Hay una nota con requisitos confirmados, decisiones propias y dudas pendientes, diferenciados.
- El equipo adopta como entrega dos personas en edificios preparados; no añade batería o fuego dinámico sin revisar tiempo y alcance.
- Se acuerda evaluar rescates completos, daño y pasos, admitiendo resultados negativos y límites del aprendizaje.

**Evidencia:** nota en `docs/` con fecha y acuerdos; no atribuir al profesor decisiones sin confirmar.

<a id="sarb-003"></a>
### SARB-003 — Ejecutar la base en los cuatro equipos

**P0 · Responsable:** persona 4 coordina; todos ejecutan · **Revisa:** persona 1 · **Depende de:** SARB-001 · **Esfuerzo:** 2 h compartidas.

**Aceptación:**
- Cada integrante instala desde el mismo commit con el lockfile y abre la interfaz sin entrenar otra vez.
- Se reproduce el pasillo actual: dos rescates, 22 pasos, daño cero.
- Se ejecutan las pruebas y se registran sistema, Python, commit y cualquier incidencia.
- Las instrucciones se corrigen usando los errores de instalación reales encontrados.

**Evidencia:** tabla de cuatro comprobaciones en `docs/`, con salidas o capturas breves.

<a id="sarb-004"></a>
### SARB-004 — Acordar el contrato de escenario editable

**P0 · Responsable:** persona 1 con persona 2 · **Revisa:** personas 3 y 4 · **Depende de:** SARB-002 · **Esfuerzo:** 1 h.

Definir una representación única del edificio fijo y las dos posiciones editables. Decidir dónde residen validación, serialización e identificador de configuración.

**Aceptación:**
- Hay un ejemplo concreto que UI, motor, entrenamiento y evaluación pueden consumir.
- Se documentan coordenadas internas `(x, y)` con origen arriba a la izquierda y su correspondencia con columnas/filas visuales.
- La edición no cambia base, paredes, temperaturas, dimensión ni límite de pasos de la plantilla.
- El escenario preparado es inmutable; se acuerda adaptar la preparación actual, que hoy recibe una ruta de archivo.
- Se fija la política para etiquetas de personas y la firma canónica de ubicaciones, para no duplicar casos por intercambiar Persona 1 y Persona 2.

**Archivos de referencia:** `core/simulation.py`, `ui/playback.py` y esquema JSON actual. Los módulos nuevos se acuerdan antes de crearlos.

## 5. Escenarios, validación y datos

<a id="sarb-005"></a>
### SARB-005 — Validar ubicaciones y archivos

**P0 · Responsable:** persona 2 · **Revisa:** persona 1 · **Depende de:** SARB-004 · **Esfuerzo:** 2 h.

**Aceptación:**
- Rechaza personas fuera del mapa, sobre paredes, en la base o en la misma celda; exige exactamente dos.
- Rechaza coordenadas con tipos inválidos, dimensiones/límites inválidos, temperaturas no finitas y JSON incompleto con mensajes comprensibles.
- Comprueba conexión entre base y personas; no presenta conectividad como garantía térmica.
- UI, importación y generador reutilizan el mismo validador.
- Se añaden pruebas de límites, duplicados, tipos y celdas desconectadas, conservando las reglas existentes.

**Evidencia:** tabla de entradas válidas/inválidas y pruebas de comportamiento. El código actual ya realiza parte de estas verificaciones; completar y unificar, no duplicarlo.

<a id="sarb-006"></a>
### SARB-006 — Comprobar viabilidad térmica sin falsas garantías

**P0 · Responsable:** persona 2 · **Revisa:** persona 1 · **Depende de:** SARB-005 · **Esfuerzo:** 4 h.

Usar un procedimiento acotado que busque una misión completa con ambos robots, integridad y límite temporal. Una trayectoria exitosa de una referencia puede funcionar como certificado positivo.

**Aceptación:**
- Distingue error estructural, viable con trayectoria testigo y no certificado dentro del presupuesto disponible.
- Solo afirma imposibilidad cuando existe una prueba válida; el fallo de una heurística o el agotamiento de búsqueda no bastan.
- Reproduce la trayectoria testigo en el motor y confirma ambas entregas, integridad positiva y pasos permitidos.
- La comprobación no utiliza el éxito de DQN para aceptar o rechazar posiciones.
- Se registra qué procedimiento produjo cada testigo. Si una referencia certifica los casos, se declara el sesgo de ese filtro a favor de la referencia; no se presenta su éxito en esos mismos casos como una validación independiente de eficacia universal.
- Tiene presupuesto de búsqueda y no congela la ventana. Un caso no certificado puede ejecutarse como exploración, identificado como tal; un caso estructuralmente inválido no inicia.
- Se prueban un caso viable, uno desconectado y otro conectado cuyo rescate no queda certificado térmicamente.

**Evidencia:** resultado del validador y testigo o explicación del límite; la UI recibe un estado explícito, no un booleano ambiguo.

<a id="sarb-007"></a>
### SARB-007 — Guardar y cargar escenarios personalizados

**P0 · Responsable:** persona 2 · **Revisa:** personas 1 y 3 · **Depende de:** SARB-004, SARB-005 · **Esfuerzo:** 2 h.

**Aceptación:**
- Exporta edificio, dos personas, parámetros térmicos, base, límites, versión del esquema e identificador o hash.
- La importación reconstruye un `Scenario` equivalente; no cambia el campo térmico ni la plantilla original.
- Guardar y volver a cargar conserva resultados de una estrategia determinista y semilla.
- Los escenarios creados durante la demo se guardan fuera de las particiones reservadas.
- Hay una prueba de ida y vuelta y mensajes claros para archivos inválidos.

**Evidencia:** un JSON de ejemplo válido y su reproducción con el motor. Mantener compatibilidad documentada con los escenarios ya existentes.

<a id="sarb-008"></a>
### SARB-008 — Generar ubicaciones variables reproducibles

**P0 · Responsable:** persona 2 · **Revisa:** personas 1 y 4 · **Depende de:** SARB-005, SARB-006, SARB-007 · **Esfuerzo:** 3 h.

**Aceptación:**
- Genera posiciones distintas para dos personas en dos edificios de 6 × 6, manteniendo la geometría y el calor por plantilla.
- Una semilla reproduce exactamente las configuraciones y sus identificadores.
- Incluye casos cercanos/lejanos, rutas compartidas y distintas exposiciones; no genera solo posiciones cómodas.
- Elimina duplicados físicos aunque se intercambien etiquetas de las personas.
- Los casos para medir rescates viables tienen certificado positivo; los no certificados o adversarios se separan para diagnóstico.
- Produce un resumen de cantidad solicitada, aceptada, descartada y no certificada; no reintenta indefinidamente.

**Evidencia:** conjunto generado, semilla, firmas canónicas, testigos y registro de generación.

<a id="sarb-009"></a>
### SARB-009 — Reservar nuevas particiones experimentales

**P0 · Responsable:** persona 4 con persona 2 · **Revisa:** persona 1 · **Depende de:** SARB-008, SARB-002 · **Esfuerzo:** 2 h.

**Aceptación:**
- Objetivo de planificación por cada uno de dos edificios: 30 configuraciones de entrenamiento, 10 de validación y 20 de prueba; total orientativo 60/20/40.
- Si la capacidad real obliga a reducirlo, se acuerdan y registran las cantidades antes de entrenar. El cierre requiere al menos 20 configuraciones viables nuevas de prueba en total; cualquier reducción adicional exige redefinir y declarar el alcance de evaluación.
- Las firmas físicas, incluidas las posiciones sin orden de etiquetas, no se repiten entre particiones.
- Se documentan los criterios de generación y certificación y la distribución resultante; un conjunto de casos certificados no representa todas las posiciones transitables posibles.
- Se preservan los conjuntos y resultados antiguos como históricos; no se presentan como la nueva prueba final.
- Se fija un manifiesto versionado y sus hashes antes de abrir resultados de DQN en prueba.
- El conjunto de prueba no se usa para entrenar, elegir checkpoints, ajustar recompensas o decidir qué semilla mostrar.

**Evidencia:** nuevo manifiesto, resumen de distribución y verificación automática de separación. El edificio puede repetirse porque se estudia generalización a ubicaciones dentro de edificios conocidos.

## 6. Editor e interfaz

<a id="sarb-010"></a>
### SARB-010 — Editor visual de dos sobrevivientes

**P0 · Responsable:** persona 3 · **Revisa:** persona 2 · **Depende de:** SARB-004, SARB-005 · **Esfuerzo:** 4 h.

**Aceptación:**
- Botón visible para entrar a edición antes de la misión; permite elegir Persona 1 o Persona 2 y colocarla con clics.
- Ofrece limpiar posiciones y restaurar las de la plantilla; muestra cuántas personas faltan.
- No permite editar paredes, base o fuego. Un clic inválido explica la causa sin cerrar la aplicación.
- El clic se traduce correctamente al redimensionar la ventana y no se confunde con controles o márgenes.
- El mapa distingue vista de edición de reproducción y refleja la validación estructural.

**Archivos actuales:** `ui/app.py`; reutilizar el validador de persona 2. **Evidencia:** captura y comprobación de colocación en bordes y ventana redimensionada.

<a id="sarb-011"></a>
### SARB-011 — Conectar editor, motor y reproducción

**P0 · Responsable:** persona 3 con persona 1 · **Revisa:** persona 2 · **Depende de:** SARB-007, SARB-010 · **Esfuerzo:** 3 h.

**Aceptación:**
- Iniciar utiliza exactamente las posiciones editadas y el escenario validado, no el archivo original sin cambios.
- Editar cancela o invalida la preparación anterior y deja la nueva misión pausada en el paso cero.
- Cambiar estrategia conserva las ubicaciones elegidas y reinicia integridad, carga y contadores.
- El episodio preparado contiene la firma de su configuración; nunca aparece en pantalla un resultado de una selección anterior pendiente.
- Se identifica viabilidad no certificada y se permite explorar sin prometer éxito. El modelo actual puede fallar en posiciones nuevas; no se cambia silenciosamente a una referencia para ocultarlo.
- El daño sigue calculándose solo en el motor y depende de pasos globales, no de la velocidad de reproducción.

**Evidencia:** pruebas de edición durante preparación, cambio rápido de estrategia y dos ejecuciones del mismo caso.

<a id="sarb-012"></a>
### SARB-012 — Importar y exportar desde la interfaz

**P0 · Responsable:** persona 3 · **Revisa:** persona 2 · **Depende de:** SARB-007, SARB-010, SARB-011 · **Esfuerzo:** 2 h.

**Aceptación:**
- El usuario puede guardar su escenario y recuperarlo desde la aplicación con un flujo sencillo; una lista de archivos locales controlada es suficiente.
- La UI confirma el nombre o identificador guardado y explica errores de carga.
- La carga valida el archivo y prepara una misión nueva sin contaminar los conjuntos reservados.
- El mismo archivo produce la misma misión determinista en otro equipo.

**Evidencia:** escenario creado por un compañero, exportado y ejecutado por otro, con las mismas posiciones y resultado.

<a id="sarb-013"></a>
### SARB-013 — Comparar estrategias en pantalla

**P1 · Responsable:** persona 3 con persona 4 · **Revisa:** persona 1 · **Depende de:** SARB-011, SARB-020 · **Esfuerzo:** 4 h.

**Aceptación:**
- Una acción permite comparar DQN, ruta corta, ruta térmica y aleatoria sobre el mismo escenario congelado.
- Muestra rescates, finalización, pasos y daño por estrategia, sin mezclar resultados de otra configuración.
- Incluye la semilla aleatoria y el modelo utilizado; permite reproducir cada resultado.
- La comparación se prepara sin bloquear la ventana; cambiar el escenario invalida la tabla anterior.
- No etiqueta como mejor una misión fallida solo porque recibió menos daño. No confunde tiempo simulado con duración del cómputo.

**Evidencia:** tabla visible en un caso con conflicto entre ruta corta y ruta segura, con exportación o referencia al CSV equivalente.

<a id="sarb-014"></a>
### SARB-014 — Mejorar mensajes y explicación visual

**P1 · Responsable:** persona 3 · **Revisa:** persona 4 · **Depende de:** SARB-010, SARB-011 · **Esfuerzo:** 2 h.

**Aceptación:**
- Ayuda breve para colocar personas, ejecutar, pausar, reiniciar y comparar.
- Los colores tienen apoyo en números, etiquetas o iconos; se distinguen robots, personas, fuego y base.
- Se entiende la diferencia entre persona recogida y entregada, y entre éxito, destrucción y límite temporal.
- Las ubicaciones no certificadas y los modelos no evaluados para el nuevo alcance se identifican con lenguaje comprensible.
- Se inspeccionan capturas de edición, traslado, éxito y fracaso, y la ventana no oculta controles en el equipo de presentación.

**Evidencia:** revisión por un compañero que no implementó la UI y lista breve de correcciones.

## 7. Aprendizaje

<a id="sarb-015"></a>
### SARB-015 — Adaptar Gymnasium a ubicaciones variables

**P0 · Responsable:** persona 1 · **Revisa:** persona 2 · **Depende de:** SARB-004, SARB-008 · **Esfuerzo:** 4 h.

**Aceptación:**
- `reset` selecciona configuraciones solo de la partición solicitada y se reproduce con semilla.
- La observación refleja las dos posiciones reales y actualiza sensores/distancias para el escenario elegido.
- Se conserva el espacio de 25 acciones y, si es posible, el esquema de 157 entradas; si cambia, se versionan esquema y modelos.
- Un modelo antiguo no se presenta como validado para el nuevo alcance aunque su dimensión permita cargarlo.
- Se comprueban rescate automático, daño simultáneo y límites en varias ubicaciones, y pasan los verificadores oficiales de Gymnasium/SB3.
- No hay posiciones o respuestas de prueba en la generación de entrenamiento.

**Evidencia:** prueba de varias selecciones reproducibles y un registro de observaciones antes/después de cambiar ubicaciones.

<a id="sarb-016"></a>
### SARB-016 — Entrenar con semillas, validación y metadatos

**P0 · Responsable:** persona 1 · **Revisa:** persona 4 · **Depende de:** SARB-009, SARB-015 · **Esfuerzo:** 2 h.

**Aceptación:**
- Se puede configurar cada semilla sin editar el motor; añadir un argumento de CLI es válido si queda documentado.
- La evaluación periódica para elegir checkpoint usa validación separada; los controles de entrenamiento se identifican como tales.
- La selección no consulta el conjunto de prueba ni depende de elegir luego la semilla que mejor salió en prueba.
- Se guardan configuración efectiva, semilla, versión de código y observación, hashes de datos/modelo y registros de episodios.
- Los metadatos indican correctamente qué partición se usó; actualizar los mensajes actuales que describen los controles como escenarios también entrenados cuando ya no corresponda.
- La memoria de experiencias, inicialización y exploración por etapa quedan registradas; los experimentos anteriores no se sobrescriben.

**Evidencia:** ejecución breve que guarda, carga y evalúa un modelo con esa configuración, sin requerir convergencia en la prueba de integración.

<a id="sarb-017"></a>
### SARB-017 — Ejecutar un piloto y diagnosticar aprendizaje

**P0 · Responsable:** persona 1 · **Revisa:** persona 4 · **Depende de:** SARB-015, SARB-016 · **Esfuerzo:** 3 h activas más cómputo.

**Aceptación:**
- Se ejecuta un piloto con posiciones variables, empezando por casos sencillos y aumentando dificultad.
- Se comparan modelo sin entrenar y checkpoint seleccionado sobre validación, registrando rescates reales además del retorno.
- Se revisan trayectorias de bloqueo, persecución de la misma persona, entregas incompletas y exposición innecesaria.
- Se fija un presupuesto de cómputo y una decisión documentada sobre configuración y alcance para la siguiente etapa.
- Si falla el piloto, se simplifica el currículo o se corrige la formulación antes de multiplicar entrenamientos; no se inventa una mejora ni se cambian casos de prueba para favorecerlo.

**Evidencia:** ficha de experimento con configuración, curvas preliminares o CSV, casos inspeccionados y decisión.

<a id="sarb-018"></a>
### SARB-018 — Investigar la decisión entre distancia y calor

**P1 · Responsable:** persona 1 · **Revisa:** personas 2 y 4 · **Depende de:** SARB-017, SARB-020 · **Esfuerzo:** 4 h activas, con presupuesto explícito.

**Aceptación:**
- Hay casos de desarrollo con rescate viable y alternativas de diferente duración y daño.
- Se estudia una modificación acotada cada vez, por ejemplo peso del daño o progresión de dificultad térmica, conservando un control comparable.
- Se mide rescate completo, daño y pasos; evitar calor abandonando una persona no cuenta como mejora.
- Se contrasta con las referencias geométrica y térmica y se explicita su costo en pasos.
- Se conserva una configuración estable para cierre. Si no hay mejora consistente, se entrega el análisis del resultado negativo y se declara la limitación.
- No se reescriben reglas del entorno después de ver prueba para hacer ganar a DQN.

**Evidencia:** comparación de desarrollo con trazas y conclusión. No es requisito afirmar superioridad universal sobre Dijkstra.

<a id="sarb-019"></a>
### SARB-019 — Entrenar tres semillas y congelar modelos

**P0 · Responsable:** personas 1 y 4 · **Revisa:** persona 2 · **Depende de:** SARB-009, SARB-017, SARB-018 · **Esfuerzo:** 2 h activas más entrenamientos.

**Aceptación:**
- Se ejecutan al menos tres semillas independientes de la misma configuración final; tres configuraciones con semilla 0 no cumplen este criterio.
- Para cada semilla se conserva su checkpoint seleccionado exclusivamente con validación.
- Antes de prueba se fijan configuración, checkpoints, hashes, particiones y política de selección del modelo de la demo.
- Se evalúan las tres semillas finales, no solo la que luego obtenga mejores resultados de prueba.
- El modelo de demostración carga en la aplicación y su historial de selección está explicado.

**Evidencia:** manifiesto de congelación y tres ejecuciones reproducibles. Si se cambia algo después de ver prueba, ese resultado pasa a desarrollo y se prepara una nueva prueba antes de afirmar independencia.

## 8. Evaluación y evidencia

<a id="sarb-020"></a>
### SARB-020 — Unificar comparaciones y métricas

**P0 · Responsable:** persona 4 · **Revisa:** persona 1 · **Depende de:** SARB-007, SARB-009 · **Esfuerzo:** 3 h.

**Aceptación:**
- DQN y las tres referencias reciben el mismo escenario, posiciones, temperaturas, integridad y límite temporal.
- Cada ejecución comienza limpia; cambiar velocidad visual no afecta las métricas.
- El CSV registra configuración, partición, estrategia, semilla del modelo o aleatoria según corresponda, hash del modelo, rescates, éxito, finalización, pasos y daño/integridad por robot y total.
- Se distinguen semillas de entrenamiento, de generación de escenarios y de acciones aleatorias.
- Se prueba que las métricas corresponden a la traza del motor y que no se reutilizan datos de una misión anterior.
- El retorno se interpreta con su función de recompensa; no se comparan directamente retornos de perfiles distintos como si fueran la misma escala.

**Evidencia:** comparación pequeña reproducible y diccionario de columnas. Reutilizar y extender los evaluadores actuales.

<a id="sarb-021"></a>
### SARB-021 — Ejecutar la evaluación final reservada

**P0 · Responsable:** persona 4 · **Revisa:** persona 1 · **Depende de:** SARB-019, SARB-020 · **Esfuerzo:** 3 h activas más ejecuciones.

**Aceptación:**
- Se usan los modelos congelados y todos los escenarios de prueba declarados, incluidos los casos difíciles; no se eliminan fallos después de observarlos.
- Se evalúan las tres semillas DQN y las referencias sobre los mismos casos. Para la referencia aleatoria se fijan al menos cinco semillas de acciones por caso.
- Las referencias deterministas se ejecutan una vez por caso; repetirlas sin variación no aumenta evidencia.
- Se reportan resultados por edificio, por semilla de entrenamiento y agregados, indicando número de configuraciones distintas y episodios.
- Se registra que varios modelos sobre los mismos mapas producen datos relacionados; no se presenta cada repetición como un mapa independiente.
- La comparación de daño y pasos incluye resultados entre misiones exitosas, número de casos emparejados y tasas de fracaso. No se favorecen fracasos tempranos de poco daño.
- La discusión informa si los casos fueron aceptados porque una referencia ya los resolvía y cómo eso limita la interpretación de su tasa de éxito.

**Evidencia:** CSV final, metadatos, manifiesto de congelación y comandos usados. A partir de aquí no se ajusta el modelo usando esos resultados sin reclasificarlos.

<a id="sarb-022"></a>
### SARB-022 — Producir gráficas y tablas finales

**P1 · Responsable:** persona 4 · **Revisa:** persona 3 · **Depende de:** SARB-021 · **Esfuerzo:** 3 h.

**Aceptación:**
- Curvas de entrenamiento y rescates en validación por semilla, con ejes y unidades claros.
- Comparación de éxito y personas entregadas por estrategia.
- Comparación de daño y pasos entre éxitos, indicando tamaños de muestra y casos emparejados.
- Una vista de la relación entre duración y daño que muestre el costo de elegir rutas seguras.
- Las tablas y figuras se generan desde los CSV conservados; no se transcriben resultados a mano.
- Se muestran variación entre semillas y límites del tamaño de prueba, sin intervalos engañosos ni porcentajes sin denominador.
- Se guardan imágenes legibles para el informe y las instrucciones de regeneración.

**Evidencia:** script de generación, datos fuente y figuras exportadas en un directorio acordado de resultados finales.

<a id="sarb-023"></a>
### SARB-023 — Analizar fallos y límites con trazas

**P1 · Responsable:** persona 4 con persona 1 · **Revisa:** persona 2 · **Depende de:** SARB-017, SARB-021 · **Esfuerzo:** 2 h.

**Aceptación:**
- Se conservan escenario y traza de al menos un rescate eficiente, un caso térmico y un fallo real del desarrollo o de la evaluación.
- Se explica lo observable: bloqueos, rodeos, retorno tardío, destrucción o rescate parcial. No se atribuyen intenciones al robot sin evidencia.
- Se distingue aprender en ciertos edificios conocidos de explorar edificios desconocidos; se declaran los sensores de distancia calculados con mapa completo.
- Se explican el carácter centralizado del control, simplificación térmica, exposición de robots y traslado abstracto de personas.
- Los fallos de prueba se analizan sin volver a ajustar el mismo modelo y seguir llamando independiente a esa prueba.

**Evidencia:** sección de discusión con capturas o trazas reproducibles y propuestas concretas de trabajo futuro.

## 9. Entrega y defensa

<a id="sarb-024"></a>
### SARB-024 — Verificar el flujo completo de la aplicación

**P0 · Responsable:** personas 3 y 2 · **Revisa:** persona 1 · **Depende de:** SARB-011, SARB-012, SARB-013, SARB-014 · **Esfuerzo:** 3 h.

**Aceptación:**
- Flujo completo: seleccionar edificio → colocar personas → validar → guardar → ejecutar → pausar → avanzar → comparar → recuperar el escenario.
- Se comprueban éxito, destrucción, límite, colocación inválida y caso térmico no certificado.
- Cambiar escenario o estrategia durante una preparación no aplica resultados antiguos ni bloquea controles.
- Se verifica resize, tiempos visuales, carga de modelo, importación incorrecta y mensajes de error.
- La suite completa pasa con extras `ui` y `rl`; se agregan pruebas de comportamiento para las nuevas reglas e integraciones, sin usar solo capturas como prueba de corrección.
- No hay errores que impidan mostrar la misión en el computador de presentación.

**Evidencia:** lista de comprobación firmada por dos integrantes y registro de pruebas/capturas.

<a id="sarb-025"></a>
### SARB-025 — Escribir el informe técnico final

**P0 · Responsable:** persona 4 coordina; todos aportan · **Revisa:** persona 1 · **Depende de:** SARB-002, SARB-021, SARB-022, SARB-023 · **Esfuerzo:** 4 h.

**Aceptación:**
- Incluye problema, objetivos, alcance, arquitectura, reglas y formulación de observación, acciones, transición, recompensa y finalización.
- Describe editor, variación de posiciones, viabilidad, datos, particiones, hiperparámetros, semillas y selección de modelos.
- Presenta referencias, métricas, resultados, gráficas, discusión, amenazas a la validez y límites.
- Diferencia requisitos confirmados del profesor, decisiones del equipo y funcionalidades futuras.
- Explica contribución de los cuatro integrantes y cómo reproducir los resultados.
- Todas las cifras apuntan a evidencia versionada; no afirma superioridad térmica, autonomía física o generalización que no se hayan demostrado.
- Usa el formato y extensión confirmados con el profesor; no se supone que un formato particular sea obligatorio.

**Evidencia:** documento final revisado, con fuentes técnicas primarias y enlaces a datos/modelos de la entrega.

<a id="sarb-026"></a>
### SARB-026 — Preparar y ensayar la demostración

**P0 · Responsable:** persona 4 coordina; todos participan · **Revisa:** persona 1 · **Depende de:** SARB-012, SARB-024, SARB-025 · **Esfuerzo:** 3 h.

**Aceptación:**
- Hay un guion ajustado al tiempo confirmado: problema → agente y reglas → ubicación de personas → rescate → comparación → resultados y límites.
- Se demuestra al menos un escenario elegido en vivo; no se sustituye ocultamente por una secuencia programada si falla DQN.
- Hay casos guardados de respaldo que permiten mostrar coordinación y riesgo térmico, además de un video corto o capturas de la versión final.
- Se puede explicar la diferencia entre modelo entrenado y referencias, y por qué menor daño sin rescate no es suficiente.
- Cada integrante puede responder qué observa el agente, qué acciones elige, cómo se aplica el daño, cómo se entrena y cómo se evitó evaluar solo mapas memorizados.
- El ensayo se realiza en el equipo de presentación sin depender de entrenar ni descargar dependencias en vivo.

**Evidencia:** guion, presentación, archivos de respaldo y ensayo completo con tiempos.

<a id="sarb-027"></a>
### SARB-027 — Cerrar la versión reproducible de entrega

**P0 · Responsable:** persona 1 con todo el equipo · **Revisa:** persona 4 · **Depende de:** SARB-001, SARB-003, SARB-019, SARB-024, SARB-025, SARB-026 · **Esfuerzo:** 2 h.

**Aceptación:**
- Todos los cambios de entrega están revisados e integrados en la rama estable acordada; se identifica una versión o etiqueta final.
- Un clon o copia limpia en otro computador instala con el lockfile y ejecuta editor, modelo y referencias siguiendo el README.
- El artefacto seleccionado contiene modelo, configuración, esquema de observación, hashes, evidencia de selección y evaluación final.
- Se conservan datos y scripts necesarios para regenerar gráficas y tablas, sin obligar a guardar todas las cachés o todos los entrenamientos.
- No se incluye un modelo incompatible ni resultados de un checkpoint distinto. Los metadatos de cada CSV coinciden con el modelo publicado.
- README, guía del equipo, informe y presentación describen la versión real; las tareas cerradas tienen evidencia y las extensiones futuras están claramente separadas.

**Evidencia:** hash/etiqueta final, comprobación de instalación limpia, lista de archivos entregados y enlace compartido con el equipo.

## 10. Definición global de terminado

El backlog se considera cerrado cuando las 27 tareas están integradas y sus evidencias están disponibles. La revisión final debe poder responder sí a lo siguiente:

1. ¿Otro integrante puede instalar y abrir el proyecto desde la versión publicada?
2. ¿El profesor puede ubicar dos personas y comprender validación, rescate y finalización?
3. ¿Las cuatro estrategias se ejecutan sobre el mismo caso y se puede repetir la comparación?
4. ¿El controlador fue entrenado con ubicaciones variadas y se eligió sin mirar prueba final?
5. ¿Hay varias semillas, configuraciones reservadas y resultados medidos, incluidos fallos?
6. ¿Las conclusiones distinguen éxito, daño, duración y los límites de la evidencia?
7. ¿La demostración y el informe corresponden al modelo y código realmente entregados?
8. ¿Los cuatro integrantes pueden explicar y defender el trabajo?

Cerrar el backlog produce una entrega completa y defendible. La calidad del aprendizaje y las conclusiones se juzgan con los datos obtenidos; no se garantiza que DQN gane siempre ni se sustituye la rúbrica del profesor.
