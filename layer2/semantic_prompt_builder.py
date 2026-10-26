from __future__ import annotations

import json


def build_semantic_prompt(features: dict, parent_resolution: dict | None, siblings: list[str], candidates: list[dict], bundle) -> str:
    valid_codes = {item["code"] for item in bundle.variable_semantics}
    candidate_codes = {candidate["code"] for candidate in candidates}
    concepts = {item["code"]: item for item in bundle.variable_semantics if item["code"] in valid_codes}
    definitions = {
        code: {
            "label": item.get("label", code),
            "definition": item.get("definition", item.get("description", "")),
            "aliases": item.get("aliases", []),
            "quantity_kind": item.get("quantity_kind"),
            "physical_dimension": item.get("physical_dimension"),
            "data_types": item.get("data_types", []),
            "units": item.get("units", []),
            "compatible_entities": item.get("compatible_entities", []),
            "measurement_role": item.get("measurement_role"),
            "direction": item.get("direction"),
            "source_references": item.get("source_references", []),
        }
        for code, item in concepts.items()
    }
    payload = {
        "task": "Select and rank the most plausible standard variable semantic from the valid bundle concepts. Return one JSON object with selected_candidate {code, confidence, reasoning}, top_k_candidates, and needs_review.",
        "allowed_candidate_codes": sorted(valid_codes),
        "node": {key: features.get(key) for key in ("browse_name", "display_name", "description", "data_type", "engineering_unit", "path")},
        "parent_entity": parent_resolution,
        "siblings": siblings[:20],
        "rule_candidates": sorted(candidates[:5], key=lambda item: (-item.get("score", 0), item.get("code", ""))),
        "bundle_definitions": definitions,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))