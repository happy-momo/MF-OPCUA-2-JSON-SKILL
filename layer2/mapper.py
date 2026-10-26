from __future__ import annotations

from collections import Counter

from layer2.entity_mapper import map_entity
from layer2.feature_builder import build_feature_index, build_features
from layer2.review_splitter import classify
from layer2.unit_normalizer import normalize_unit
from layer2.variable_mapper import map_variable
from layer2.scorer import eligible_candidates, score_candidate
from layer2.semantic_alignment_step import align_semantically


def _review_triggers(node, features: dict, semantic: dict, candidates: list[dict], selected: dict | None, parent_resolution: dict | None, constraint_conflicts: list[dict], bundle) -> list[str]:
    policy_triggers = set(bundle.review_policy.get("mandatory_review_triggers", []))
    triggered = []
    ambiguity_margin = float(bundle.rules.get("semantic_ambiguity_margin", 0.1))
    if "candidate tie" in policy_triggers and len(candidates) > 1:
        if candidates[0]["score"] - candidates[1]["score"] <= ambiguity_margin:
            triggered.append("candidate tie")
            triggered.append("semantic ambiguity")
    if "semantic fallback" in policy_triggers and semantic.get("fallback_triggered"):
        triggered.append("semantic fallback")
    if "unresolved parent" in policy_triggers and node.parent_node_id and not parent_resolution:
        triggered.append("unresolved parent")
    if "synthetic hierarchy fallback" in policy_triggers and node.node_class == "Object" and selected:
        triggered.append("synthetic hierarchy fallback")
    if "bundle_gap" in policy_triggers and node.node_class in {"Object", "Variable"} and not candidates:
        triggered.append("bundle_gap")
    breakdown = (selected or {}).get("score_breakdown", {})
    if "unit or data-type conflict" in policy_triggers:
        has_score_conflict = (features.get("engineering_unit") and breakdown.get("unit") == 0) or (features.get("data_type") and breakdown.get("datatype") == 0)
        has_hard_conflict = any(set(item["constraint_violations"]) & {"data_type", "engineering_unit"} for item in constraint_conflicts)
        if has_score_conflict or has_hard_conflict:
            triggered.append("unit or data-type conflict")
    if semantic.get("needs_review"):
        triggered.append("semantic ambiguity")
    return list(dict.fromkeys(triggered))


def map_model(canonical, bundle, semantic_mode: str = "off", semantic_adapter=None, run_mode: str = "review") -> dict:
    entity_choices: dict[str, dict | None] = {}
    records = []
    review_groups = {"auto_accepted": [], "needs_review": [], "unmapped": [], "rejected": []}
    feature_index = build_feature_index(canonical)

    ordered_nodes = sorted(canonical.nodes, key=lambda item: (item.path.count("/"), item.path, item.node_id))
    for node in ordered_nodes:
        features = build_features(node, canonical, feature_index)
        parent_resolution = entity_choices.get(node.parent_node_id or "")
        if parent_resolution:
            features["parent_entity_code"] = parent_resolution["code"]
            features["parent_entity_confidence"] = parent_resolution["score"]
        entity_candidates = map_entity(features, bundle) if node.node_class == "Object" else []
        entity_selected = entity_candidates[0] if entity_candidates else None

        variable_candidates = map_variable(features, bundle) if node.node_class == "Variable" else []
        if node.node_class == "Variable":
            semantic_candidates = variable_candidates or [
                score_candidate(features, entry, bundle.alias_sets, bundle.rules.get("score_weights"), bundle.unit_dictionary, bundle.rules)
                for entry in eligible_candidates(bundle.variable_semantics, features)
            ]
            semantic = align_semantically(features, parent_resolution, features["sibling_names"], semantic_candidates, bundle, semantic_mode, semantic_adapter)
        else:
            semantic = {"candidate_mappings": [], "selected_candidate": None, "semantic_alignment_used": False, "semantic_mode": semantic_mode, "semantic_candidates": [], "semantic_reasoning": [], "semantic_score": None, "fallback_triggered": False}
            semantic_candidates = []
        selected = semantic.get("selected_candidate")
        selected_code = selected.get("code") if selected else (entity_selected or {}).get("code")
        score = selected.get("score") if selected else (entity_selected or {}).get("score")
        relevant_candidates = semantic_candidates if node.node_class == "Variable" else entity_candidates
        selected_candidate = selected if node.node_class == "Variable" else entity_selected
        candidate_entries = bundle.variable_semantics if node.node_class == "Variable" else bundle.entity_types
        eligible_entries = eligible_candidates(candidate_entries, features)
        constraint_conflicts = [
            {"code": entry["code"], "constraint_violations": result["constraint_violations"]}
            for entry in eligible_entries
            if (result := score_candidate(features, entry, bundle.alias_sets, bundle.rules.get("score_weights"), bundle.unit_dictionary, bundle.rules))["constraint_violations"]
            and (result["score_breakdown"]["alias"] > 0 or result["score_breakdown"]["regex"] > 0)
        ]
        review_triggers = _review_triggers(node, features, semantic, relevant_candidates, selected_candidate, parent_resolution, constraint_conflicts, bundle)
        policy = bundle.review_policy
        if run_mode == "strict":
            strict_threshold = float(policy.get("auto_accept_threshold", 0.9))
            policy = {**policy, "review_threshold": strict_threshold, "reject_threshold": strict_threshold}
        status = classify(score, policy, selected_code is not None)
        if selected_code and review_triggers and status in {"auto_accepted", "unmapped"}:
            status = "needs_review"
        if node.node_class == "Object":
            eligible_parent_statuses = {"auto_accepted"} if run_mode == "strict" else {"auto_accepted", "needs_review"}
            entity_choices[node.node_id] = entity_selected if entity_selected and status in eligible_parent_statuses else None
        record = {
            "source_node": node.model_dump(),
            "preprocessed_features": features,
            "entity_resolution": {"candidate_mappings": entity_candidates, "selected_candidate": entity_selected},
            "semantic_resolution": semantic,
            "structure_resolution": {"level": "Variable" if node.node_class == "Variable" else "Equipment", "parent_node_id": node.parent_node_id},
            "final_selection": {"code": selected_code, "score": score, "status": status},
            "review_triggers": review_triggers,
            "constraint_conflicts": constraint_conflicts,
            "review": {"status": status, "required": status != "auto_accepted" or bool(review_triggers)},
            "normalized_unit": normalize_unit(node.engineering_unit, bundle.unit_dictionary),
        }
        records.append(record)
        review_groups[status].append(record)
    counts = Counter(row["final_selection"]["status"] for row in records)
    trigger_counts = Counter(trigger for row in records for trigger in row["review_triggers"])
    selected_count = sum(1 for row in records if row["final_selection"]["code"])
    mapped_count = sum(1 for row in records if row["final_selection"]["code"] and row["final_selection"]["status"] in {"auto_accepted", "needs_review"})
    return {"node_results": records, "review_queue": review_groups, "summary": {"node_count": len(records), "selected_candidate_count": selected_count, "mapped_count": mapped_count, "status_counts": dict(counts), "review_trigger_counts": dict(trigger_counts)}}