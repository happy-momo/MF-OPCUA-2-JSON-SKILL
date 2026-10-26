from __future__ import annotations

from pathlib import Path


def resolve_from(base: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else (base / candidate).resolve()