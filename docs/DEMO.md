# Demostración de la versión final

Versión del 26 de noviembre de 2026. Preparada para una exposición de 5–10 minutos; la duración es una elección del equipo. El guion utiliza resultados reales y un ejemplo conocido de validación.

## Antes de presentar

1. Instalar con `uv sync --locked --extra ui --extra rl --python 3.12` y abrir `run.bat`.
2. Conservar localmente el repositorio completo, el modelo incluido y las figuras de `results/final/figures/`. No se necesita descargar un modelo ni entrenar durante la exposición.
3. Probar los dos comandos de respaldo de abajo. Cerrar otras ventanas de SAR-Bot que estén usando la misma sesión de aprendizaje.
4. Abrir `results/final/figures/tablas.md` y este guion. La prueba automatizada del equipo se documenta en [VERSION_FINAL.md](VERSION_FINAL.md); no sustituye un ensayo oral del grupo.

## Guion sugerido

| Bloque | Tiempo | Qué explicar y mostrar |
|---|---:|---|
| Problema | 45 s | Dos robots deben entregar tres personas; cada uno carga una. Paredes, coordinación y exposición al calor producen decisiones con consecuencias. |
| Motor y agente | 60 s | Temperatura × tiempo de exposición; un paso aplica daño a ambos robots. Una red DQN centralizada recibe 390 valores y decide una de 25 acciones conjuntas. |
| Editor y rescate fiable | 2 min | Con la referencia térmica, editar las tres posiciones en el edificio preparado, validar, preparar y reproducir. Mostrar pausa, un paso, temperatura e integridad. Si no hay certificado, explicar el aviso y elegir posiciones verificables. |
| Política aprendida | 90 s | Abrir el ejemplo conocido DQN. Mostrar sus tres entregas y aclarar que este caso se usó en validación; no representa posiciones nuevas. |
| Aprendizaje persistente | 90 s | En DQN, activar «Aprender», completar una misión y esperar el mensaje de guardado. Mostrar misiones, recuerdos y actualizaciones; abrir otra ejecución y recuperar los contadores. Puede fallar el rescate y aun así aportar experiencia. |
| Comparación y resultados | 2 min | Comparar las cuatro estrategias sobre exactamente el mismo caso. Mostrar la tabla de prueba: DQN 0/40, corta 33/40, térmica 40/40; explicar límites y mejoras futuras. |

Para cinco minutos, reducir el editor a una posición, mostrar la persistencia ya comprobada y dar prioridad a las diferencias entre estrategia programada, red entrenada y resultado medido. Los integrantes pueden repartirse problema, motor/aprendizaje, interfaz y resultados; ya no hay trabajo técnico pendiente por roles para esta versión.

## Comandos de respaldo

Desde la raíz del repositorio:

```powershell
# Edificio grande con la referencia térmica: 3 entregas, 66 pasos, daño 42.
.\run.bat

# DQN: caso conocido de validación; 3 entregas, 126 pasos, daño 0.
.\run.bat --scenario scenarios/demo_final.json --strategy dqn

# Aprendizaje: caso de entrenamiento; no se garantiza completar el rescate.
.\run.bat --scenario scenarios/partitions/v2_12x12/training/hub_training_01_easy.json --strategy dqn --learn
```

La velocidad inicial es de seis pasos visuales por segundo, modificable en la interfaz; no cambia la temperatura, las recompensas ni el daño por turno. Las cifras de respaldo corresponden a **Evaluar sin aprender**, usando `artifacts/final/model.zip`. Una sesión aprendida puede comportarse de otra manera.

## Mejora de uso posterior a la entrega congelada

En `main`, los selectores muestran **Mapa del edificio** y las cuatro estrategias con sus explicaciones. DQN ofrece dos botones: **Solo ejecutar** y **Aprender**. Las otras estrategias ocultan las opciones de entrenamiento. La comparación usa **Ver recorrido** para reproducir cada fila.

La actualización candidata se comprueba contra los pesos anteriores sobre controles de entrenamiento. Si empeora, se conservan esos pesos y se guarda la memoria. Las cifras históricas de regresión de la sección siguiente corresponden al mecanismo anterior, sin esta protección; se conservan como evidencia de por qué se añadió. [Comprobación de la protección](../results/online_guard/check.json).

## Qué ocurre al aprender

La misión se prepara en segundo plano con la política de sesión y exploración del 10 %. Reproducirla muestra decisiones reales ya calculadas; al llegar a su final se verifican sus transiciones, se añaden a la memoria y se actualiza la red. El trabajo y el guardado ocurren fuera del hilo de dibujo. No aprende en cada fotograma ni al rebobinar. «Preparar nueva misión» crea una misión nueva; reiniciar reproduce la existente y evita duplicar su aprendizaje.

Se conserva una sesión por perfil y modelo base en `outputs/learning_sessions/`. Incluye replay de hasta 4096 transiciones, pesos, optimizador, estados aleatorios y contadores. Al cerrar durante el guardado, la aplicación espera a que termine. Una copia anterior permite recuperar un guardado dañado. Cambiar a evaluación o comparar utiliza el **modelo base congelado**, para mantener las cifras reproducibles.

Comprobación realizada: dos procesos separados acumularon dos misiones, 580 transiciones y 128 actualizaciones; cambiaron los parámetros Q y el archivo base conservó su hash. [Evidencia](../results/online/persistence.json). Esto demuestra persistencia y actualización, no mejora garantizada.

## Resultados y explicación de límites

- La referencia térmica resuelve los 40 casos de prueba. La ruta corta resuelve 33. En los **33 éxitos comunes**, la térmica añade 2,9 pasos y reduce 24 puntos de daño en promedio.
- DQN completa 3/20 casos de validación y 0/40 de prueba: aprende comportamientos parciales y falla al cambiar las posiciones. No presentar el ejemplo elegido como rendimiento general.
- Solo hay una semilla de entrenamiento DQN; las seis configuraciones probadas no son seis réplicas independientes. Los casos fueron certificados por referencias y favorecen esos planificadores.
- La simulación conoce el mapa completo y usa calor estático. La máscara que impide ciertas colisiones es programada; la red aprende preferencias entre acciones permitidas.
- Tras ver prueba no se cambió el checkpoint. El aprendizaje local está separado y su comparación posterior usa validación, nunca el conjunto reservado.

## Si algo falla en vivo

Mostrar el fallo y sus métricas. Para una ejecución fiable, volver a evaluar con la referencia térmica y posiciones certificadas. Si no abre la ventana, usar las capturas versionadas `docs/images/final-default.png`, `final-dqn-demo.png` y `learning-persistence.png`, aclarando que son respaldos de ejecuciones automatizadas. Las tablas y trazas originales permiten revisar los resultados sin la interfaz.

No se necesita volver a entrenar, ejecutar otra prueba final ni cambiar parámetros para presentar esta versión.
