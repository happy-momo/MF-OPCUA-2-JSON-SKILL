from __future__ import annotations

from pathlib import Path

from exporters.json_exporter import write_json


def package_results(output_dir: str | Path, standard_model, mapping_results: dict, canonical_model, options: dict) -> dict:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    required_options = ("include_mapping_results", "include_review_queue", "include_unmapped_nodes")
    disabled_required = [name for name in required_options if options.get(name, True) is False]
    if disabled_required:
        raise ValueError(f"Required artifacts cannot be disabled: {', '.join(disabled_required)}")
    outputs = {
        "standard_model": target / "standard_model.json",
        "mapping_results": target / "mapping_results.json",
        "review_queue": target / "review_queue.json",
        "unmapped_nodes": target / "unmapped_nodes.json",
        "result_package": target / "result_package.json",
    }
    write_json(outputs["standard_model"], standard_model)
    write_json(outputs["mapping_results"], mapping_results)
    write_json(outputs["review_queue"], mapping_results["review_queue"])
    write_json(outputs["unmapped_nodes"], [row for row in mapping_results["node_results"] if row["final_selection"]["status"] in {"unmapped", "rejected"}])
    if options.get("include_canonical_model", True):
        outputs["canonical_model"] = target / "canonical_model.json"
        write_json(outputs["canonical_model"], canonical_model)
    return {"status": "success", "run_info": mapping_results["run_info"], "summary": mapping_results["summary"], "outputs": {key: str(path) for key, path in outputs.items()}}