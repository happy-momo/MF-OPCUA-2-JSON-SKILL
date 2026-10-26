from __future__ import annotations

from collections.abc import Callable
from typing import Any

from layer2.scorer import score_candidate
from layer2.semantic_fallback import baseline_resolution
from layer2.semantic_prompt_builder import build_semantic_prompt
from layer2.semantic_response_parser import parse_semantic_response


SemanticAdapter = Callable[[str], str | dict[str, Any]]


def align_semantically(features: dict, parent_resolution: dict | None, siblings: list[str], candidates: list[dict], bundle, mode: str, adapter: SemanticAdapter | None, context_consistency: float = 1.0) -> dict:
    if not candidates:
        return baseline_resolution(candidates, "no_rule_candidates", mode)
    baseline = candidates[0]
    has_hard_conflict = bool(baseline.get("constraint_violations"))
    if baseline["score"] >= 0.9 and not has_hard_conflict:
        return {**baseline_resolution(candidates, "high_confidence_baseline_protected", mode), "fallback_triggered": False, "selected_candidate": baseline}
    if mode == "off":
        return {**baseline_resolution(candidates, "semantic_mode_off", mode), "fallback_triggered": False}
    if mode == "assist":
        review_threshold = float(bundle.review_policy.get("review_threshold", 0.65))
        second_score = candidates[1]["score"] if len(candidates) > 1 else 0.0
        ambiguity_margin = float(bundle.rules.get("semantic_ambiguity_margin", 0.1))
        if baseline["score"] >= review_threshold and baseline["score"] - second_score > ambiguity_margin and not has_hard_conflict:
            return {**baseline_resolution(candidates, "assist_policy_skipped_high_confidence", mode), "fallback_triggered": False}
    if adapter is None:
        return baseline_resolution(candidates, "host_semantic_adapter_unavailable", mode)
    try:
        prompt = build_semantic_prompt(features, parent_resolution, siblings, candidates, bundle)
        valid_codes = {item["code"] for item in bundle.variable_semantics}
        parsed = parse_semantic_response(adapter(prompt), valid_codes)
    except Exception as exc:
        return baseline_resolution(candidates, f"semantic_response_rejected: {exc}", mode)

    selected = parsed["selected_candidate"]
    baseline_code = baseline["code"]
    selected_rule = next((item for item in candidates if item["code"] == selected["code"]), None)
    if selected_rule is None:
        bundle_entry = next((item for item in bundle.variable_semantics if item["code"] == selected["code"]), None)
        if bundle_entry is None:
            return baseline_resolution(candidates, f"semantic_response_rejected: unknown selected code {selected['code']!r}", mode)
        selected_rule = score_candidate(features, bundle_entry, bundle.alias_sets, bundle.rules.get("score_weights"), bundle.unit_dictionary, bundle.rules)
    semantic_score = selected["confidence"]
    final_score = 0.60 * selected_rule["score"] + 0.25 * semantic_score + 0.15 * context_consistency
    final_selection = {**selected_rule, "score": round(final_score, 4), "rule_score": selected_rule["score"], "semantic_score": semantic_score, "context_consistency": context_consistency}
    semantic_candidates = parsed["top_k_candidates"] or [{"code": selected["code"], "confidence": semantic_score}]
    return {
        "candidate_mappings": candidates,
        "selected_candidate": final_selection,
        "semantic_alignment_used": True,
        "semantic_mode": mode,
        "semantic_candidates": semantic_candidates,
        "semantic_reasoning": selected["reasoning"],
        "semantic_score": semantic_score,
        "fallback_triggered": False,
        "baseline_candidate_code": baseline_code,
        "needs_review": parsed["needs_review"],
    }