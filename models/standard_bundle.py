from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class StandardBundle(BaseModel):
    model_config = ConfigDict(extra="allow")

    bundle_id: str
    bundle_name: str
    version: str
    meta: dict[str, Any]
    standards_registry: list[dict[str, Any]]
    structure_schema: dict[str, Any]
    entity_types: list[dict[str, Any]]
    variable_semantics: list[dict[str, Any]]
    unit_dictionary: dict[str, Any]
    alias_sets: dict[str, Any]
    rules: dict[str, Any]
    output_contract: dict[str, Any]
    review_policy: dict[str, Any]

    @model_validator(mode="after")
    def validate_bundle_contract(self) -> "StandardBundle":
        if not self.bundle_id.strip() or not self.bundle_name.strip() or not self.version.strip():
            raise ValueError("bundle_id, bundle_name and version must not be empty")
        if not self.standards_registry:
            raise ValueError("standards_registry must declare at least one source standard")
        for source in self.standards_registry:
            for field_name in ("standard_id", "edition", "uri", "scope"):
                if not str(source.get(field_name, "")).strip():
                    raise ValueError(f"Each standards_registry entry requires {field_name}")
                standard_ids = {str(source["standard_id"]) for source in self.standards_registry}

        required_levels = {"Site", "Area", "Line", "Equipment", "Variable"}
        levels = self.structure_schema.get("levels", [])
        if not required_levels.issubset(set(levels)):
            raise ValueError("structure_schema.levels must include Site, Area, Line, Equipment and Variable")
        level_definitions = self.structure_schema.get("level_definitions", {})
        if not required_levels.issubset(set(level_definitions)):
            raise ValueError("structure_schema.level_definitions must define all required hierarchy levels")
        required_artifacts = {"standard_model.json", "mapping_results.json", "review_queue.json", "unmapped_nodes.json", "result_package.json"}
        if not required_artifacts.issubset(set(self.output_contract.get("required_artifacts", []))):
            raise ValueError("output_contract.required_artifacts must include all mandatory JSON artifacts")

        codes: set[str] = set()
        for collection_name, entries in (("entity_types", self.entity_types), ("variable_semantics", self.variable_semantics)):
            for entry in entries:
                code = str(entry.get("code", "")).strip()
                if not code:
                    raise ValueError(f"Every {collection_name} entry requires a non-empty code")
                if code in codes:
                    raise ValueError(f"Bundle candidate code is duplicated: {code}")
                codes.add(code)
                if not str(entry.get("definition", "")).strip():
                    raise ValueError(f"{collection_name} entry {code} requires a definition")
                for list_field in ("aliases", "regex", "data_types", "units", "source_references"):
                    values = entry.get(list_field, [])
                    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                        raise ValueError(f"{collection_name}.{code}.{list_field} must be a list of strings")
                status = str(entry.get("status", "active")).casefold()
                if status not in {"active", "inactive", "deprecated", "retired", "draft"}:
                    raise ValueError(f"{collection_name}.{code}.status has unsupported value: {status}")
                node_classes = entry.get("node_classes", [])
                allowed_node_classes = {"object", "variable", "method", "objecttype", "variabletype", "datatype", "referencetype"}
                if not isinstance(node_classes, list) or any(str(value).casefold() not in allowed_node_classes for value in node_classes):
                    raise ValueError(f"{collection_name}.{code}.node_classes contains an unsupported node class")
                unknown_sources = set(entry.get("source_references", [])) - standard_ids
                if unknown_sources:
                    raise ValueError(f"{collection_name} entry {code} references unknown standards: {sorted(unknown_sources)}")

        unknown_alias_codes = set(self.alias_sets) - codes
        if unknown_alias_codes:
            raise ValueError(f"alias_sets contains undeclared codes: {sorted(unknown_alias_codes)}")
        for code, aliases in self.alias_sets.items():
            if not isinstance(aliases, list) or not all(isinstance(alias, str) and alias.strip() for alias in aliases):
                raise ValueError(f"alias_sets.{code} must be a list of non-empty strings")

        weights = self.rules.get("score_weights", {})
        expected_weights = {"alias", "regex", "datatype", "unit", "parent", "sibling"}
        if set(weights) != expected_weights:
            raise ValueError(f"rules.score_weights must define exactly {sorted(expected_weights)}")
        numeric_weights = [float(value) for value in weights.values()]
        if any(not math.isfinite(value) or value < 0 for value in numeric_weights) or sum(numeric_weights) <= 0:
            raise ValueError("rules.score_weights must be finite, non-negative and have a positive total")
        top_k = self.rules.get("top_k")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
            raise ValueError("rules.top_k must be a positive integer")
        allowed_constraints = {"data_type", "engineering_unit", "parent_entity"}
        if not set(self.rules.get("hard_constraints", [])).issubset(allowed_constraints):
            raise ValueError(f"rules.hard_constraints may contain only {sorted(allowed_constraints)}")
        for rule_name in ("missing_evidence_score", "semantic_ambiguity_margin"):
            value = float(self.rules.get(rule_name, float("nan")))
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"rules.{rule_name} must be finite and within [0, 1]")

        policy = self.review_policy
        allowed_review_triggers = {"semantic ambiguity", "candidate tie", "unit or data-type conflict", "unresolved parent", "synthetic hierarchy fallback", "bundle_gap", "semantic fallback"}
        review_triggers = policy.get("mandatory_review_triggers", [])
        if not isinstance(review_triggers, list) or not set(review_triggers).issubset(allowed_review_triggers):
            raise ValueError("review_policy.mandatory_review_triggers contains unsupported trigger names")
        thresholds = [float(policy.get(key, float("nan"))) for key in ("reject_threshold", "review_threshold", "auto_accept_threshold")]
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in thresholds):
            raise ValueError("review_policy thresholds must be finite values in [0, 1]")
        if thresholds != sorted(thresholds):
            raise ValueError("review thresholds must satisfy reject <= review <= auto_accept")
        return self

    @classmethod
    def load(cls, path: str | Path) -> "StandardBundle":
        bundle_path = Path(path)
        if not bundle_path.is_file():
            raise FileNotFoundError(f"Standard bundle not found: {bundle_path}")
        try:
            raw = json.loads(bundle_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid bundle JSON in {bundle_path}: {exc}") from exc
        return cls.model_validate(raw)