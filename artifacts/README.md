# Modelos y resultados publicados

Esta carpeta guarda los modelos que el equipo necesita para continuar sin volver a entrenar. Las corridas completas se guardan en `models/` y `runs/`, que no se suben al repositorio.

Todos los modelos se entrenaron con la configuración guardada en su `metadata.json`: mapa 6 × 6, dos robots, dos víctimas y observación de 227 valores. Solo funcionan con esa configuración. Si cambia el tamaño del mapa, el número de víctimas o la observación, hay que volver a entrenar.

## Modelo elegido

`etapa3_desde2_s2/best_model.zip` es el modelo con calor elegido en validación, con 96,0 % de éxito. Es el que se usa en la demo y en la presentación.

## Las tres semillas

| Carpeta | Archivo | Uso | Éxito en validación |
|---|---|---|---:|
| `etapa3_desde2_s0` | `best_model.zip` | Etapa con calor, semilla 0 | 84,7 % |
| `etapa3_desde2_s1` | `best_model.zip` | Etapa con calor, semilla 1 | 95,3 % |
| `etapa3_desde2_s2` | `best_model.zip` | Etapa con calor, semilla 2 (elegido) | 96,0 % |
| `etapa2_s0` | `final_model.zip` | Etapa sin calor, semilla 0; punto de partida de la etapa con calor | — |
| `etapa2_s1` | `final_model.zip` | Ídem, semilla 1 | — |
| `etapa2_s2` | `final_model.zip` | Ídem, semilla 2 | — |

La evaluación final en prueba debe reportar las tres semillas con calor, no solo la elegida.

Los modelos sin calor se incluyen para repetir la etapa con calor si cambia el calor. Esa etapa parte de `final_model.zip`, no del mejor punto. El bloque `best` de su `metadata.json` describe el mejor punto de esa corrida, no el archivo publicado aquí.

El campo `init_model` del `metadata.json` muestra la ruta local original, `models/...`. Para reentrenar desde este repositorio, usar la ruta equivalente en `artifacts/`.

## Resultados por episodio

`resultados/eval_semillas_etapa2_validation.csv` y `resultados/eval_semillas_etapa3_validation.csv` tienen 150 escenarios de validación por estrategia: `referencia`, `dqn_s0`, `dqn_s1` y `dqn_s2`. Columnas:

- Identificación: `strategy`, `split`, `layout`, `scenario_id`, `seed`.
- Resultado: `outcome`, `success`, `rescued`, `victims`, `steps`.
- Daño e integridad: `damage_r0`, `damage_r1`, `damage_total`, `integrity_r0`, `integrity_r1`.
- Movimiento: `wall_bumps`, `robot_blocks`.
- Retorno: `return`, con shaping, y `task_return`, sin shaping.

Son resultados de **validación**. La partición de prueba todavía no se ha usado.
