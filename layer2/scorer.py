from __future__ import annotations

import re
from typing import Any

from utils.regex_utils import matches_any
from utils.text_normalizer import normalize_text
from utils.token_utils import tokens


DEFAULT_WEIGHTS = {"alias": 0.30, "regex": 0.20, "datatype": 0.10, "unit": 0.10, "parent": 0.20, "sibling": 0.10}


def _aliases(entry: dict[str, Any], alias_sets: dict[str, Any]) -> list[str]:
    values = list(entry.get("aliases", []))
    extra = alias_sets.get(entry.get("code", []), [])
    if isinstance(extra, list):
        values.extend(extra)
    return [str(value) for value in values]


def _canonical_unit(value: str, unit_dictionary: dict[str, Any]) -> str:
    stripped = value.strip()
    if stripped in unit_dictionary:
        return stripped
    folded = stripped.casefold()
    for code, definition in unit_dictionary.items():
        aliases = definition if isinstance(definition, list) else definition.get("aliases", [])
        if folded in {str(alias).casefold() for alias in aliases}:
            return code
    return folded


def _canonical_data_type(value: str, aliases: dict[str, str]) -> str:
    normalized = value.casefold().strip()
    normalized = re.sub(r"^ns=\d+;", "", normalized)
    normalized = normalized.split(";")[-1].split("=")[-1]
    return aliases.get(normalized, normalized).casefold()


def eligible_candidates(entries: list[dict], features: dict) -> list[dict]:
    node_class = str(features.get("node_class") or "").casefold()
    eligible = []
    for entry in entries:
        if str(entry.get("status", "active")).casefold() != "active":
            continue
        node_classes = entry.get("node_classes", [])
        if node_classes and node_class not in {str(value).casefold() for value in node_classes}:
            continue
        eligible.append(entry)
    return eligible


def score_candidate(features: dict, entry: dict, alias_sets: dict, weights: dict | None = None, unit_dictionary: dict | None = None, rules: dict | None = None) -> dict:
    weights = weights or DEFAULT_WEIGHTS
    unit_dictionary = unit_dictionary or {}
    rules = rules or {}
    text = " ".join(str(features.get(key) or "") for key in ("browse_name", "display_name", "description", "path"))
    normalized = normalize_text(text)
    candidate_aliases = _aliases(entry, alias_sets)
    alias_hit = any(normalize_text(alias) in normalized for alias in candidate_aliases if normalize_text(alias))
    entry_tokens = set().union(*(tokens(alias) for alias in candidate_aliases)) if candidate_aliases else set()
    node_tokens = tokens(text)
    alias_score = 1.0 if alias_hit else (len(entry_tokens & node_tokens) / len(entry_tokens) if entry_tokens else 0.0)
    regex_score = 1.0 if matches_any(entry.get("regex", []), text) else 0.0

    datatype_aliases = {str(key).casefold(): str(value).casefold() for key, value in rules.get("data_type_aliases", {}).items()}
    expected_types = {_canonical_data_type(str(value), datatype_aliases) for value in entry.get("data_types", [])}
    actual_type = _canonical_data_type(str(features.get("data_type") or ""), datatype_aliases)
    evidence_missing_score = float(rules.get("missing_evidence_score", 0.5))
    datatype_score = evidence_missing_score if not actual_type and expected_types else (1.0 if not expected_types or any(item == actual_type for item in expected_types) else 0.0)

    expected_units = {_canonical_unit(str(value), unit_dictionary) for value in entry.get("units", [])}
    actual_unit = _canonical_unit(str(features.get("engineering_unit") or ""), unit_dictionary)
    unit_score = evidence_missing_score if not actual_unit and expected_units else (1.0 if not expected_units or actual_unit in expected_units else 0.0)

    allowed_parents = {str(value).casefold() for value in entry.get("compatible_entities", entry.get("compatible_parent_codes", []))}
    actual_parent = str(features.get("parent_entity_code") or "").casefold()
    parent_score = evidence_missing_score if not actual_parent and allowed_parents else (1.0 if not allowed_parents or actual_parent in allowed_parents else 0.0)

    sibling_words = set().union(*(tokens(value) for value in features.get("sibling_names", []))) if features.get("sibling_names") else set()
    sibling_hints = entry.get("sibling_hints", [])
    if not sibling_words:
        sibling_score = 1.0
    elif not sibling_hints:
        sibling_score = 0.5
    else:
        sibling_score = 1.0 if any(tokens(hint) & sibling_words for hint in sibling_hints) else 0.0

    breakdown = {"alias": alias_score, "regex": regex_score, "datatype": datatype_score, "unit": unit_score, "parent": parent_score, "sibling": sibling_score}
    total_weight = sum(max(float(weights.get(key, 0)), 0) for key in breakdown)
    score = sum(breakdown[key] * max(float(weights.get(key, 0)), 0) for key in breakdown) / total_weight if total_weight else 0.0
    violations = []
    hard_constraints = set(rules.get("hard_constraints", []))
    if "data_type" in hard_constraints and expected_types and actual_type and datatype_score == 0:
        violations.append("data_type")
    if "engineering_unit" in hard_constraints and expected_units and actual_unit and unit_score == 0:
        violations.append("engineering_unit")
    if "parent_entity" in hard_constraints and allowed_parents and actual_parent and parent_score == 0:
        violations.append("parent_entity")
    return {"code": entry["code"], "label": entry.get("label", entry["code"]), "score": round(score, 4), "score_breakdown": breakdown, "constraint_violations": violations}


def score_candidates(features: dict, entries: list[dict], alias_sets: dict, weights: dict | None = None, unit_dictionary: dict | None = None, rules: dict | None = None) -> list[dict]:
    scored = [score_candidate(features, entry, alias_sets, weights, unit_dictionary, rules) for entry in entries]
    scored = [item for item in scored if not item["constraint_violations"]]
    ordered = sorted(scored, key=lambda item: (-item["score"], item["code"]))
    limit = int((rules or {}).get("top_k", len(ordered)))
    return ordered[:max(limit, 0)]