"""Catalogo de checkpoints: metadatos y cabecera JSON, nunca deserializa pesos."""
from dataclasses import dataclass
import json
import zlib
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from sar_bot.core import Scenario


@dataclass(frozen=True)
class ModelEntry:
    path: Path
    dimensions: tuple[int, int, int] | None = None
    mode: str = "desconocido"
    observation_size: int = 0
    schema: str = "sin metadatos"
    architecture: str = "desconocida"
    status: str = "piloto / desarrollo"
    error: str | None = None

    def reason(self, scenario):
        if self.error:
            return self.error
        expected = (scenario.width, scenario.height, scenario.victim_count)
        if self.dimensions != expected:
            return f"Requiere {self.dimensions[0]}x{self.dimensions[1]} y {self.dimensions[2]} personas"
        return None


def inspect_model(root, path):
    path = Path(path).resolve()
    try:
        metadata = json.loads((path.parent / "metadata.json").read_text(encoding="utf-8"))
        config = metadata["config"]
        profile = metadata.get("observation_profile")
        if profile is not None:
            if profile["schema_version"] != 2:
                raise ValueError("Esquema de modelo no soportado")
            dimensions = (profile["width"], profile["height"], profile["victims"])
            mode, schema = profile["mode"], "schema_version=2"
        else:
            # Perfiles historicos: dimensiones documentadas por sus entradas
            # de entrenamiento, nunca deducidas solo del largo del vector.
            paths = {p for stage in config["stages"] for p in stage["scenarios"]}
            profiles = set()
            for name in paths:
                source = (Path(root) / name).resolve()
                if not source.is_relative_to(Path(root).resolve()):
                    raise ValueError("Entrada de entrenamiento fuera del proyecto")
                scenario = Scenario.load(source)
                profiles.add((scenario.width, scenario.height, scenario.victim_count))
            if len(profiles) != 1:
                raise ValueError("No hay un perfil historico unico verificable")
            dimensions = profiles.pop()
            mode = config.get("observation_mode", "full")
            schema = "historico: version no declarada"
        if any(type(v) is not int or v < 1 for v in dimensions) or mode not in ("full", "sensors"):
            raise ValueError("Perfil de observacion invalido")
        with ZipFile(path) as archive:
            info = archive.getinfo("data")
            if info.file_size > 2_000_000:
                raise ValueError("Cabecera del checkpoint demasiado grande")
            if info.flag_bits & 1:
                raise ValueError("Checkpoint ZIP cifrado: se requiere un archivo sin contrasena")
            try:
                header = archive.read("data")
            except NotImplementedError as error:
                raise ValueError("Compresion del checkpoint no soportada") from error
            except RuntimeError as error:
                if "password" in str(error).lower() or "encrypted" in str(error).lower():
                    raise ValueError("Checkpoint ZIP cifrado: no se puede abrir sin contrasena") from error
                raise
            data = json.loads(header)
        shape = data["observation_space"]["_shape"]
        if len(shape) != 1 or type(shape[0]) is not int or type(data["action_space"]["n"]) not in (int, str) or str(data["action_space"]["n"]) != "25":
            raise ValueError("Espacios del checkpoint no soportados")
        if profile is not None and (profile["observation_size"] != shape[0] or profile["actions"] != 25):
            raise ValueError("Metadatos y checkpoint no coinciden")
        embedded = data.get("sar_bot_profile")
        if embedded is not None and profile is not None:
            for key in ("schema_version", "width", "height", "victims", "mode", "observation_size", "actions"):
                if embedded.get(key) != profile[key]:
                    raise ValueError("Perfil del checkpoint distinto de sus metadatos")
        # La API publica determina el esquema actual; no se duplica su formula.
        from sar_bot.env import RescueEnv
        if shape[0] != RescueEnv.observation_size(*dimensions, mode):
            raise ValueError("El vector no coincide con el perfil declarado")
        architecture = "MLP " + str(config["dqn"]["policy_kwargs"]["net_arch"])
        return ModelEntry(path, dimensions, mode, shape[0], schema, architecture)
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, BadZipFile, zlib.error, EOFError, ImportError) as error:
        if isinstance(error, FileNotFoundError):
            message = "Falta model.zip o metadata.json en la carpeta seleccionada"
        elif isinstance(error, PermissionError):
            message = "No se puede leer el modelo o sus metadatos. Revisa permisos"
        else:
            message = str(error)[:100]
        return ModelEntry(path, error="Modelo no verificable: " + message)


def discover_models(root, extra=None):
    paths = set((Path(root) / "artifacts").glob("*/model.zip"))
    if extra is not None:
        paths.add(Path(extra))
    return tuple(inspect_model(root, p) for p in sorted({p.resolve() for p in paths}))
