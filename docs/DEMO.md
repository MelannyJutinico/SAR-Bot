# Guion y respaldo de la demostración (SARB-026)

**Coordina:** persona 4; participan todos. **Revisa:** persona 1. **Versión:** borrador del 18 de noviembre de 2026.

**Estado:** guion preparado y casos de respaldo listos. Falta confirmar la duración con el profesor (SARB-002), tener los modelos 12 × 12 congelados (SARB-019), el modo de aprendizaje continuo (SARB-033 y SARB-034) y hacer el ensayo en el equipo de presentación. Mientras tanto se usan 10 minutos como supuesto, con una versión corta de 5.

## 1. Guion

| Bloque | 10 min | 5 min | Quién | Qué se muestra |
|---|---:|---:|---|---|
| Problema | 1:00 | 0:30 | Persona 4 | Dos robots, tres personas, un edificio con calor. El objetivo es rescatar a todos, con pocos pasos y poco daño. |
| Agente y reglas | 1:30 | 1:00 | Persona 1 | Control centralizado de 25 acciones conjuntas, observación, daño por temperatura y tiempo, y recompensas (sección 4) |
| Ubicación de personas | 1:30 | 0:45 | Persona 3 | Editor: elegir edificio, colocar las tres personas con clics y pulsar «Validar y preparar». Explicar «certificado» frente a «no certificado». |
| Rescate | 2:00 | 1:00 | Persona 3 | Ejecutar la misión con pausa, un paso y velocidad. Señalar las recogidas, las entregas, el segundo viaje y el daño en las tarjetas de robots. |
| Comparación | 2:00 | 1:00 | Persona 2 | «Comparar estrategias» sobre el mismo caso: DQN, ruta corta, térmica y aleatoria. Leer primero el éxito y después pasos y daño. |
| Resultados y límites | 2:00 | 0:45 | Persona 4 | Figuras de `results/final/figuras` (SARB-021 y SARB-022) o, mientras no existan, las de validación. Sesgo de certificación, edificios conocidos, simplificación térmica y fallos reales. |

Reglas del guion:

- **El caso en vivo es real.** Si DQN falla en vivo, se muestra el fallo, se abre «Analisis» → «Historial» para ver lo que pasó y luego se comparan las referencias. No se sustituye por una secuencia programada sin decirlo.
- **Primero el rescate completo.** Una misión fallida con poco daño no es mejor. La interfaz no elige ganador, y se explica así.
- **No se usa la partición de prueba para elegir qué mostrar.** La semilla DQN de la demostración se elige con la validación (`docs/PARTICIONES_V2.md`). Si el profesor coloca personas en vivo, ese caso es nuevo para todos los modelos.

## 2. Casos de respaldo

Se cargan desde la línea de comandos con `--scenario`, porque el selector solo lista `scenarios/` y `scenarios/v2/`. Las cifras esperadas salen de los CSV conservados y se reproducen en cualquier equipo con la instalación del lockfile.

| Caso | Archivo | Qué muestra | Resultado esperado | Fuente |
|---|---|---|---|---|
| Rodeo térmico en 12 × 12 | `scenarios/partitions/v2_12x12/training/detour_training_14_intermediate.json` | La ruta corta cruza el corredor caliente y pierde un robot; la térmica rodea | Corta: robot destruido en el paso 45, 2/3 personas, daño 190. Térmica: 3/3 en 66 pasos, daño 0 | `results/sarb031/v2_12x12_training_referencias.csv` |
| Caso exigente en 10 × 10 | `scenarios/development/v2_10x10/building10_dev_03_demanding.json` | Personas lejanas y calor en el camino | Corta: destruido en el paso 62, 2/3, daño 135. Térmica: 3/3 en 60 pasos, daño 58 | `results/sarb031/v2_10x10_desarrollo.csv` |
| Distancia contra calor, ambas con éxito | `scenarios/v2/building_10x10.json` | La térmica tarda 4 pasos más y recibe 43 puntos menos | Térmica: 3/3, 62 pasos, daño 64. Corta: 3/3, 58 pasos, daño 107 | `docs/INSTALACION_EQUIPOS.md` |
| DQN que sí resuelve | `scenarios/v2/warmup_10x10.json` con `artifacts/v2_pilot/model.zip` | Política aprendida en un caso de su entrenamiento | 3/3 en 6 pasos, daño 0 | `results/sarb020/v2_10x10_piloto_desarrollo.csv` |
| DQN histórico 6 × 6 | `scenarios/pasillo_compartido.json` (inicio predeterminado) | Coordinación en un pasillo compartido | 2/2 en 22 pasos, daño 0 | `docs/INSTALACION_EQUIPOS.md` |
| Límite del aprendizaje | Cualquier caso de `scenarios/development/v2_10x10/` con `v2_pilot` | Una política entrenada con posiciones fijas no resuelve posiciones nuevas | Límite de 240 pasos sin completar; muchos movimientos bloqueados | `docs/ESTUDIO_ESCALA.md`, sección 3 |

```powershell
uv run --locked --extra ui --extra rl python scripts/ui.py --scenario scenarios/partitions/v2_12x12/training/detour_training_14_intermediate.json --strategy thermal
uv run --locked --extra ui --extra rl python scripts/ui.py --scenario scenarios/development/v2_10x10/building10_dev_03_demanding.json --strategy shortest
uv run --locked --extra ui --extra rl python scripts/ui.py --scenario scenarios/v2/warmup_10x10.json --strategy dqn --model artifacts/v2_pilot/model.zip
```

