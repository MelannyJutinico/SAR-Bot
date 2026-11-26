# Interfaz de SAR-Bot

## Simplificación de uso y protección de aprendizaje

Comprobación final: **321 pruebas aprobadas** en 247,237 segundos. [Registro](../results/online_guard/verification.json).

La interfaz actual de `main` reemplaza las etiquetas técnicas de la primera entrega:

| Opción | Para qué sirve |
|---|---|
| Mapa del edificio | Elegir un mapa preparado; no significa mapa de entrenamiento. Muestra su tamaño y cantidad de personas. |
| Colocar personas | Editar las tres posiciones antes de preparar la misión. |
| Red neuronal (DQN) | Decisiones aprendidas con recompensas; es experimental y puede fallar. |
| Ruta corta | Planificar priorizando distancia, sin considerar daño por calor. |
| Ruta segura (calor) | Planificar considerando distancia y daño térmico; no garantiza resolver cualquier caso. |
| Movimientos al azar | Control básico sin planificación ni entrenamiento. |
| Solo ejecutar / Aprender | Opciones exclusivas de DQN. La primera usa el modelo base; la segunda recupera la sesión y aprende de nuevas misiones. |
| Elegir red neuronal | Mostrar únicamente redes compatibles. La red en uso aparece resaltada. Los modelos de otros tamaños se ocultan. |
| Comparar las 4 estrategias | Ejecutar todas sobre el mismo mapa y posiciones iniciales. Comparar primero entregas y finalización. |
| Ver recorrido | Reproducir el resultado de una fila; no entrena ni cambia la estrategia seleccionada para una misión nueva. |

[Captura de las opciones DQN](images/interface-dqn.png) · [Captura de la comparación](images/interface-comparison.png).

Las dos opciones de DQN están visibles simultáneamente, con la activa resaltada. No se muestran controles de redes ni de entrenamiento para las estrategias programadas. Los selectores tienen flecha y explicaciones; la navegación de modelos aparece únicamente si hay más de una página.

Al terminar una misión de aprendizaje se comprueba una actualización candidata sobre seis casos fijos de **entrenamiento**, uno por edificio y dificultad, y sobre la misión recién terminada si no está ya incluida. Se comparan misiones completas, entregas y retorno en ese orden. Si la puntuación agregada cae, se recuperan red, red objetivo y optimizador anteriores. La experiencia, identidad de misión, memoria y contadores de intentos se conservan. Un error al comprobar también conserva los pesos anteriores.

Esto reduce regresiones detectables en esos controles; no garantiza generalización ni que cada caso individual mejore. No usa validación o prueba reservada para esta decisión. La comprobación ocurre en segundo plano y se explica en el aviso de guardado. Los controles no se usan para calcular gradientes.

Prueba real: 64 actualizaciones candidatas redujeron las entregas de 5 a 0 en los controles. Se rechazaron; los parámetros Q finales fueron idénticos a los originales, se guardaron 280 experiencias y el modelo congelado permaneció intacto. [Evidencia](../results/online_guard/check.json).

Las secciones siguientes describen el estado de la primera entrega y el historial. Donde usen etiquetas anteriores, prevalecen los nombres de esta tabla.


## Versión final — 26 de noviembre de 2026

`run.bat` abre el edificio de coordinación 12 × 12 con la referencia térmica, en pausa. El modelo predeterminado es `artifacts/final/model.zip` y el catálogo lo identifica como **congelado / una semilla**. DQN es experimental: 3/20 misiones completas en validación y 0/40 en prueba.

**Preparación:** elegir plantilla, estrategia y modelo compatible; editar tres personas, validar, guardar/cargar escenarios personalizados y preparar una misión. **Ejecución:** iniciar, pausar, avanzar un paso, reiniciar la reproducción y cambiar velocidad. **Análisis:** comparar estrategias en el mismo escenario, consultar historial, exportar y reproducir trazas.

Con DQN se habilita **Modo: Aprender y guardar**. Al finalizar una misión nueva, se actualiza la red en segundo plano y aparece un aviso con misiones, recuerdos y actualizaciones. Esperar a ese aviso antes de preparar otra. Al reiniciar el programa y activar de nuevo aprendizaje se recupera la sesión. Reiniciar la reproducción o consultar historial no repite el entrenamiento. Evaluar y comparar usan el modelo base congelado.

