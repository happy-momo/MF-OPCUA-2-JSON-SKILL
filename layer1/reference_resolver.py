from __future__ import annotations

from .normalizer import local_name


PARENT_REFERENCE_TYPES = {"HasComponent", "Organizes", "HasProperty", "HasOrderedComponent"}


def parent_candidates(node_elements: list[tuple[str, object]]) -> dict[str, str]:
    parents: dict[str, str] = {}
    for source_id, element in node_elements:
        for reference in element:
            if local_name(reference.tag) != "References":
                continue
            for item in reference:
                ref_type = item.attrib.get("ReferenceType", "").rsplit("i=", 1)[-1]
                if item.attrib.get("IsForward", "true").lower() == "false" and ref_type in PARENT_REFERENCE_TYPES:
                    parents[source_id] = (item.text or "").strip()
    return parents