from __future__ import annotations


def baseline_resolution(candidates: list[dict], reason: str, semantic_mode: str) -> dict:
    selected = candidates[0] if candidates else None
    return {
        "candidate_mappings": candidates,
        "selected_candidate": selected,
        "semantic_alignment_used": False,
        "semantic_mode": semantic_mode,
        "semantic_candidates": [],
        "semantic_reasoning": [],
        "semantic_score": None,
        "fallback_triggered": True,
        "fallback_reason": reason,
    }