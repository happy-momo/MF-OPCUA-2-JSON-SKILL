import json
import pytest

from exporters.result_packager import package_results
from models.standard_model import StandardModel


def test_package_writes_required_outputs(tmp_path):
    mapping = {"run_info": {}, "summary": {}, "review_queue": {"unmapped": []}, "node_results": []}
    model = StandardModel(standard_id="b", bundle_version="1", sites=[])
    package = package_results(tmp_path, model, mapping, {"model_info": {}, "nodes": []}, {"include_canonical_model": True})
    assert set(package["outputs"]) >= {"standard_model", "mapping_results", "review_queue", "unmapped_nodes", "result_package", "canonical_model"}
    for key, name in package["outputs"].items():
        if key == "result_package":
            continue
        assert json.loads(__import__("pathlib").Path(name).read_text(encoding="utf-8")) is not None


def test_package_rejects_disabling_required_artifacts(tmp_path):
    mapping = {"run_info": {}, "summary": {}, "review_queue": {"unmapped": []}, "node_results": []}
    model = StandardModel(standard_id="b", bundle_version="1", sites=[])
    with pytest.raises(ValueError, match="Required artifacts cannot be disabled"):
        package_results(tmp_path, model, mapping, {"model_info": {}, "nodes": []}, {"include_review_queue": False})


def test_package_can_omit_optional_canonical_artifact(tmp_path):
    mapping = {"run_info": {}, "summary": {}, "review_queue": {"unmapped": []}, "node_results": []}
    model = StandardModel(standard_id="b", bundle_version="1", sites=[])
    package = package_results(tmp_path, model, mapping, {"model_info": {}, "nodes": []}, {"include_canonical_model": False})
    assert "canonical_model" not in package["outputs"]