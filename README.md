# SAR-Bot

Simulador de rescate con **dos robots controlados por una red neuronal**, tres personas, edificios de 12 × 12 y exposición térmica acumulada. El agente aprende a repartir rescates y elegir entre rapidez y menor exposición; un planificador A* calcula los movimientos.

## Iniciar

En Windows, instalar una vez con Python 3.12 y `uv`:

```powershell
uv sync --locked --extra ui --extra rl --python 3.12
.\run.bat
```

Después basta abrir **run.bat**. La aplicación inicia con el **agente neuronal de rescate**, en pausa. Pulsa **Ver misión y controles** y luego iniciar. El caso inicial entrega las tres personas en **62 pasos**, con daño total 42. Las dependencias y el modelo quedan instalados localmente; la ejecución no necesita Internet.

![Rescate completado por el agente neuronal](docs/images/neural-rescue.png)

## Qué hace la red

Es una red pequeña **16 → 64 → 32 → 1**, compartida por los dos robots. Puntúa alternativas de reparto y de exposición al calor. Sus entradas describen distancias de ruta, daño previsto, carga, integridad y trabajo pendiente. Se entrenó por **aprendizaje supervisado** con etiquetas de un estimador de coste programado. El entrenamiento y su evaluación están conservados en el repositorio.

El agente mantiene cada objetivo hasta recoger a la persona; vuelve a la base para entregarla. Cuando queda sin carga ni tarea, espera en la base mientras su compañero termina. **A* se encarga de los caminos y las colisiones**. La red aprende las preferencias de reparto y riesgo; no se atribuye a la red una locomoción aprendida de extremo a extremo. Una sola red controla a dos agentes físicos.

El DQN anterior, que elegía movimientos individuales y se quedaba dando vueltas, se conserva como antecedente experimental. **El modelo usado ahora es `artifacts/rescue_network/model.zip`.**

## Usar la interfaz

1. **Mapa del edificio:** elegir uno de los mapas compatibles.
2. **Colocar personas:** cambiar las tres ubicaciones, validar y preparar.
3. Elegir **Solo ejecutar** para usar la red base, o **Aprender** para continuar la sesión.
4. **Ver misión y controles:** iniciar, pausar, avanzar un paso y ajustar velocidad. Cada robot muestra a qué persona se dirige o si vuelve a la base.
5. **Comparar las 4 estrategias:** ejecutar el mismo caso con la red, ruta corta, ruta térmica y movimientos al azar. Son referencias de evaluación. **Ver recorrido** reproduce cada resultado sin entrenar.

La velocidad solo modifica la reproducción. El daño se aplica a ambos robots en cada paso, incluso al esperar: menos de 40 °C → 0; desde 40 y menos de 60 → 2; desde 60 y menos de 80 → 5; desde 80 → 10. Cada robot empieza con integridad 100 y transporta una persona por viaje.

## Aprendizaje entre ejecuciones

**Aprender** recupera la sesión del modelo y guarda experiencias al finalizar cada misión nueva. Se entrenan pesos candidatos y se comprueba su resultado en casos de control de entrenamiento. Una regresión detectada conserva pesos y optimizador anteriores; las experiencias permanecen guardadas. Comparar, pausar y reproducir no entrenan.

Se conserva modelo, optimizador, ejemplos de asignación, estados aleatorios y contadores en `outputs/learning_sessions/`. Al reiniciar, pulsa **Aprender** para recuperar esa sesión. La red base permanece intacta y **Solo ejecutar** utiliza siempre esa base reproducible.

Comprobación real del controlador actual: dos procesos independientes rescataron a las tres personas en 12 y 16 pasos sobre dos casos de entrenamiento. La sesión acumuló **2 misiones, 28 pasos observados, 40 ejemplos de asignación y 128 actualizaciones aceptadas**. Los parámetros cambiaron y se mantuvo el resultado de los controles; eso no significa mejora garantizada en cualquier caso.

```powershell
.\run.bat --learn --scenario scenarios/partitions/v2_12x12/training/hub_training_01_easy.json
```

## Resultados y documentación

**Prueba nueva reservada:** 40 ubicaciones, sin solapamiento con los 120 casos anteriores. El modelo se congeló antes de abrirlas.

| Controlador | Rescates completos | Pasos medios | Daño medio |
|---|---:|---:|---:|
| Red entrenada + A* | 40/40 | 41,20 | 13,83 |
| Misma red antes de entrenar + A* | 40/40 | 43,63 | 15,63 |
| Referencia térmica | 40/40 | 44,28 | 13,80 |

Las dos redes comparten arquitectura, inicialización de semilla 7 y planificador. Las medias de esta tabla se comparan sobre los mismos cuarenta éxitos. Se evaluaron además otras cinco inicializaciones sin entrenar y la referencia de ruta corta: ver el informe completo. El planificador aporta la navegación; el entrenamiento mejora las decisiones de reparto y riesgo.


- El modelo actual completó **20/20 misiones de validación** y **40/40 misiones reservadas nuevas**, con las tres personas pendientes en todos los casos.
- [Resultados reservados, comparación con redes sin entrenar y límites](results/assignment/report.md).
- [Informe técnico vigente](docs/INFORME.md), [guion de presentación](docs/DEMO.md), [controles](docs/INTERFAZ.md).
- [Modelo, método, fuentes y semilla](artifacts/rescue_network/metadata.json).
- [Protocolo congelado antes de las nuevas ubicaciones reservadas](configs/assignment_protocol.json).
- [Persistencia comprobada del agente actual](results/assignment/online/persistence.json).

Se compara con redes sin entrenar que usan el mismo planificador para distinguir el aporte del aprendizaje del aporte de A*. Solo hay una semilla entrenada. Los edificios son conocidos y las posiciones reservadas son nuevas; los escenarios se certificaron mediante referencias, lo que favorece sus resultados. No se promete resolver cualquier colocación posible.

**330 pruebas automatizadas aprobadas**, además de reproducir las trazas de los 360 episodios de la evaluación nueva.

## Comprobar y reproducir

```powershell
uv run --locked --extra ui --extra rl python -m unittest discover -s tests
uv run --locked python scripts/report_assignment.py --check
```

El segundo comando verifica el informe y reproduce acciones conservadas; no entrena ni vuelve a abrir prueba. La reproducción de un entrenamiento se hace en una carpeta local nueva:

```powershell
uv run --locked --extra rl python scripts/train_assignment.py --output outputs/reproduccion_neuronal
```

Se trabaja en **main**, sin crear nuevas etiquetas de versión. La etiqueta inicial conserva el estado anterior para trazabilidad. Los resultados del DQN de movimientos están en `results/final/`; corresponden a otro controlador y otra prueba reservada. Los documentos históricos del backlog se interpretan según el [alcance acordado](docs/ALCANCE.md).
