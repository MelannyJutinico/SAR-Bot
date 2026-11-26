# Fallos y límites observados en trazas (SARB-023)

## Análisis final — 26 de noviembre de 2026

Las trazas reservadas ya están evaluadas: DQN termina 39/40 misiones por tiempo y una por destrucción, con 16/120 personas entregadas. En `detour_test_01_easy` entrega dos personas, pero agota 300 pasos sin recoger la restante; los robots registran 194 y 112 retornos a la celda de dos pasos antes. La ruta corta y la térmica completan ese mismo caso en 18 pasos, sin daño. Son movimientos observables, no una explicación causal del estado interno de la red.

El [análisis final generado](../results/final/trace_analysis/trazas.md) reproduce las acciones conservadas y comprueba sus totales. El [informe](INFORME.md) explica el resultado de generalización y la regresión de la sesión adaptada. Las secciones siguientes conservan ejemplos de desarrollo anteriores, con sus perfiles y modelos originales.

---

**Responsable:** persona 4 con persona 1. **Revisa:** persona 2. **Actualización:** 18 de noviembre de 2026.

**Estado:** analizados un rescate eficiente, un caso térmico y un fallo real, todos con datos de desarrollo y entrenamiento. Falta agregar los fallos de la evaluación final (SARB-021) cuando existan los modelos congelados, siguiendo la sección 4.

Las descripciones salen de [`results/sarb023/trazas.md`](../results/sarb023/trazas.md). Ese archivo se genera con `scripts/trace_story.py` desde `configs/analysis/sarb023_casos.json`: reproduce las acciones guardadas de cada episodio en un motor nuevo y comprueba que los totales coincidan con su fila del CSV. Solo se describe lo que cambia en los estados (posiciones, carga, daño, integridad); no se atribuyen intenciones al controlador.

## 1. Casos

### Rescate eficiente de una política aprendida

`sensors_dqn` en el pasillo compartido de 6 × 6: rescate completo en 22 pasos, sin daño. Cada robot entrega a una persona. El robot 2 recorre el pasillo hasta F6 y entrega en el paso 22. El robot 1, en cambio, entrega en el paso 12 y se queda en la base: acumula 6 movimientos bloqueados (5 seguidos entre los pasos 13 y 17) y 4 esperas. Este escenario se usó al entrenar, así que el caso muestra una ejecución eficiente y no generalización.

### Caso térmico: misma misión, dos criterios

Caso `detour_training_14_intermediate` de la partición de entrenamiento de 12 × 12. Allí, la fila 7 entre E7 y J7 es un corredor que llega a 90 °C y separa la base de las personas.

- **Ruta corta.** Ambos robots atraviesan el corredor en casi cada tramo de ida o de vuelta. El robot 2 recibe 44 de daño en su ida (pasos 3 a 10) y otros 44 en su vuelta (pasos 18 a 25). El robot 1 recibe 11 en su primera ida, 24 al volver con la persona 1 y 44 en su segunda ida. Al volver con la persona 3 recibe otros 21 y queda destruido en I7, en el paso 45, cargándola. Termina con 2 de 3 personas, 190 de daño, y el robot 2 con integridad 10.
- **Ruta térmica.** Completa el rescate en 66 pasos con daño 0. Las dos primeras entregas llegan en el paso 32, cuatro pasos después que con la ruta corta (paso 28). El robot 1 hace el segundo viaje entre los pasos 49 y 66.

El rodeo cuesta pasos en cada viaje y elimina toda la exposición. Con la ruta corta, el daño se acumula viaje a viaje hasta destruir a un robot que cargaba a una persona; por eso hay rescate parcial.

### Fallo real: piloto DQN con posiciones nuevas

`v2_pilot` en `building10_dev_16_easy`, un caso fácil del conjunto de desarrollo 10 × 10. El piloto solo se entrenó con las posiciones fijas de ese edificio.