La sesión local conserva modelo, optimizador, replay y contadores en `outputs/learning_sessions/`; no altera el artefacto publicado. Las acciones que cambian la configuración quedan bloqueadas durante el guardado. Aprender puede empeorar el comportamiento: el informe registra la regresión observada. [Guion y respaldo](DEMO.md), [informe](INFORME.md).

![Interfaz final](images/final-default.png)

## Historial de implementación y auditorías

Los estados fechados de las secciones siguientes documentan versiones anteriores; las ausencias de checkpoint 12 × 12 o de modo persistente ya están resueltas.

Estado de estabilizacion: 2026-11-18. Alcance: SARB-010, SARB-011, SARB-012,
SARB-030, SARB-014, SARB-013 y SARB-032. Implementacion local lista para revision
tecnica cuando pasen las verificaciones indicadas al final. No equivale a cerrar
las revisiones humanas ni las actividades compartidas del backlog.

## Ejecutar

Desde la raiz del repositorio, con Python 3.12 y las dependencias del lockfile:

```powershell
uv run --locked --extra ui --extra rl python scripts/ui.py
uv run --locked --extra ui --extra rl python scripts/ui.py --scenario scenarios/v2/warmup_10x10.json --strategy shortest
uv run --locked --extra ui --extra rl python scripts/ui.py --scenario scenarios/v2/warmup_10x10.json --strategy dqn --model artifacts/v2_pilot/model.zip
```

El inicio predeterminado usa el pasillo V1 y su checkpoint con sensores. El
selector permite plantillas del primer nivel de scenarios y de scenarios/v2;
excluye curriculum, validation y test. Una ruta CLI explicita puede agregar otra
entrada, pero no convierte un conjunto reservado en datos de demostracion.
Los modelos publicados actuales son pilotos/de desarrollo. No hay un modelo
12x12 compatible; se explica su ausencia y no se sustituye la estrategia.

## Flujo y vistas

Preparacion: selecciona escenario, estrategia y modelo; abre el editor o la
biblioteca personal y pulsa Validar y preparar. Ejecucion: reproduce la traza
calculada con iniciar/continuar, pausa, un paso, reinicio y velocidad 1 a 12.
Analisis: consulta el ultimo resultado individual, la comparacion o el historial.
Cambiar de vista pausa la reproduccion y no vuelve a ejecutar una politica.

Atajos durante reproduccion: ESPACIO pausa/continua, N un paso, R reinicia,
H mapa de calor, T recorridos, + y - velocidad. En el editor, 1/2/3 seleccionan
persona. ESC cierra selectores. La ventana es redimensionable y conserva la
misma transformacion para dibujar y recibir clics, incluidos los margenes.
Se verifican 1280x860, 800x600 y 1600x900; el texto se reduce en ventanas pequenas
por escalado, por lo que falta validar legibilidad con otro integrante.

## Editor visual y preparacion (SARB-010 / SARB-011)

Editar personas crea un borrador separado para plantillas de tres personas.
Selecciona Persona 1, 2 o 3 y haz clic en una celda. Puedes limpiar o restaurar
las posiciones de la plantilla; se indica cuantas faltan. No se editan paredes,
base ni fuego. Los errores de ubicacion se explican y conservan el borrador.

ScenarioDraft.build usa Scenario.with_victims; las reglas y la conectividad se
validan exclusivamente en el nucleo. Validar y preparar ejecuta exactamente ese
Scenario inmutable, sin archivos temporales ni modificaciones de la plantilla.
Cambiar de estrategia conserva las posiciones aplicadas y prepara desde cero,
con integridad, carga y contadores iniciales. Volver a mision conserva el borrador
sin aplicarlo: para ejecutarlo debes confirmar Validar y preparar en el editor.

Coordenadas internas (x,y), origen arriba a la izquierda; A1 representa (0,0).
Los IDs internos de personas empiezan en cero y las etiquetas visuales en uno.
scenario_id agrupa el caso fisico; configuration_id conserva ademas el orden de
las personas. Una generacion distingue solicitudes repetidas del mismo caso.
La preparacion y certificacion se ejecutan fuera de Pygame. Los resultados solo
se aplican si coinciden generacion, identidad exacta, estrategia y modelo.
Editar o cambiar configuracion invalida resultados previos; Future.cancel es
solo una optimizacion y no la proteccion principal contra resultados obsoletos.

