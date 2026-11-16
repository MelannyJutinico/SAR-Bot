# Traspaso de la base al equipo

**Rama:** `feature/base` ([PR #1](https://github.com/MelannyJutinico/SAR-Bot/pull/1) hacia `main`). **Fecha:** 16 de noviembre de 2026.

Esta nota permite que cada integrante continúe su parte sin conocer toda la historia. Resume:

- Qué decidir primero.
- Qué está hecho.
- Cómo arrancar.
- Qué falta a cada persona.

El detalle técnico está en [DISENO.md](DISENO.md) y las reglas acordadas en [CONTEXTO.md](CONTEXTO.md).

## 1. Primero: decidir qué base usamos

En el repositorio hay dos bases independientes. No se pueden fusionar: hay que elegir una.

| Rama | Alcance | Estado al 16 de noviembre |
|---|---|---|
| `feature/base` (esta) | 6 × 6, dos robots, dos víctimas, tres planos | DQN con calor: 92,0 % ± 6,4 % de éxito en validación. Faltan la evaluación final, las gráficas y el informe |
| `feature/simulation-core` | V2: de 10 × 10 a 12 × 12, tres personas, editor por clics, aprendizaje continuo. Backlog SARB-001 a SARB-035 | Base publicada el 13 de noviembre. Las 35 tareas siguen abiertas. Su piloto DQN aún no resuelve el edificio grande |

Hasta decidir, **no fusionar el PR #1 a `main`**.

Esta rama se construyó con el rol de persona 1 descrito en `CONTEXTO.md`. El equipo debe confirmar quién ocupa cada rol. El resto de esta nota supone que se continúa con `feature/base`. Si eligen la V2, el apartado 8 resume lo que se puede trasladar.

## 2. Avance estimado

| Parte | Avance | Qué hay |
|---|---:|---|
| Persona 1: base, DQN e integración | ~85 % | Motor, Gymnasium, referencia, DQN que aprende, evaluación, demo, 119 pruebas, tres semillas y modelo elegido |
| Persona 2: entorno y escenarios | ~60 % | Motor con calor y choques, tres planos, generador reproducible y comprobación de viabilidad |
| Persona 3: visualización | ~50 % | Demo Pygame con calor, panel de estado y controles |
| Persona 4: evaluación e informe | ~25 % | Evaluación con CSV y resultados de validación documentados |
| **Proyecto completo** | **~62 %** | Días 1 a 4 del plan hechos; día 5 a medias |

Son estimaciones sobre los entregables de [PLAN_DE_TRABAJO.md](PLAN_DE_TRABAJO.md). No miden horas.

## 3. Arrancar

Requiere Python 3.11 o superior; se verificó con 3.11.9 en Windows.

```bash
git clone https://github.com/MelannyJutinico/SAR-Bot.git
cd SAR-Bot
git switch feature/base
python -m venv .venv
```

Activar el entorno: en Windows con `.venv\Scripts\activate`; en Linux o macOS con `source .venv/bin/activate`. Después:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Deben pasar las 119 pruebas.

Ver la demo con el modelo elegido. No hace falta entrenar: los modelos están en [artifacts/](../artifacts/README.md).

```bash
python scripts/play.py --strategy dqn --model artifacts/etapa3_desde2_s2/best_model.zip
```

Controles:

| Tecla | Acción |
|---|---|
| Espacio | Pausa |
| → | Un paso |
| R | Reinicia |
| N / B | Escenario siguiente o anterior |
| + / − | Velocidad |
| E | Cambia de estrategia |
| Esc | Sale |

Comparar el modelo con la referencia en validación:

```bash
python scripts/evaluate.py --strategy referencia dqn --model artifacts/etapa3_desde2_s2/best_model.zip
```

## 4. Mapa del código

| Ruta | Qué contiene | Quién continúa |
|---|---|---|
| `src/sar_bot/core/` | Motor: reglas, movimiento, calor y generador de escenarios | Persona 2 |
| `scenarios/layouts/` | Planos 6 × 6 en texto (`.` libre, `#` pared, `B` base) | Persona 2 |
| `configs/*.toml` | Reglas, calor, escenarios, recompensa y entrenamiento | Persona 2 (calor), persona 1 (entrenamiento) |
| `src/sar_bot/env/` | Entorno Gymnasium, observación, recompensa y guía | Persona 1 |
| `src/sar_bot/agents/` | DQN, referencia y política aleatoria | Persona 1 (DQN), persona 4 (referencia) |
| `src/sar_bot/training.py`, `scripts/train.py` | Entrenamiento y selección en validación | Persona 1 |
| `src/sar_bot/ui/renderer.py`, `scripts/play.py` | Demo Pygame | Persona 3 |
| `src/sar_bot/evaluation.py`, `scripts/evaluate.py` | Métricas y CSV por episodio | Persona 4 |
| `artifacts/` | Modelos publicados y CSV de resultados | Personas 1 y 4 |
| `tests/` | Pruebas de reglas e integración | Cada autor sobre su cambio |

El motor es la única fuente de reglas. La interfaz y la evaluación solo leen su estado.

## 5. Resultados actuales (validación, 150 escenarios)

| Estrategia | Éxito | Daño total medio | Pasos en éxitos |
|---|---:|---:|---:|
| Referencia (ruta corta, ignora el calor) | 100 % | 17,7 | 14,1 |
| DQN semilla 0 | 84,7 % | 23,1 | 17,6 |
| DQN semilla 1 | 95,3 % | 18,3 | 16,3 |
| DQN semilla 2 (elegido) | 96,0 % | 19,8 | 17,4 |
| DQN, media de las tres | 92,0 % ± 6,4 % | 20,4 ± 2,4 | — |

Conclusiones actuales:

- DQN aprende a rescatar y coordinar con calor, pero solo si antes entrena sin calor. Desde cero con calor llega al 24 %.
- Todavía no supera a la referencia: rescata algo menos y sus rutas son más largas.
- La partición de **prueba** no se ha usado.

## 6. Qué falta por persona

### Persona 2: entorno y escenarios

1. **Decidir la severidad del calor.** Bloquea la evaluación final.
   - Con el calor actual, la referencia nunca fracasa. DQN solo puede mejorarla en daño.
   - Con pico 100 y gradiente 15, la referencia completa 149 de 150 y su daño medio sube a 46,4.
   - Elegir entre mantener o endurecer `[heat]` o las franjas de daño en `configs/base.toml`, y registrarlo en DISENO.md, apartado «Hallazgo para decidir en equipo».
2. **Si cambia el calor, avisar.** La etapa con calor de las tres semillas se repite desde `artifacts/etapa2_s*/final_model.zip`; son unos 15 minutos en paralelo. La etapa sin calor no cambia.
3. **Revisar reglas y viabilidad.** Las pruebas están en `tests/test_movement.py`, `tests/test_engine.py` y `tests/test_scenario.py`. Añadir un plano cambia las particiones: hacerlo antes de la evaluación final y reentrenar.
4. **No cambiar** el tamaño 6 × 6 ni el número de víctimas. Los modelos dejarían de servir.

### Persona 3: visualización

1. Dibujar el rastro recorrido por cada robot.
2. Comparar referencia y DQN sobre el mismo escenario, alternando con E o lado a lado, con las métricas finales de ambos.
3. Preparar capturas o un video de respaldo para la presentación. `Renderer.render_array` permite capturar sin abrir ventana.
4. Revisar la claridad de la leyenda, de los mensajes de fin y de los colores de calor.
5. Mantener la regla: la interfaz no calcula daño ni decide rescates.

### Persona 4: evaluación e informe

1. **Ahora:** preparar gráficas con los CSV de validación de `artifacts/resultados/`:
   - Éxito por estrategia.
   - Daño y pasos solo en éxitos.
   - Resultados por plano.
   - Media ± desviación entre semillas.
2. **Cuando el calor esté decidido y los modelos congelados:** evaluación final en prueba, una sola vez, con las tres semillas:

   ```bash
   python scripts/evaluate.py --strategy referencia aleatoria dqn --model artifacts/etapa3_desde2_s0/best_model.zip --split test --out outputs/prueba_s0.csv
   ```

   Repetir con `s1` y `s2`. No ajustar nada después de ver estos resultados.
3. **Informe:**
   - Problema y reglas.
   - Formulación: observación de 227 valores, 25 acciones conjuntas, recompensa y guía por potencial.
   - Entrenamiento por etapas.
   - Resultados, incluidos los negativos: sin currículo y con mayor peso del daño.
   - Límites.
4. **Presentación y ensayo** con la demo y el video de respaldo.

### Persona 1: integración y cierre

1. Repetir la etapa con calor de las tres semillas si cambia el calor, y publicar los modelos nuevos en `artifacts/`.
2. Revisar e integrar los cambios de las personas 2, 3 y 4.
3. Fusionar a `main` la base elegida.
4. Apoyar la evaluación final.

## 7. Reglas para no romper la base

- **Ramas:** trabajar en `feature/<tema>` creada desde `feature/base` y abrir el PR hacia `feature/base`.
- **Pruebas:** ejecutar `python -m pytest` antes de cada PR.
- **Reentrenar si cambia el modelo del problema.** Cambiar las reglas, el calor, la recompensa, la observación, las acciones o los planos invalida los modelos. Registrar el cambio en DISENO.md y reentrenar.
- **Prueba de una sola vez.** La partición de prueba se usa una vez, con los modelos congelados.
- **Qué no se sube:** `.venv/`, `outputs/`, `runs/` y `models/`. Solo los modelos elegidos van a `artifacts/`, con su `metadata.json`.

## 8. Si el equipo elige la base V2

El código de esta rama no se traslada directamente, pero estos aprendizajes sí:

- **Seleccionar modelos** por tasa de éxito en validación y, a igual éxito, por retorno sin guía. El retorno con guía premia quedarse quieto cuando γ < 1 y elige puntos que no rescatan.
- **Currículo:** primero sin calor y después con calor, partiendo de los pesos anteriores con exploración inicial 0,3.
- **Guía por potencial**, con la distancia de camino pendiente como potencial. Funcionaron γ = 0,95 y actualización del objetivo cada 500 pasos.
- **No subir el peso del daño:** con −0,3 y −0,5 el éxito cae al 38 % y al 22,7 % sin rutas más seguras.
- **Reportar varias semillas:** el éxito varía unos 6 puntos entre ellas.
