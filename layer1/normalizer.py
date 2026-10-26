from __future__ import annotations

import re


def normalize_node_id(value: str) -> str:
    return value.strip()


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]