from __future__ import annotations


def map_level(node_class: str, code: str | None) -> str:
    if node_class == "Variable":
        return "Variable"
    if code:
        return "Equipment"
    return "Equipment"