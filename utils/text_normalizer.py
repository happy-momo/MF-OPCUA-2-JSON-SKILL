from __future__ import annotations

import re


def normalize_text(value: str | None) -> str:
    text = (value or "").casefold()
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()