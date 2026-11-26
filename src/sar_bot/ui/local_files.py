"""Publicacion local completa y sin reemplazo: enlace atomico en el mismo volumen."""
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile


@contextmanager
def atomic_text(path, validate):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".sarbot-", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        validate(temporary)
        # os.link fails if the destination exists; unlike replace(), it cannot overwrite.
        # Both names share an already closed, validated file. Unsupported filesystems fail safely.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
