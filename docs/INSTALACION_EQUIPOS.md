# Ejecución de la base en los cuatro equipos (SARB-003)

**Coordina:** persona 4. **Revisa:** persona 1. **Actualización:** 18 de noviembre de 2026.

Cada integrante instala la base desde el mismo commit con el lockfile, abre la interfaz sin entrenar y reproduce las cifras de referencia. Esta tabla reúne las cuatro comprobaciones. La de la persona 4 ya está hecha; las otras tres se completan con los mismos pasos (sección 3).

## 1. Comprobaciones

Commit común: `df029d72f42c5f7dc8320d0a6d93d1a25eb2a657` (punta de `feature/simulation-core`, que incluye el PR de la persona 2).

| Integrante | Sistema | Python | Instalación | Pruebas | Pasillo con DQN | V2 térmica | V2 ruta corta | Interfaz | Fecha |
|---|---|---|---|---|---|---|---|---|---|
| Persona 4 | Windows 11 (10.0.26200) | 3.12.16 (gestionado por `uv`) | Clon limpio, `uv sync --locked --extra ui --extra rl --python 3.12`, 29 s | 98 de 98, OK | 2/2, 22 pasos, daño 0 | 3/3, 62 pasos, daño 64 | 3/3, 58 pasos, daño 107 | Abre sin entrenar ([captura](images/sarb003_persona4_ui.png)) | 2026-11-18 |
| Persona 1 | Pendiente | | | | | | | | |
| Persona 2 | Pendiente | | | | | | | | |
| Persona 3 | Pendiente | | | | | | | | |

Valores esperados: el pasillo compartido con `artifacts/sensors_dqn/model.zip` da dos rescates en 22 pasos con daño 0. En `scenarios/v2/building_10x10.json`, la térmica da tres rescates en 62 pasos con daño total 64, y la ruta corta tres rescates en 58 pasos con daño 107.

### Detalle de la persona 4

- **Versiones instaladas por el lockfile:** gymnasium 1.4.0, stable-baselines3 2.9.2, torch 2.15.0+cpu, numpy 2.5.4 y pygame 2.6.1. `uv` resolvió 38 paquetes y descargó CPython 3.12.16 (21 MiB) y torch (121 MiB).
- **Interfaz:** `scripts/ui.py --headless --steps 22 --screenshot ...` terminó con `"outcome": "success", "rescued": 2`. La captura muestra «Rescate completo», 2/2 personas, 22/100 pasos y daño 0 con «DQN entrenado».
- **Rama de la persona 4:** en el mismo entorno limpio, el commit `8ccb90b` de `feature/persona4-evaluacion` pasa sus 262 pruebas. La copia de trabajo previa, creada con pip y Python 3.11.9, pasa las 266 pruebas de `5b05b8d`. Python 3.11, declarado en `pyproject.toml`, también funciona.

## 2. Incidencias encontradas y correcciones

| Incidencia real | Efecto | Corrección |
|---|---|---|
| `uv` no estaba instalado en el equipo de la persona 4 | `uv sync` no se podía ejecutar | Se instaló con `python -m pip install uv`, que la documentación de `uv` admite junto al instalador oficial. Se agregó a la guía del equipo. |
| La copia de trabajo ya tenía un `.venv` creado con pip y Python 3.11 | `uv sync --python 3.12` habría recreado ese entorno, quitando lo instalado a mano | La comprobación se hizo en un clon limpio. En la guía: hacer la primera instalación en un clon nuevo o aceptar que `uv` recree `.venv`. |
| En Git Bash, la salida con tildes aparece con símbolos extraños («est� �ntegro») | Solo estético; los archivos se escriben en UTF-8 | Usar PowerShell o Windows Terminal, o definir `PYTHONIOENCODING=utf-8`. |

## 3. Pasos para completar una fila

```powershell
git clone https://github.com/MelannyJutinico/SAR-Bot.git sarbot-comprobacion
cd sarbot-comprobacion
git checkout df029d72f42c5f7dc8320d0a6d93d1a25eb2a657
uv sync --locked --extra ui --extra rl --python 3.12
uv run --locked --extra ui --extra rl python -c "import sys, platform; print(sys.version, platform.platform())"
uv run --locked --extra ui --extra rl python -m unittest discover -s tests
uv run --locked --extra rl python scripts/demo.py --strategy dqn --model artifacts/sensors_dqn/model.zip --scenario scenarios/pasillo_compartido.json --json
uv run --locked --extra rl python scripts/demo.py --strategy thermal --scenario scenarios/v2/building_10x10.json --json
uv run --locked --extra rl python scripts/demo.py --strategy shortest --scenario scenarios/v2/building_10x10.json --json
uv run --locked --extra ui --extra rl python scripts/ui.py --scenario scenarios/v2/building_10x10.json --strategy thermal
```

La última línea de cada `demo.py --json` contiene `steps`, `outcome`, `rescued` y el daño de cada robot. Se copian a la fila junto con el sistema, la versión de Python, el resultado de las pruebas y cualquier incidencia. Si una cifra no coincide, se anota tal cual y se avisa a la persona 1; no se corrige la tabla para que coincida.
