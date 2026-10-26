from __future__ import annotations

import json
from typing import Any


class SemanticResponseError(ValueError):
    pass


def parse_semantic_response(response: str | dict[str, Any], allowed_codes: set[str]) -> dict[str, Any]:
    try:
        data = json.loads(response) if isinstance(response, str) else response
    except (json.JSONDecodeError, TypeError) as exc:
        raise SemanticResponseError(f"Invalid semantic JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SemanticResponseError("Semantic response must be a JSON object")
    selected = data.get("selected_candidate")
    if not isinstance(selected, dict) or selected.get("code") not in allowed_codes:
        raise SemanticResponseError("Selected semantic candidate is not in the allowed candidate set")
    confidence = selected.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        raise SemanticResponseError("Selected candidate confidence must be between 0 and 1")
    reasoning = selected.get("reasoning")
    if not isinstance(reasoning, list) or not reasoning or not all(isinstance(item, str) and item.strip() for item in reasoning):
        raise SemanticResponseError("Selected candidate reasoning must be a non-empty list of strings")
    ranked = data.get("top_k_candidates", [])
    if not isinstance(ranked, list):
        raise SemanticResponseError("top_k_candidates must be a list")
    checked = []
    for candidate in ranked:
        if not isinstance(candidate, dict) or candidate.get("code") not in allowed_codes:
            raise SemanticResponseError("Top-K contains a candidate outside the allowed set")
        score = candidate.get("confidence")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 1:
            raise SemanticResponseError("Top-K candidate confidence must be between 0 and 1")
        checked.append({"code": candidate["code"], "confidence": float(score)})
    return {
        "selected_candidate": {"code": selected["code"], "confidence": float(confidence), "reasoning": reasoning},
        "top_k_candidates": checked,
        "needs_review": bool(data.get("needs_review", False)),
    }