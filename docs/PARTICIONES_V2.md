# Particiones experimentales V2 (SARB-009)

**Responsable:** persona 4, con persona 2. **Revisa:** persona 1. **Congelado el:** 18 de noviembre de 2026.

Este documento fija los casos que se usarán para entrenar, seleccionar y evaluar los modelos del perfil 12 × 12 con tres personas. Reemplaza a `configs/scenario_splits.json` como conjunto experimental del nuevo alcance. Ese archivo se conserva como historia de desarrollo del perfil 6 × 6 y no se presenta como prueba final.

## 1. Qué queda congelado

| Elemento | Valor |
|---|---|
| Identificador | `v2_12x12_v1` |
| Perfil | 12 × 12, tres personas, dos robots |
| Configuración de entrada | `configs/partitions/v2_12x12.config.json` |
| Manifiesto | `configs/partitions/v2_12x12.json` |
| SHA-256 del manifiesto (LF) | `3e0f1b71388118713c93eb11fe183934e17a2c40467cc49036650e095c8d6f39` |
| `content_sha256` interno | `c83ea4c157850f6c64768aee267b46a60cf3b50c41b99fa103564ab32aee4bc6` |
| Testigos de viabilidad | `configs/partitions/v2_12x12.witnesses.jsonl` |
| Escenarios | `scenarios/partitions/v2_12x12/{training,validation,test}/` |

Los hashes de archivo se calculan normalizando los finales de línea a LF, porque Git puede convertirlos a CRLF en Windows. El manifiesto registra el hash de cada escenario, de cada plantilla y del archivo de testigos, y su propio `content_sha256`.

Las cantidades se fijaron antes de entrenar y coinciden con el objetivo de planificación: no hizo falta reducirlas.

| Edificio | Plantilla | Entrenamiento | Validación | Prueba |
|---|---|---:|---:|---:|
| Centro de coordinación (`hub`) | `scenarios/v2/coordination_hub_12x12.json` | 30 | 10 | 20 |
| Desvío térmico (`detour`) | `scenarios/v2/thermal_detour_12x12.json` | 30 | 10 | 20 |
| **Total** | | **60** | **20** | **40** |

## 2. Cómo se generaron

1. Para cada edificio se llamó a `generate_configurations()` de persona 2 con una semilla de generación propia (`1209001` para `hub` y `1209002` para `detour`). Esta semilla no es la del entrenamiento ni la de la política aleatoria.
2. El generador alterna las familias `easy`, `intermediate` y `demanding`, y solo acepta casos con certificado positivo de `certify_viability()`. El presupuesto de certificación es el predeterminado: el límite de pasos del escenario por cada referencia intentada.
3. Se pidieron dos casos de margen por familia (66 por edificio). Se descartaron las configuraciones de desarrollo: las posiciones de cada plantilla y los ejemplos de `configs/v2_scenario_families.json`. Ninguna coincidió con los casos generados; quedaron seis certificados sin usar por edificio.
4. Dentro de cada familia se tomaron los primeros casos en orden de generación y se barajaron con una semilla de reparto propia (`1209101` y `1209102`). La prueba se asignó primero, después la validación y por último el entrenamiento.
5. Las cuotas por familia son las mismas en ambos edificios: entrenamiento 10/10/10, validación 4/3/3 y prueba 6/7/7, en el orden fácil/intermedio/exigente.

La separación usa `scenario_id`, la firma física que no depende del orden de las etiquetas. Intercambiar Persona 1 y Persona 2 produce el mismo `scenario_id` y no puede aparecer en dos particiones. `configuration_id` conserva el orden exacto para reproducir cada misión.

## 3. Distribución resultante

La tabla se obtiene con `python scripts/build_partitions.py summary --manifest configs/partitions/v2_12x12.json`. La distancia es la media de la distancia Manhattan de las personas a la base, normalizada por `ancho + alto − 2`. «Personas en calor» cuenta posiciones iniciales a 40 °C o más. Los pasos y el daño corresponden al testigo de certificación, no a DQN.

| Partición | Edificio | Casos | Fácil | Intermedio | Exigente | Distancia media | Personas en calor | Pasos testigo | Daño testigo |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Entrenamiento | hub | 30 | 10 | 10 | 10 | 0,362 | 23 | 40,2 | 23,2 |
| Entrenamiento | detour | 30 | 10 | 10 | 10 | 0,332 | 10 | 36,8 | 2,2 |
| Validación | hub | 10 | 4 | 3 | 3 | 0,380 | 7 | 43,7 | 18,8 |
| Validación | detour | 10 | 4 | 3 | 3 | 0,358 | 2 | 38,2 | 1,3 |
| Prueba | hub | 20 | 6 | 7 | 7 | 0,348 | 19 | 39,4 | 22,1 |
| Prueba | detour | 20 | 6 | 7 | 7 | 0,349 | 10 | 38,9 | 2,3 |