La viabilidad distingue structural_invalid, certified y not_certified. Un caso
no certificado permite explorar y no se presenta como imposible. Un certificado
pertenece a la referencia y no garantiza que DQN rescate posiciones nuevas.

## Biblioteca personal (SARB-012)

Guardar y Cargar personal usan outputs/custom_scenarios. El nombre es el prefijo
de configuration_id; el JSON contiene el identificador completo y conserva
personas ordenadas, geometria, temperatura y limite temporal con Scenario.to_dict.
Cargar valida el archivo, conserva el estado anterior ante error y abre el editor;
confirma Validar y preparar para ejecutar la nueva configuracion desde cero.
Para importar un JSON externo, copialo a ese directorio y seleccionalo en la lista.
No se escriben datos en conjuntos de entrenamiento, validacion ni prueba.

La lista, carga y guardado usan un trabajador separado. Token y contexto impiden
que una lectura obsoleta cambie un borrador nuevo. La confirmacion identifica el
archivo o explica el error. Guardar dos veces no sobrescribe la configuracion.

## Catalogo DQN y mensajes (SARB-030 / SARB-014)

Seleccionar modelo DQN descubre artifacts/*/model.zip y el archivo de --model.
Comprueba metadata.json, escenarios de entrenamiento de perfiles historicos y
la cabecera JSON del ZIP sin deserializar pesos. Muestra dimensiones, personas,
modo/tamano de observacion, esquema, arquitectura, ruta mediante su registro y
estado piloto. La API publica RescueEnv.observation_size determina el perfil;
el cargador DQN mantiene su validacion final al preparar una mision.

Se rechazan metadatos ausentes o contradictorios, esquemas desconocidos, ZIP
corruptos, cifrados o con compresion no soportada. Otros modelos validos siguen
disponibles. No se capturan indiscriminadamente errores de programacion.
El catalogo se descubre al iniciar: reinicia la aplicacion si incorporas modelos.
Compatibilidad tecnica no implica validacion experimental ni garantia de exito.

El tablero identifica robots, personas, base, obstaculos y calor con numeros,
etiquetas e iconos ademas del color. Recogida significa que un robot transporta
una persona; el contador de rescates aumenta al entregarla en base. Exito,
destruccion y limite temporal son resultados diferentes. El dano proviene del
motor y depende de pasos globales, nunca de la velocidad de la reproduccion.

## Comparaciones conservadas (SARB-013 / SARB-030)

Comparar estrategias congela una copia validada de la configuracion aplicada y
prepara DQN, ruta corta, ruta termica y aleatoria con las mismas condiciones.
La tabla muestra rescates, finalizacion, pasos, dano, semilla y modelo. Pendiente,
completada, error y no disponible son estados del calculo: una fila completada
puede contener una mision fracasada. DQN incompatible no se reemplaza por otra
politica. No se elige un ganador ni se considera mejor un fracaso por menor dano.

La solicitud en curso es independiente de la ultima comparacion completada.
Al completar las cuatro filas se conserva una instantanea inmutable, incluidos
errores e incompatibilidades. Preparar o editar otra mision invalida trabajadores
pendientes, pero no borra esa instantanea ni el ultimo resultado individual.
Analisis permite consultar Ver comparacion; si corresponde a otro escenario se
muestran sus IDs originales y el aviso Configuracion anterior. Mientras hay un
calculo nuevo puedes alternar entre este y Ver ultima completa. Solo se conserva
una comparacion completada; la siguiente completa la reemplaza. No se reconstruyen
filas desde el historial ni se mezclan configuraciones.

Reproducir selecciona una traza calculada desde cero sin invocar la politica.
Los mensajes de otra preparacion se limpian; la reproduccion no atribuye una
certificacion nueva ni sobrescribe el resultado individual. Las tareas obsoletas
no pueden restaurar errores o resultados descartados.

Exportar CSV se habilita al completar las filas. Un trabajador escribe una
instantanea inmutable en outputs/comparisons, con nombre unico. La interfaz
sigue operativa. Si cambia el escenario o la vista, el archivo que ya se estaba
escribiendo puede finalizar, pero no se aplica una confirmacion a otro contexto.
Los campos siguen siendo: scenario_id, configuration_id, strategy, model, seed,
status, rescued, outcome, steps, damage_total, error y scenario_json completo.
No se han agregado columnas experimentales ni cambiado el esquema de Persona 4.

## Historial, eventos y reproduccion (SARB-032)

Historial, accesible desde Analisis o comparaciones, registra la mision individual
cuando alcanza su final visual y cada fila de comparacion al terminar su calculo.
Filas incompatibles o sin episodio no se convierten en misiones ficticias.
Selecciona un registro para consultar escenario, IDs, estrategia/modelo, semilla,
metricas, eventos y estados/acciones paso a paso. La reproduccion no vuelve a
registrarlo. Dos ejecuciones nuevas pueden tener trazas identicas y UUID distintos.

Los eventos se derivan de pares de estados: movimiento por cambio de posicion,
recogida por cambio de carga, entrega por incorporacion a rescued, dano por su
delta real y destruccion por integridad que llega a cero. Inicio, rescate completo
y finalizacion se registran cuando corresponde. No se inventan intenciones ni
razones internas de la politica. Contadores y eventos se comprueban en pruebas.

Reproducir desde cero usa Playback con los estados y acciones almacenados:
no ejecuta motor, decisiones ni entrenamiento. Mantiene pausa, paso y reinicio.
Volver a Analisis conserva registro y comparacion; volver a Preparacion muestra
el estado inicial de su configuracion actual.

Exportar seleccion crea JSON sar-bot-ui-trace version 1 en outputs/mission_traces.
Incluye escenario schema 2 completo, IDs, estrategia, ruta de modelo, semilla de
solicitud, acciones, estados, metricas, eventos, version de Python y SHA-256 del
documento canonico. Episode registra el hash real de core/simulation.py durante
la preparacion. Para DQN registra el hash del checkpoint antes de cargarlo y
comprueba que no cambie hasta finalizar. Valores desconocidos permanecen null;
no se inventan semillas de entrenamiento o generacion. seed gobierna las acciones
de RandomPolicy y no demuestra procedencia del entrenamiento.

Importar traza lista trace-*.json del directorio local. La lectura, validacion y
reconstruccion ocurren fuera de Pygame. Se comprueban version, checksum, escenario,
IDs y limites; se ejecutan las acciones registradas en un motor nuevo para
verificar que los estados, eventos y metricas coinciden, sin invocar politicas.
La reproduccion posterior solo selecciona los estados verificados. No requiere
el checkpoint original para visualizar. Archivos corruptos o de otro motor se
rechazan conservando seleccion y resultados anteriores.

El hash de fuente exige coincidencia exacta del motor, incluso ante cambios no
funcionales; no se migran trazas de otras versiones. El checksum verifica integridad,
no autoria ni procedencia del modelo declarado en una importacion.

## Limites de recursos y persistencia local

Las entradas de Persona 3 limitan JSON a 16 MiB antes de leerlos, lados a 24 celdas,
personas a tres y max_steps a 4999 (5000 estados incluido el inicial). Estas son
restricciones de representacion/registro, no reglas nuevas del motor. Todos los
escenarios oficiales actuales se aceptan: el mayor es 12x12 y usa 300 pasos.
Se conserva el estado previo si una importacion excede los limites.

El historial mantiene 20 registros y 10000 estados agregados, expulsando primero
el mas antiguo. La seleccion puede retener adicionalmente un registro. Hay hasta
16 registros pendientes; superar el limite informa un rechazo. Las trazas de
comparacion reutilizan Episode y no duplican sus estados al conservar resultados.
Los episodios activos y la ultima comparacion tambien ocupan memoria, acotada
por los limites de entrada. La planificacion publica puede no ser interrumpible
durante una llamada; su resultado obsoleto nunca se aplica a otra solicitud.

Escenarios, trazas y CSV locales se escriben en un temporal del mismo directorio,
se vacian con flush/fsync y se validan antes de publicarse mediante os.link.
El enlace publica un archivo completo sin reemplazar destinos existentes. La
copia temporal propia se elimina al terminar o ante errores controlados. Si el
sistema de archivos no soporta enlaces duros, la operacion falla con mensaje y
sin sobrescritura; no se degrada a una escritura insegura. Se verifica en NTFS/Windows.
No se promete durabilidad frente a perdida fisica de energia del dispositivo.
Una terminacion abrupta puede dejar .sarbot-*.tmp propios sin publicar: no aparecen
en las listas y no se borran automaticamente archivos de otras sesiones o usuarios.

No hay autoguardado del historial ni limpieza automatica de exportaciones.
Exporta antes de cerrar para conservar sesiones. Los resultados completos de
comparacion se conservan en memoria mientras vive la aplicacion; sus CSV pueden
inspeccionarse externamente, no hay importador de comparaciones CSV.

## Verificacion y revisiones pendientes

```powershell
uv run --locked --extra ui --extra rl python -m unittest discover -s tests -p test_stabilization.py -v
uv run --locked --extra ui --extra rl python -m unittest discover -s tests -v
uv run --locked --extra ui --extra rl python scripts/ui.py --headless --strategy shortest --scenario scenarios/demo.json --steps 1 --screenshot outputs/ui-check.png
```

Headless sin episodio preparado devuelve codigo 2 y JSON de error en stderr con
la causa original e IDs; no llama a step ni genera una captura engañosa. Un
escenario valido conserva salida 0, captura y metricas. Ejemplo esperado de
incompatibilidad: --scenario scenarios/v2/coordination_hub_12x12.json --strategy
dqn --headless --steps 1, mientras no exista un checkpoint compatible seleccionado.

La verificacion automatizada no sustituye la revision humana. Pendientes:
Persona 2 para SARB-010/011/012, intercambio real entre equipos de SARB-012,
Persona 4 para claridad de SARB-014 y coordinacion de SARB-013/032, Persona 1
para SARB-030/013/032. El computador de presentacion requiere comprobacion humana.
Los formatos locales NO estan homologados con SARB-020. Persona 4 debe acordar
particiones, procedencia de semillas, hashes y correspondencia de campos.
SARB-034 espera el contrato publico de sesiones SARB-033 de Persona 1; no se
implementa aprendizaje persistente ni se sustituye por un servicio propio.
SARB-024 sigue siendo una integracion compartida pendiente, no cerrada por esta
suite ni por recorridos automatizados. No se modifican esquemas experimentales,
politicas, checkpoints, dependencias ni reglas de Persona 2.

### Evidencia de estabilizacion

- Pruebas focalizadas: 18 aprobadas en tests/test_stabilization.py.
- Suite completa: 200 aprobadas, cero fallos y cero omisiones, 49.418 s.
- Recorrido Windows: 941 fotogramas en las tres resoluciones, con clics de
  edicion, guardado/carga, ejecucion, comparacion, exportacion pendiente,
  nueva preparacion, consulta de la comparacion anterior e historial/reproduccion.
- Punto de entrada scripts/ui.py: 140 fotogramas adicionales, salida 0, con un
  ZIP cifrado temporal; el catalogo muestra el rechazo y conserva el piloto valido.
- Capturas fisicas y registros locales: outputs/persona3-stable-0ab41186/.
  Se inspeccionaron comparaciones anteriores, reproduccion tras incompatibilidad
  y catalogos valido/invalido, sin controles superpuestos. Son evidencias de
  desarrollo ignoradas por Git; no deben incorporarse como resultados experimentales.
- git diff --check aprobado. La comparacion local usa
  refs/remotes/origin/feature/simulation-core, que apunta al mismo HEAD base
  df029d72f42c5f7dc8320d0a6d93d1a25eb2a657. No se actualizaron referencias remotas:
  confirmar vigencia de GitHub queda fuera de esta comprobacion local.

La rama queda tecnicamente preparada para revision de los cambios de Persona 3.
No se han creado commits, pushes ni Pull Request. Las aceptaciones humanas y
las dependencias externas enumeradas arriba siguen pendientes.

### Auditoria funcional integral posterior

La ultima auditoria se conserva en outputs/persona3-functional-552ceef0/:
AUDITORIA_FUNCIONAL.md, functional_plan.csv, functional_matrix.csv,
functional_interactions.csv, strategy_matrix.csv, missions.json y capturas.
Son evidencias locales de desarrollo, ignoradas por Git y ajenas a SARB-020.

Se ejecutaron todas las siete plantillas del menu con las cuatro estrategias:
26 episodios reales y dos rechazos esperados de DQN en 12x12. Se repitio Aleatoria
con semilla 0 y coincidieron exactamente acciones y estados. Las particiones
reservadas no se usaron como escenarios repetidos de demostracion.

El escenario 10x10 con sensors_dqn es una incompatibilidad conocida: ese modelo
requiere 6x6/dos personas, sensores con 157 entradas y 25 acciones. v2_pilot
requiere 10x10/tres personas, schema 2 y sensores con 302 entradas. Se selecciona
explicitamente en el catalogo; no hay un checkpoint publicado 12x12. La UI ahora
distingue MODELO INCOMPATIBLE, DQN NO DISPONIBLE y MODELO INVALIDO del ERROR DE
CARGA inesperado, sin cambiar outcome del motor ni sustituir politicas.
El piloto 10x10 completa warmup, pero en building_10x10 agota 240 pasos con cero
rescates. Es una limitacion del aprendizaje, no un defecto de carga ni del motor.

Resultados reales de tres personas (rescates/pasos/dano):

| Plantilla | DQN compatible | Ruta corta | Ruta termica | Aleatoria, semilla 0 |
|---|---|---|---|---|
| warmup_10x10 | Exito 3/6/0 | Exito 3/6/0 | Exito 3/6/0 | Limite 2/80/0 |
| building_10x10 | Limite 0/240/0 | Exito 3/58/107 | Exito 3/62/64 | Destruccion 0/123/104 |
| coordination_hub_12x12 | No disponible | Exito 3/58/63 | Exito 3/66/42 | Destruccion 0/160/110 |
| thermal_detour_12x12 | No disponible | Destruccion 2/44/188 | Exito 3/60/2 | Destruccion 0/102/100 |

El fracaso de una politica es un resultado valido y no selecciona ganadores.
Se reprodujeron las observaciones manuales: dano 23 en paso 11 de building,
dano 10 con dos personas recogidas en paso 12 de coordination, y destruccion
con dano 188 en paso 44 de thermal_detour.

Se accionaron botones y atajos mediante eventos de raton y teclado Windows:
editor, intercambio, validacion, pausa/paso/reinicio, velocidad, capas, vistas,
catalogo/paginacion, biblioteca/paginacion, comparacion, CSV, historial/eventos,
JSON e importacion corrupta/incompatible. Se verificaron estados previos y
conservacion de resultados; el registro diferencia controles deshabilitados y
operaciones que no aplican. Las inyecciones de permisos denegados se identifican
como fallos controlados, no como desempeno real de DQN.

Mejoras propias: botones deshabilitados no despachan clics; el texto secundario
alcanza contraste >=7:1 en paneles y las temperaturas >=4.5:1 en la paleta termica
25..160. wrap divide tokens largos para evitar que rutas desborden el panel, y
los errores de modelo ausente/permisos se presentan sin volcar rutas extensas.
No se afirma conformidad integral de accesibilidad: legibilidad subjetiva en
800x600 y revision humana siguen pendientes.

Ultima suite: 207 pruebas aprobadas, cero fallos y cero omisiones, 27.203 s;
25 pruebas focalizadas de estabilizacion, siete regresiones mas que las 200
anteriores. Registro limpio: suite-final-207.log. El recorrido principal exitoso
comprende 5829 fotogramas con ventanas 1280x860, 800x600 y 1600x900; se agregaron
pruebas suplementarias y 530 fotogramas del punto de entrada scripts/ui.py.
El contador agregado del auxiliar incluye esperas/reintentos y no se usa para
inflar misiones verificadas. Los apuntes del banco estan en harness_notes.txt.
Tres episodios reales de 5000 estados comprobaron que se retienen como maximo
10000 estados. Los hashes de modelos, escenarios, nucleo, politicas, recompensas,
configuraciones y dependencias se mantuvieron sin cambios.

LISTA TECNICAMENTE PARA PREPARAR EL PR; se conservan las revisiones humanas y
las dependencias SARB-020/033/034/024 pendientes. Sin commits, pushes ni PR.
