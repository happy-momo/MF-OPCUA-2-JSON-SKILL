from __future__ import annotations

from layer2.scorer import eligible_candidates, score_candidates


def map_variable(features: dict, bundle) -> list[dict]:
    entries = eligible_candidates(bundle.variable_semantics, features)
    return score_candidates(features, entries, bundle.alias_sets, bundle.rules.get("score_weights"), bundle.unit_dictionary, bundle.rules)