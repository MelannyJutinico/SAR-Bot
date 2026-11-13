# Segundo experimento: cooperación desde el modelo inicial

Este experimento se conserva como evidencia de desarrollo, no como modelo recomendado.

- Inicialización: `artifacts/initial_dqn/model.zip` (42000 pasos previos).
- Pasos adicionales: 160000; semilla 0.
- Mejor checkpoint: 80000 pasos adicionales.
- Configuración: `configs/dqn_cooperation.json`.
- Observación: modo original de 97 entradas.
- Recompensa por daño: −2; no comparar directamente retornos con la primera ejecución.

El checkpoint seleccionado completa cinco de los seis escenarios de control. Aprende el paso compartido cercano en seis pasos, pero entrega solo una víctima en el pasillo largo y agota el tiempo. Mantiene 18 y 74 puntos de daño en los mapas térmicos, sin mejorar la referencia geométrica.

Otros checkpoints completaron el pasillo largo a costa de perder otras tareas. No se seleccionaron casos diferentes para aparentar un controlador que resuelva todo. Los seis controles se usaron en entrenamiento y selección; no hay evaluación de prueba reservada para este modelo.

Los CSV, metadatos, modelo y evaluaciones temporales permiten reproducir estos resultados. El tercer experimento estudia sensores locales adicionales, conservando este registro y el modelo inicial.