- Las personas 1 y 3 están junto a la base, y ambos robots las recogen y entregan en los dos primeros pasos.
- Desde el paso 3 hasta el 240, los dos robots permanecen en la base A1 y no logran moverse en ninguno de sus intentos: 238 movimientos bloqueados cada uno, sin esperas ni daño.
- La persona 2, en A4 (tres celdas más abajo), nunca se recoge. La misión termina por límite de pasos con 2 de 3 personas.

La ruta térmica resuelve el mismo caso en 8 pasos con daño 0. Lo observable es que la política repite acciones que no cambian la posición cuando la tercera persona no está donde estaba al entrenar. La traza no distingue si cada intento choca con el borde, con una pared o con el otro robot. Las trazas no muestran por qué la red elige esas acciones. El estudio de escala encontró el mismo patrón en los 30 casos con posiciones nuevas: ninguno completado y 342,1 bloqueos por episodio de media (`docs/ESTUDIO_ESCALA.md`).

## 2. Lo que estos casos permiten y no permiten afirmar

- **Edificios conocidos, no exploración.** Todos los casos usan edificios preparados y conocidos. Una política que funciona en ellos aprende a resolver ubicaciones dentro de esos edificios; no explora edificios desconocidos. El fallo del piloto ocurre incluso dentro de un edificio conocido cuando cambian las posiciones.
- **Sensores con mapa completo.** El modo con sensores calcula legalidad, ocupación, temperatura y distancias de camino a partir del mapa completo. No modela sensores físicos con alcance o ruido.
- **Control centralizado.** Una sola política elige la acción conjunta de ambos robots, con información perfecta y sin retrasos de comunicación. El reparto 1–1 o 2–1 que se observa no prueba cooperación entre agentes independientes.
- **Simplificación térmica.** El campo de temperatura es fijo durante la misión, el daño depende de cuatro tramos de temperatura y no hay recuperación. No representa un incendio real.
- **Exposición de los robots.** Ambos robots reciben daño en cada paso según su celda, aunque esperen o choquen. La destrucción de un robot hace fallar la misión aunque el otro siga operativo.
- **Traslado abstracto.** Recoger y entregar son automáticos al llegar a la celda, sin tiempo de carga, y cada robot lleva a una persona. Las personas no se mueven ni tienen un plazo de supervivencia.

## 3. Propuestas de trabajo futuro

Cada propuesta surge de lo observado y queda fuera del alcance actual salvo que el backlog la incluya.

- Entrenar con posiciones variables desde el inicio (SARB-015 y SARB-016) y medir los movimientos bloqueados junto con el éxito, porque el fallo observado es una repetición de acciones sin efecto.
- Probar el enmascaramiento de acciones inválidas, o una penalización explícita a los bloqueos, como ablación separada y sin mezclarla con otros cambios.
- Agregar una etapa con corredores calientes que separen base y personas, como en `detour`, para que la política vea el costo acumulado de cruzarlos varias veces.
- Evaluar en un edificio que no se usó al entrenar para medir generalización a edificios nuevos, separada de la generalización a posiciones nuevas.
- Estudiar observación parcial y sensores con alcance limitado, o políticas descentralizadas, como extensiones posteriores.

## 4. Procedimiento para los fallos de la prueba final

Cuando SARB-021 produzca el CSV de prueba con los modelos congelados:

1. Crear `configs/analysis/sarb023_final.json` con al menos un fallo real de prueba por modelo, si lo hay, y su contraste con una referencia. No se edita `sarb023_casos.json`, que la suite comprueba que no use la prueba.
2. Generar con `uv run python scripts/trace_story.py --cases configs/analysis/sarb023_final.json --output-dir results/final/trazas`.
3. Analizarlos aquí con el mismo criterio: solo lo observable, sin volver a entrenar ni ajustar el modelo. Si un resultado de prueba se usa para ajustar algo, esos casos pasan a desarrollo y la evaluación deja de ser independiente (`docs/PARTICIONES_V2.md`).

Las trazas exportadas desde la interfaz (`outputs/mission_traces`) también sirven para reproducir un caso, pero las de este análisis salen de los CSV versionados para que cualquiera pueda regenerarlas.
