# OPC UA NodeSet2 to Standard JSON

Offline Python project that parses NodeSet2 XML deterministically, builds a canonical model, and maps nodes only to entries in a validated standard bundle. The invoking agent owns the post-run semantic audit using its normal reasoning capability. The Python converter does not call an AI model or external model API; it emits baseline mappings and audit evidence for the agent to inspect.

## Layout

- `layer1/`: XML parsing, reference recovery and canonical paths.
- `layer2/`: bundle-constrained features, matching, scoring, review and semantic response validation.
- `models/`: Pydantic v2 data contracts.
- `exporters/`: atomic JSON writing and output package creation.
- `config/`, `examples/`, `tests/`: offline bundle, sample NodeSet2, invocation config and test coverage.

## Agent Workflow

Use [SKILL.md](SKILL.md) as the invocation contract. The skill is intended for NodeSet2 conversion and mapping review, not generic XML conversion or live-server browsing. The agent checks every non-auto-accepted, unmapped, or rejected result, verifies selected concepts against source type/unit/hierarchy/context, and reports its verdict separately from the generated mapping. The agent must not silently rewrite converter outputs or invent codes outside the selected bundle.

The demonstration bundle records source references to OPC UA Core, IEC 62264/ISA-95 concepts, UCUM, and the OPC UA Pumps companion specification. Those references provide provenance and design context; the sample concepts are local examples, not an official vocabulary or conformance claim. UCUM aliases are normalized from the bundle table, but the converter is not a full UCUM parser or unit-conversion engine.

## Install

Python 3.11+ is required.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

Run from this directory:

```powershell
python runner.py --input examples/input.json --output-dir outputs/example-run
```

Files are written under `outputs/`: `standard_model.json`, `mapping_results.json`, `review_queue.json`, `unmapped_nodes.json`, optional `canonical_model.json`, and `result_package.json`. For repeated or concurrent runs, pass a unique `--output-dir`; the package manifest lists all output paths, including itself. The config file argument is relative to the current working directory, while input XML and bundle paths inside it are relative to the project root.

The current profile does not infer `Site`, `Area`, or `Line` from source nodes. It labels these containers as synthetic, records the fallback in metadata, and requires equipment mappings using that fallback to be reviewed. Strict mode therefore omits those mappings unless a future profile adds an explicit source hierarchy mapping.

The input JSON selects the NodeSet XML, bundle, run mode (`fast`, `review`, or `strict`) and optional in-process adapter mode (`off`, `assist`, `enhanced`). In the ordinary skill workflow, set semantic alignment to `off`: the invoking agent performs its audit after the baseline run rather than through a Python adapter. `fast` disables adapter calls; `review` applies configured review thresholds; `strict` accepts only mappings at the auto-accept threshold. Adapter modes exist only for an explicitly supplied host integration, are not required by the project, and do not represent the invoking agent's review.

## Test

```powershell
python -m pytest
```

The tests use local fixtures and deterministic fake adapter responses; no network, OPC UA server, or external model API is required.