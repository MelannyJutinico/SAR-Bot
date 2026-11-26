# Comprobación real de protección de aprendizaje

Se ejecutó una misión nueva del conjunto de entrenamiento con el modelo base congelado, en una sesión aislada de `outputs/guard_checks/`. No se entrenó ni evaluó sobre prueba reservada.

La candidata se entrenó durante 64 actualizaciones. En los seis casos fijos de control de entrenamiento obtuvo:

| Métrica | Antes | Candidata |
|---|---:|---:|
| Misiones completas | 0 | 0 |
| Personas entregadas | 5 | 0 |
| Retorno acumulado | −1442 | −1760 |

Se rechazaron los pesos candidatos. Los parámetros Q después de guardar fueron idénticos a los del modelo anterior; se conservaron 280 experiencias y una misión procesada. El artefacto base permaneció intacto. `check.json` contiene hashes, identidades de controles, contadores y resultado del guardado.

Reproducir en otra sesión aislada:

```powershell
uv run --locked --extra rl python scripts/check_learning_guard.py --output outputs/learning-guard.json
```

Esta protección compara puntuación agregada y solo evita regresiones detectadas en esos controles; no garantiza mejora en cada caso ni generalización. Los controles no se usan para gradientes. Los nuevos pesos se aceptan si mantienen o mejoran la tupla de misiones completas, entregas y retorno, en ese orden. Una comprobación fallida recupera pesos y optimizador anteriores, guardando la experiencia.
