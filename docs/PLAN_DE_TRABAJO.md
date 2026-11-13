# Plan de trabajo: cuatro personas y una semana

## Nuestro rol: persona 1

Nosotros construiremos la base integrada, el aprendizaje y la dirección técnica. Las otras tres personas refinarán y continuarán esa base. La meta inicial es que todos puedan ejecutar el mismo proyecto y trabajar en módulos separados.

## Base que dejaremos durante los primeros dos días

1. Estructura Python con dependencias verificadas e instrucciones de instalación.
2. Motor con dos robots, recogida, entrega, obstáculos y pasos globales.
3. Temperatura y exposición de ambos robots, independiente de la velocidad visual.
4. Adaptador Gymnasium con observaciones de tamaño fijo y 25 acciones conjuntas.
5. Entrenamiento DQN ejecutable, guardado y carga del modelo, sin prometer convergencia inicial.
6. Render mínimo en Pygame con figuras de colores.
7. Estrategia de referencia funcional.
8. Evaluación que exporte resultados por episodio.
9. Verificaciones de reglas críticas y un escenario de misión completa reproducible.

La base debe funcionar de principio a fin, aunque su aspecto visual y el desempeño inicial sean modestos. El estado actual del repositorio es documentación: estos componentes todavía están pendientes.

## Separación de responsabilidades

| Persona | Responsabilidad | Entregables |
|---|---|---|
| 1: nosotros | Base, Gymnasium, DQN, diagnóstico e integración | Sistema ejecutable, scripts y política guardada |
| 2 | Entorno y escenarios | Reglas refinadas, calor, mapas viables y verificación de movimientos |
| 3 | Visualización | Pygame, controles, indicadores y claridad de la demostración |
| 4 | Evaluación y documentación | Referencia refinada, experimentos, gráficas e informe |

Durante la construcción inicial, la persona 2 diseña escenarios, la 3 prepara vistas con estados de ejemplo y la 4 especifica casos de verificación y resultados esperados.

## Estructura prevista, todavía por implementar

```text
src/sar_bot/
    core/          # Estado, movimientos, rescate y calor; persona 2
    env/           # Adaptador Gymnasium y recompensas; persona 1
    agents/        # Política aprendida y referencias; personas 1 y 4
    ui/            # Pygame; persona 3
scripts/           # Entrenar, reproducir y evaluar
configs/           # Reglas, recompensas y entrenamiento
scenarios/         # Mapas y particiones de entrenamiento/validación/prueba
tests/             # Verificaciones críticas de reglas
docs/              # Contexto, diseño y resultados
```

El motor será la única fuente de las reglas. La interfaz no calculará daño ni decidirá rescates. La evaluación y el entrenamiento consumirán el mismo entorno.

## Calendario relativo

| Día | Hito |
|---|---|
| 1 | Contrato de estado y acciones; motor básico |
| 2 | Referencia, render y entrenamiento conectados |
| 3 | Rescate aprendido sencillo sin calor; refinamiento por módulo |
| 4 | Calor, configuraciones variadas y diagnóstico |
| 5 | Cierre de funcionalidades y selección mediante validación |
| 6 | Evaluación final, gráficas y análisis |
| 7 | Correcciones, ensayo y entrega |

El calendario es un objetivo, no evidencia de progreso ni una garantía de convergencia. Si el agente no aprende, reducir obstáculos y variedad y revisar el entorno antes de añadir complejidad. Mantener dos robots y exposición térmica como identidad de la entrega.

## Verificaciones necesarias

- Esperar en una celda caliente causa daño en cada paso global.
- Ambos robots reciben exposición exactamente una vez por paso.
- Cuatro pasos a 65 °C causan 20 puntos de daño.
- Los umbrales 40, 60 y 80 se aplican sin huecos ni solapamientos.
- Las colisiones no detienen el reloj y no duplican exposición.
- Una víctima no puede recogerse o entregarse dos veces.
- Destrucción y límite de tiempo se distinguen de éxito.
- Una trayectoria de referencia completa un escenario viable.
- Reiniciar con la misma semilla reproduce el escenario.

## Criterios de entrega

- [ ] Instalación documentada y reproducible.
- [ ] Dos robots y dos sobrevivientes visibles.
- [ ] Calor y daño acumulativo según tiempo simulado.
- [ ] Controlador entrenado guardado y cargable.
- [ ] Referencia comparable y resultados medidos.
- [ ] Panel de integridad, turnos, rescates y estado de misión.
- [ ] Pausa, reinicio, velocidad y selección de estrategia.
- [ ] Informe de resultados y limitaciones.
- [ ] Todos los integrantes pueden explicar el problema y sus reglas.
