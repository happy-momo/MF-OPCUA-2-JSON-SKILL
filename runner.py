from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from uuid import uuid4

from exporters.json_exporter import write_json
from exporters.result_packager import package_results
from layer1.parser import parse_nodeset
from layer2.mapper import map_model
from layer2.standard_model_builder import build_standard_model
from models.standard_bundle import StandardBundle
from utils.file_utils import resolve_from


PROJECT_ROOT = Path(__file__).resolve().parent
LOGGER = logging.getLogger("opcua_nodeset_to_standard_json")


def run(input_path: str | Path, output_dir: str | Path | None = None, semantic_adapter=None) -> dict:
    input_file = Path(input_path).resolve()
    if not input_file.is_file():
        raise FileNotFoundError(f"Input configuration not found: {input_file}")
    try:
        config = json.loads(input_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid input JSON: {exc}") from exc

    input_xml = resolve_from(PROJECT_ROOT, config["input_file"]["path"])
    bundle_config = config["target_standard"]
    bundle_path = resolve_from(PROJECT_ROOT, bundle_config["bundle_path"])
    bundle = StandardBundle.load(bundle_path)
    if bundle.bundle_id != bundle_config["bundle_id"]:
        raise ValueError(f"Configured bundle_id {bundle_config['bundle_id']!r} does not match bundle {bundle.bundle_id!r}")

    options = config.get("options", {})
    mode = options.get("mode", "review")
    semantic_mode = options.get("semantic_mode", "off")
    if mode not in {"fast", "review", "strict"}:
        raise ValueError(f"Unsupported mode: {mode}")
    if semantic_mode not in {"off", "assist", "enhanced"}:
        raise ValueError(f"Unsupported semantic_mode: {semantic_mode}")
    if not options.get("enable_semantic_alignment", False):
        semantic_mode = "off"
    if mode == "fast":
        semantic_mode = "off"

    canonical = parse_nodeset(input_xml)
    mapping = map_model(canonical, bundle, semantic_mode=semantic_mode, semantic_adapter=semantic_adapter, run_mode=mode)
    mapping["run_info"] = {
        "run_id": uuid4().hex,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(input_xml),
        "bundle_id": bundle.bundle_id,
        "bundle_version": bundle.version,
        "mode": mode,
        "semantic_mode": semantic_mode,
        "semantic_adapter_available": semantic_adapter is not None,
    }
    mapping["summary"]["semantic_alignment_used_count"] = sum(row["semantic_resolution"]["semantic_alignment_used"] for row in mapping["node_results"])
    standard_model = build_standard_model(canonical, mapping["node_results"], bundle, mode)
    destination = Path(output_dir) if output_dir else PROJECT_ROOT / "outputs"
    if not destination.is_absolute():
        destination = PROJECT_ROOT / destination
    package = package_results(destination, standard_model, mapping, canonical, options)
    package["run_info"] = mapping["run_info"]
    package["summary"] = mapping["summary"]
    write_json(destination / "result_package.json", package)
    LOGGER.info("Converted %d nodes; %d mapped", mapping["summary"]["node_count"], mapping["summary"]["mapped_count"])
    return package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert OPC UA NodeSet2 XML into bundle-constrained standard JSON")
    parser.add_argument("--input", required=True, help="Path to JSON run configuration")
    parser.add_argument("--output-dir", help="Override output directory")
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        result = run(arguments.input, arguments.output_dir)
    except (OSError, ValueError, KeyError) as exc:
        LOGGER.error("Conversion failed: %s", exc)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())