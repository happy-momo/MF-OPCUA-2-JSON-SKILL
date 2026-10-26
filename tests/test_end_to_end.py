import json
from pathlib import Path

from runner import run


ROOT = Path(__file__).resolve().parents[1]


def test_example_config_runs_end_to_end(tmp_path):
    result = run(ROOT / "examples" / "input.json", tmp_path)
    assert result["status"] == "success"
    assert result["run_info"]["run_id"]
    assert result["summary"]["node_count"] >= 5
    for name in ("standard_model", "mapping_results", "review_queue", "unmapped_nodes", "canonical_model"):
        path = Path(result["outputs"][name])
        assert path.is_file()
        json.loads(path.read_text(encoding="utf-8"))
    standard = json.loads(Path(result["outputs"]["standard_model"]).read_text(encoding="utf-8"))
    assert standard["sites"]
    assert standard["sites"][0]["synthetic"] is True
    manifest = json.loads(Path(result["outputs"]["result_package"]).read_text(encoding="utf-8"))
    assert manifest["outputs"]["result_package"] == result["outputs"]["result_package"]
    assert manifest["run_info"]["run_id"] == result["run_info"]["run_id"]

    mapping = json.loads(Path(result["outputs"]["mapping_results"]).read_text(encoding="utf-8"))
    mapped_equipment = [row for row in mapping["node_results"] if row["entity_resolution"]["selected_candidate"]]
    assert all("synthetic hierarchy fallback" in row["review_triggers"] for row in mapped_equipment)