| Edificio | Intentos | Certificados | No certificados | Duplicados | Sin usar |
|---|---:|---:|---:|---:|---:|
| hub | 96 | 66 | 0 | 0 | 6 |
| detour | 86 | 66 | 0 | 0 | 6 |

Todos los testigos los obtuvo la referencia térmica, que es la primera que intenta el certificador. Ninguna configuración quedó como no certificada; si las hubiera, se guardarían en `diagnostic_not_certified` y no entrarían en ninguna partición.

## 4. Reglas de uso

- **Entrenamiento:** las etapas de entrenamiento solo usan la lista `training`.
- **Validación:** es la única partición para elegir checkpoints, hiperparámetros, recompensas o la semilla que se mostrará en la demostración.
- **Prueba:** no se usa para entrenar, elegir checkpoints, ajustar recompensas ni decidir qué semilla mostrar. Se abre una sola vez, con los modelos congelados de SARB-019, en SARB-021.
- Si un resultado de prueba se usa para ajustar algo, esos casos pasan a desarrollo y hay que crear un manifiesto nuevo (`v2_12x12_v2`) antes de volver a afirmar una evaluación independiente.
- El manifiesto no se edita a mano. Cualquier cambio requiere un `manifest_id` nuevo; el script se niega a sobrescribir archivos congelados.
- Un modelo de 10 × 10 no se evalúa con estas particiones. Si el equipo conserva el perfil 10 × 10 (SARB-002), se genera un manifiesto separado con otra configuración y el mismo script.

El manifiesto mantiene las claves `training`, `validation` y `test` con listas de rutas, así que funciona con el evaluador actual:

```powershell
uv run --extra rl python scripts/evaluate_dqn.py --model <modelo_12x12.zip> --manifest configs/partitions/v2_12x12.json --split validation --output outputs/validacion_v2.csv
```

Para entrenar, una etapa puede copiar la lista `training` del manifiesto en su campo `scenarios`.

## 5. Verificación automática

```powershell
uv run python scripts/build_partitions.py verify --manifest configs/partitions/v2_12x12.json
uv run python -m unittest tests.test_partitions -v
```

`verify` comprueba:

- los hashes de escenarios, plantillas, testigos y del contenido del manifiesto;
- que los identificadores y posiciones registrados coincidan con cada archivo;
- el perfil 12 × 12 con tres personas, y que cada caso conserve la geometría y el calor de su plantilla;
- las cuotas por edificio, partición y familia, y el mínimo de 20 casos de prueba;
- que ninguna ruta, `scenario_id` ni `configuration_id` se repita entre particiones;
- que no aparezcan ejemplos de desarrollo ni particiones históricas;
- que cada testigo se reproduzca con éxito en `RescueSimulation`;
- que ningún `configs/dqn_*.json` entrene con validación o prueba, ni elija checkpoints con prueba.

Las pruebas también regeneran el inicio de cada secuencia con la semilla registrada para comprobar que es reproducible, y alteran copias temporales del manifiesto para comprobar que el verificador detecta cada tipo de fuga.

Para crear un manifiesto nuevo a partir de otra configuración:

```powershell
uv run python scripts/build_partitions.py build --config configs/partitions/<nuevo>.config.json
```

## 6. Límites

- **Sesgo de certificación.** Solo entran casos que una referencia resolvió. La tasa de éxito de las referencias en estas particiones está inflada por construcción y no prueba que sean eficaces en cualquier posición. El conjunto no representa todas las posiciones transitables.
- **Familias heurísticas.** «Fácil», «intermedio» y «exigente» describen distancia y exposición inicial; no predicen el desempeño de DQN.
- **Edificios conocidos.** Las tres particiones usan los mismos dos edificios. Se mide la generalización a ubicaciones nuevas dentro de edificios conocidos, no a edificios desconocidos.
- **Exposición desigual.** En el desvío térmico, el testigo térmico casi no recibe daño (unos 2 puntos de media), porque los rodeos seguros son accesibles. El conflicto entre distancia y calor en ese edificio se observa sobre todo al comparar con la ruta corta, lo que corresponde a SARB-020 y SARB-021.
- **Alcance pendiente de confirmar.** El objetivo 12 × 12 depende de la confirmación de SARB-002. Si el alcance se reduce, este manifiesto se conserva y se crea otro por perfil.
