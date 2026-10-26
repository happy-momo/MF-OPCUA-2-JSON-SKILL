from __future__ import annotations


def normalize_unit(unit: str | None, unit_dictionary: dict) -> str | None:
    if not unit:
        return None
    source = unit.strip()
    if source in unit_dictionary:
        return source
    folded = source.casefold()
    for canonical, values in unit_dictionary.items():
        aliases = values if isinstance(values, list) else values.get("aliases", [])
        if folded in {str(alias).casefold() for alias in aliases}:
            return canonical
    return source