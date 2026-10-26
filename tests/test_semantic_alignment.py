from pathlib import Path

import pytest

from layer1.parser import parse_nodeset
from layer2.mapper import map_model
from layer2.semantic_response_parser import SemanticResponseError, parse_semantic_response
from models.standard_bundle import StandardBundle


ROOT = Path(__file__).resolve().parents[1]


def _bundle():
    return StandardBundle.load(ROOT / "config" / "default_bundle.json")


def _low_score_node():
    model = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    node = next(item for item in model.nodes if item.browse_name.endswith("T_Out_102"))
    node.data_type = "i=1"
    node.engineering_unit = "bar"
    return model, node


def test_semantic_off_and_host_unavailable_fall_back():
    model = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    bundle = _bundle()
    result = map_model(model, bundle, "off")
    variable = next(row for row in result["node_results"] if row["source_node"]["node_class"] == "Variable")
    assert variable["semantic_resolution"]["fallback_triggered"] is False
    unavailable = map_model(model, bundle, "assist")
    assert all(not row["semantic_resolution"]["semantic_alignment_used"] for row in unavailable["node_results"])


def test_semantic_adapter_can_rerank_low_confidence_candidate():
    model, target = _low_score_node()
    bundle = _bundle()
    allowed = "OutletTemperature"

    def adapter(prompt: str):
        assert allowed in prompt
        return {"selected_candidate": {"code": allowed, "confidence": 0.87, "reasoning": ["Description identifies outlet temperature."]}, "top_k_candidates": [{"code": allowed, "confidence": 0.87}], "needs_review": False}

    result = map_model(model, bundle, "assist", adapter)
    row = next(item for item in result["node_results"] if item["source_node"]["node_id"] == target.node_id)
    assert row["semantic_resolution"]["semantic_alignment_used"] is True
    assert row["semantic_resolution"]["semantic_reasoning"]
    assert row["semantic_resolution"]["fallback_triggered"] is False


@pytest.mark.parametrize("response", ["not json", {"selected_candidate": {"code": "MadeUp", "confidence": 0.9, "reasoning": ["bad"]}}])
def test_invalid_response_falls_back(response):
    model, target = _low_score_node()
    result = map_model(model, _bundle(), "assist", lambda _: response)
    row = next(item for item in result["node_results"] if item["source_node"]["node_id"] == target.node_id)
    assert row["semantic_resolution"]["fallback_triggered"] is True
    assert row["semantic_resolution"]["semantic_alignment_used"] is False


def test_high_confidence_baseline_is_protected():
    model = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    bundle = _bundle()
    called = False

    def adapter(_):
        nonlocal called
        called = True
        return {}

    map_model(model, bundle, "enhanced", adapter)
    assert called is False


def test_candidate_tie_forces_review_even_when_baseline_is_high():
    model = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    bundle = _bundle()
    outlet = next(item for item in bundle.variable_semantics if item["code"] == "OutletTemperature")
    temperature = next(item for item in bundle.variable_semantics if item["code"] == "Temperature")
    for field in ("aliases", "regex", "data_types", "units", "compatible_entities", "sibling_hints"):
        temperature[field] = list(outlet[field])
    bundle.alias_sets["Temperature"] = list(bundle.alias_sets["OutletTemperature"])

    result = map_model(model, bundle, "off")
    row = next(item for item in result["node_results"] if item["source_node"]["browse_name"].endswith("T_Out_102"))
    assert "candidate tie" in row["review_triggers"]
    assert row["final_selection"]["status"] == "needs_review"


def test_response_parser_rejects_out_of_range_confidence():
    with pytest.raises(SemanticResponseError):
        parse_semantic_response({"selected_candidate": {"code": "Pressure", "confidence": 1.2, "reasoning": ["x"]}}, {"Pressure"})