from __future__ import annotations


def classify(score: float | None, policy: dict, selected: bool) -> str:
    if not selected:
        return "unmapped"
    auto = float(policy.get("auto_accept_threshold", 0.9))
    review = float(policy.get("review_threshold", 0.65))
    reject = float(policy.get("reject_threshold", 0.4))
    score = float(score or 0.0)
    if score >= auto:
        return "auto_accepted"
    if score >= review:
        return "needs_review"
    if score < reject:
        return "rejected"
    return "unmapped"