El primer caso pertenece a la partición de entrenamiento. Sirve para mostrar las referencias, pero no para presentar a DQN como generalización, porque los modelos finales lo habrán visto al entrenar.

### Capturas de la versión actual

Las capturas de `docs/demo/` se generaron sin ventana con `scripts/ui.py --headless`, en el último paso de cada misión. Se vuelven a generar con la versión final.

| Captura | Estado |
|---|---|
| [`respaldo_12x12_desvio_corta.png`](demo/respaldo_12x12_desvio_corta.png) | Robot 1 destruido en el corredor de 72 °C cargando a la persona 3 |
| [`respaldo_12x12_desvio_termica.png`](demo/respaldo_12x12_desvio_termica.png) | Rescate completo sin daño |
| [`respaldo_10x10_exigente_corta.png`](demo/respaldo_10x10_exigente_corta.png) | Robot destruido, 2/3 personas |
| [`respaldo_10x10_exigente_termica.png`](demo/respaldo_10x10_exigente_termica.png) | Rescate completo |
| [`respaldo_10x10_plantilla_termica.png`](demo/respaldo_10x10_plantilla_termica.png) | Plantilla 10 × 10 con la térmica |
| [`respaldo_10x10_calentamiento_dqn.png`](demo/respaldo_10x10_calentamiento_dqn.png) | DQN piloto en el calentamiento |

Falta grabar un video corto con la versión final. Se graba durante el ensayo, con la misma secuencia del guion.

## 3. Preparación del equipo de presentación

1. Instalar desde la etiqueta final con `uv sync --locked --extra ui --extra rl --python 3.12`, siguiendo `docs/INSTALACION_EQUIPOS.md`. La primera vez se necesita red.
2. Ejecutar la suite y los tres comandos de reproducción. Anotar el resultado en la tabla de SARB-003.
3. Abrir la interfaz con el modelo congelado de la demostración y comprobar que el catálogo lo muestra compatible con 12 × 12.
4. Tener abiertas las figuras finales y los CSV, y copiar los casos de respaldo a la biblioteca personal (`outputs/custom_scenarios`) si se prefiere cargarlos desde la interfaz.
5. Cuando exista el modo continuo: preparar una sesión de aprendizaje y conservar aparte una copia del modelo congelado para comparar y como respaldo (SARB-035).

## 4. Respuestas que todos deben poder dar

| Pregunta | Respuesta breve | Detalle |
|---|---|---|
| ¿Qué observa el agente? | Un vector con paredes, temperaturas normalizadas, posiciones de base, personas y robots, integridad, carga, estado de cada persona y fracción de pasos usados: `2WH + 11 + 7N` valores (320 en 12 × 12). El modo con sensores agrega `40 + 10N` distancias calculadas con el mapa completo (390 en total). Conoce el mapa; no busca a ciegas. | `docs/APRENDIZAJE.md`, `docs/CONTRATOS_V2.md` sección 6 |
| ¿Qué acciones elige? | Una acción conjunta entre 25: `5 × acción_robot_1 + acción_robot_2`, con arriba, abajo, izquierda, derecha o esperar para cada robot. Un solo controlador maneja a ambos. | `docs/CONTEXTO.md` |
| ¿Cómo se aplica el daño? | En cada paso, cada robot recibe daño según la temperatura de su celda: 0 bajo 40 °C, 2 entre 40 y 60, 5 entre 60 y 80 y 10 desde 80. Ocurre aunque espere o choque. La integridad empieza en 100, no se recupera, y llegar a 0 destruye al robot y hace fallar la misión. | `docs/CONTEXTO.md` sección 4 |
| ¿Cómo se entrena? | DQN de stable-baselines3 con recompensas por recoger (+5), entregar (+50), completar (+100), y penalizaciones por paso (−1), daño, destrucción y límite de tiempo, más una guía de distancia acotada. Se entrena por etapas y se guarda el checkpoint con más misiones completas en la evaluación periódica. | `docs/APRENDIZAJE.md` |
| ¿Cómo se evitó evaluar solo mapas memorizados? | Las particiones se congelaron antes de entrenar y separan los casos por firma física. Se elige con validación y la prueba se abre una sola vez con modelos congelados. El piloto 10 × 10 sirve de advertencia: resuelve sus posiciones de entrenamiento y falla en 30 de 30 posiciones nuevas. | `docs/PARTICIONES_V2.md`, `docs/ESTUDIO_ESCALA.md` |
| ¿Por qué menor daño sin rescate no basta? | La misión es rescatar a todos. Un fracaso temprano puede tener poco daño porque el robot se detuvo o se destruyó pronto. Por eso pasos y daño se comparan solo entre misiones exitosas. | `docs/METRICAS.md` |
| ¿Qué diferencia hay entre el modelo y las referencias? | Las referencias planifican con búsqueda sobre el mapa completo en cada misión. DQN aplica una política aprendida sin buscar. Las referencias certifican que un caso es viable; no garantizan que DQN lo resuelva. | `docs/EVALUACION.md`, `docs/INTERFAZ.md` |
| ¿Qué es aprender de forma continua y qué es evaluar? | Continuar el aprendizaje actualiza pesos y memoria. Evaluar usa un modelo congelado sin actualizarlo. Reproducir solo muestra una traza guardada. | SARB-033 a SARB-035 (pendiente) |

## 5. Registro del ensayo

| Campo | Valor |
|---|---|
| Fecha y equipo | Pendiente |
| Versión o etiqueta | Pendiente |
| Tiempo por bloque | Pendiente |
| Problemas encontrados | Pendiente |
| Cambios al guion | Pendiente |
| Video o capturas finales | Pendiente |
