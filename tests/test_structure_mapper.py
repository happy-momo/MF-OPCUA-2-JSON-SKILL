from pathlib import Path

from layer1.parser import parse_nodeset
from layer2.mapper import map_model
from layer2.review_splitter import classify
from layer2.scorer import score_candidate
from layer2.standard_model_builder import build_standard_model
from layer2.structure_mapper import map_level
from models.standard_bundle import StandardBundle


ROOT = Path(__file__).resolve().parents[1]


def test_score_breakdown_and_review_thresholds():
    result = score_candidate({"browse_name": "Pump", "data_type": None}, {"code": "Pump", "aliases": ["pump"]}, {})
    assert set(result["score_breakdown"]) == {"alias", "regex", "datatype", "unit", "parent", "sibling"}
    assert result["score"] == 0.8
    policy = {"auto_accept_threshold": 0.9, "review_threshold": 0.65, "reject_threshold": 0.4}
    assert classify(0.9, policy, True) == "auto_accepted"
    assert classify(0.65, policy, True) == "needs_review"
    assert classify(0.5, policy, True) == "unmapped"
    assert classify(0.39, policy, True) == "rejected"
    assert classify(None, policy, False) == "unmapped"
    assert map_level("Variable", None) == "Variable"


def test_strict_mode_excludes_mappings_blocked_by_synthetic_hierarchy():
    canonical = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    bundle = StandardBundle.load(ROOT / "config" / "default_bundle.json")
    mapping = map_model(canonical, bundle, run_mode="strict")
    standard = build_standard_model(canonical, mapping["node_results"], bundle, "strict")

    assert standard.sites == []
    assert standard.unassigned_equipment == []
    assert standard.unassigned_variables == []