# Cierre técnico de SAR-Bot 1.0.0

**Estado actual de main:** después del cierre se simplificaron los controles y se protegieron las actualizaciones de sesión contra regresiones detectadas. Se continúa en la misma rama, sin nuevas etiquetas de versión. [Guía actual de opciones](INTERFAZ.md). Los resultados congelados y las verificaciones de la primera entrega se conservan abajo.

Versión del **26 de noviembre de 2026**, bajo el [alcance de cierre acordado](ALCANCE.md). La distribución se identifica con la etiqueta Git `v1.0.0`. El README contiene la instalación y `run.bat` inicia la aplicación.

## Qué se considera terminado

| Entregable | Evidencia |
|---|---|
| Simulación 12 × 12, dos robots y tres personas; daño por temperatura y exposición | Motor en `src/sar_bot/core/`, escenarios y pruebas |
| Interfaz, edición, validación, comparación, historial y exportación | `src/sar_bot/ui/`, capturas y [guion](DEMO.md) |
| DQN entrenado y modelo congelado de una semilla | `artifacts/final/`, `configs/final_protocol.json`; congelación en `3f5eed5` antes de prueba |
| Evaluación reservada completa | 40 casos, 320 episodios; [tablas](../results/final/figures/tablas.md), CSV y trazas en `results/final/` |
| Aprendizaje persistente entre misiones | Dos procesos, 580 experiencias, 128 actualizaciones; [evidencia](../results/online/persistence.json) |
| Medición antes/después de aprender | [Comparación sobre validación](../results/online/figures/tablas.md), con regresión declarada |
| Informe, análisis de fallos y presentación | [Informe](INFORME.md), [trazas finales](../results/final/trace_analysis/trazas.md), [demostración](DEMO.md) |
| Instalación y ejecución verificadas | Lockfile válido, paquete 1.0.0 instalado, **315 pruebas aprobadas** y dos ejemplos reproducidos |

## Verificación realizada

Entorno: Windows, Python 3.12.15, Pygame 2.6.1; dependencias fijadas en `uv.lock` y PyTorch CPU.

- Suite completa: **315 pruebas, 221,304 segundos, OK**, sobre el último código funcional de interfaz y aprendizaje (`7da1318`). Los cambios posteriores añaden documentación, evidencia, script de archivo de sesión y versión del paquete.
- `uv sync --locked --extra ui --extra rl --python 3.12`: correcto; instaló SAR-Bot 1.0.0 sin modificar dependencias resueltas.
- Inicio predeterminado, térmica: **3 entregas, 66 pasos, daño 42**.
- Ejemplo DQN conocido de validación: **3 entregas, 126 pasos, daño 0**.
- Persistencia: primera ejecución 280 experiencias y 64 actualizaciones; segunda ejecución recuperó esa sesión y terminó con 580 y 128. Cambiaron los parámetros Q y se mantuvo intacto el modelo base.
- ZIP extraído en una carpeta aparte, entorno virtual nuevo e instalación con lockfile: correctos. El lanzador y el ejemplo DQN reprodujeron las cifras anteriores; sus capturas resultaron idénticas a las originales. Las figuras del paquete también pasaron `--check`.
- Las figuras y análisis se regeneraron desde CSV y trazas, comprobando las acciones contra un motor nuevo.

Registro estructurado: [verification.json](../results/final/verification.json). Las capturas son de ejecuciones automatizadas en el computador disponible; no se atribuye un ensayo oral ni instalaciones en cuatro computadores.

## Resultados que se deben explicar

DQN obtuvo **3/20 misiones completas de validación y 0/40 de prueba**, con 16/120 personas entregadas en prueba. La ruta corta completó 33/40 y la térmica 40/40. Se usó una sola semilla de entrenamiento y los escenarios fueron certificados por referencias. El modelo congelado no se ajustó después de abrir prueba.

La sesión local de dos misiones empeoró de 3/20 a 0/20 en validación. La persistencia funciona; no se garantiza mejora ni se sustituye automáticamente el checkpoint congelado por una sesión adaptada. El ejemplo DQN de presentación fue elegido en validación y se identifica como caso conocido.

## Reproducir las comprobaciones

Desde la raíz:

```powershell
uv sync --locked --extra ui --extra rl --python 3.12
.\run.bat
uv run --locked --extra ui --extra rl python -m unittest discover -s tests
uv run --locked --extra rl python scripts/evaluate_experiment.py --verify results/final/test.csv
uv run --locked python scripts/report_figures.py --check results/final/figures
uv run --locked python scripts/report_figures.py --check results/online/figures
uv run --locked python scripts/trace_story.py --check results/final/trace_analysis
```

Estas verificaciones no entrenan ni ejecutan una nueva prueba final. El marcador `configs/final_protocol.started.json` impide reutilizar su protocolo para otra apertura. Los archivos congelados conservan sus hashes originales.

## Distribución

El repositorio etiquetado contiene código, modelos publicados, escenarios, manifiestos, protocolo, resultados, figuras, capturas y documentación. El ZIP de entrega se genera con `git archive` desde `v1.0.0`, por lo que excluye `.venv`, cachés, secretos y sesiones personales de `outputs/`.

La primera instalación necesita las dependencias; después, la demostración funciona sin conexión. Una instalación nueva comienza sin sesión aprendida y conserva el checkpoint final como base. No se requiere entrenar durante la exposición.

El backlog original queda como historial. Tres semillas, validación en cuatro computadores, aprendizaje en cada movimiento y mejoras futuras del controlador no se presentan como actividades realizadas ni bloquean el alcance reducido autorizado. La aceptación académica corresponde al profesor; el repositorio documenta la entrega técnica y sus límites observados.
