import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from layer2.unit_normalizer import normalize_unit
from models.standard_bundle import StandardBundle


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("relative_path", ["config/default_bundle.json", "examples/sample_bundle.json"])
def test_standard_bundles_include_provenance_and_load(relative_path):
    bundle = StandardBundle.load(ROOT / relative_path)
    assert bundle.standards_registry
    assert {"Site", "Area", "Line", "Equipment", "Variable"}.issubset(bundle.structure_schema["levels"])
    assert bundle.output_contract["required_artifacts"]


def _raw_default_bundle():
    return json.loads((ROOT / "config" / "default_bundle.json").read_text(encoding="utf-8"))


def test_missing_standards_registry_is_rejected():
    data = _raw_default_bundle()
    del data["standards_registry"]
    with pytest.raises(ValidationError):
        StandardBundle.model_validate(data)


def test_invalid_score_weights_are_rejected():
    data = _raw_default_bundle()
    data["rules"]["score_weights"]["alias"] = -0.1
    with pytest.raises(ValidationError, match="score_weights"):
        StandardBundle.model_validate(data)


def test_invalid_review_threshold_order_is_rejected():
    data = _raw_default_bundle()
    data["review_policy"]["reject_threshold"] = 0.8
    with pytest.raises(ValidationError, match="reject <= review <= auto_accept"):
        StandardBundle.model_validate(data)


def test_unknown_standard_reference_is_rejected():
    data = _raw_default_bundle()
    data["variable_semantics"][0]["source_references"].append("UNREGISTERED-SOURCE")
    with pytest.raises(ValidationError, match="unknown standards"):
        StandardBundle.model_validate(data)


def test_unsupported_candidate_status_and_node_class_are_rejected():
    data = _raw_default_bundle()
    data["entity_types"][0]["status"] = "preferred"
    with pytest.raises(ValidationError, match="unsupported value"):
        StandardBundle.model_validate(data)

    data = _raw_default_bundle()
    data["variable_semantics"][0]["node_classes"] = ["UnknownNodeClass"]
    with pytest.raises(ValidationError, match="unsupported node class"):
        StandardBundle.model_validate(data)


def test_unit_normalization_preserves_case_sensitive_canonical_codes():
    bundle = StandardBundle.load(ROOT / "config" / "default_bundle.json")
    assert normalize_unit("degC", bundle.unit_dictionary) == "Cel"
    assert normalize_unit("Pa", bundle.unit_dictionary) == "Pa"
    assert normalize_unit("pa", bundle.unit_dictionary) == "pa"