from __future__ import annotations

from .text_normalizer import normalize_text


def tokens(value: str | None) -> set[str]:
    return {part for part in normalize_text(value).split() if len(part) > 1}