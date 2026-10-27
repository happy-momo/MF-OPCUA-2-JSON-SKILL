# OPC UA NodeSet2 to Standard JSON -  Traceable semantic alignment and information-model transformation for manufacturing systems

Chinese version: [README.zh-CN.md](README.zh-CN.md)

A manufacturing-focused Agent Skill for OPC UA semantic alignment and information-model transformation. It helps bridge vendor-specific NodeSet2 XML and a selected, versioned target profile: extracting source-model facts, mapping equipment and process signals to bundle concepts, and producing traceable JSON evidence for agent-led review.

The project is designed for traceability rather than blind automation. It does not call an external model API or require an online service. Instead, it emits explainable outputs that can be reviewed after each run.

## Contents

- [Why this project exists](#why-this-project-exists)
- [Key capabilities](#key-capabilities)
- [Install the skill for an agent](#install-the-skill-for-an-agent)
- [How the agent uses this skill](#how-the-agent-uses-this-skill)
- [Architecture and implementation](#architecture-and-implementation)
- [Agent workflow and acceptance criteria](#agent-workflow-and-acceptance-criteria)
- [Manual CLI use](#manual-cli-use)
- [Inputs and output contract](#inputs-and-output-contract)
- [Generated artifacts](#generated-artifacts)
- [Customize and extend](#customize-and-extend)
- [Testing](#testing)
- [Limitations](#safety-and-limits)
- [License](#license)

## Why this project exists

Manufacturing environments bring together equipment, control systems, and information models from different vendors and generations. Even when systems use OPC UA, names, type definitions, hierarchy, and engineering units can differ enough to make cross-system integration, asset-model reuse, and trustworthy analytics labor-intensive.

This Skill gives an agent a repeatable way to turn a NodeSet2 export into a profile-specific, reviewable mapping package. Its value for manufacturing teams is to:

- **Reduce repetitive integration work** by extracting source facts and organizing candidate mappings in a consistent workflow.
- **Make semantics easier to reuse** by aligning equipment and process signals to an explicit target bundle rather than relying on vendor-specific names alone.
- **Expose data-quality risks early** by surfacing missing concepts, uncertain hierarchy, candidate ambiguity, and unit or data-type conflicts for review.
- **Improve traceability** by retaining source NodeIds, mapping evidence, bundle versions, and run metadata in machine-readable outputs.
- **Keep engineering decisions under control** by separating deterministic conversion from agent or human validation, and by never inventing target codes.

The result is an auditable starting point for manufacturing data harmonization—not an automatic certification of a model, a replacement for domain experts, or a guarantee of conformance to a standard. Mapping quality depends on the source NodeSet and the completeness and provenance of the selected bundle.

## Key capabilities

- Offline NodeSet2 parsing and canonicalization
- Bundle-constrained entity and variable mapping
- Rule-based candidate scoring and conflict detection
- Hierarchy fallback and synthetic container labeling
- Unit and data-type conflict reporting
- Review queue generation for ambiguous nodes
- Agent-oriented semantic review workflow
- Output package generation for downstream auditing

## Project structure

- `layer1/`: parsing, reference resolution, canonical path generation, source-fact extraction
- `layer2/`: feature extraction, scoring, candidate selection, review generation, semantic alignment adapter hooks
- `models/`: validated bundle and model contracts
- `exporters/`: JSON writing, manifest generation, result packaging
- `config/`: bundle and runtime configuration
- `examples/`: sample XML and invocation JSON files
- `tests/`: regression and behavior validation
- `utils/`: shared normalization and path helpers
- `runner.py`: command-line entrypoint
- `SKILL.md`: invocation contract and review boundaries

## Install the skill for an agent

This repository is an **Agent Skill package with a Python implementation**, not an installable Python distribution. Installing the skill makes its instructions discoverable to a compatible agent; preparing the Python environment is a separate step the agent performs when it needs to run a conversion.

### VS Code / GitHub Copilot

VS Code discovers workspace skills in `.github/skills/`, `.claude/skills/`, or `.agents/skills/`, and personal skills in `~/.copilot/skills/`, `~/.claude/skills/`, or `~/.agents/skills/`. The skill directory must contain `SKILL.md` directly. This repository keeps `SKILL.md`, `runner.py`, `layer1/`, `layer2/`, `models/`, and the other runtime files together at its root, so install the **whole repository** as the skill directory; do not put an extra project subdirectory between the skill directory and `SKILL.md`. See the [VS Code Agent Skills documentation](https://code.visualstudio.com/docs/agent-customization/agent-skills) for current discovery behavior.

For example, from the host workspace root, a workspace-level installation is:

```powershell
git clone https://github.com/happy-momo/OPCUA2graph.git .github/skills/opcua-nodeset-to-standard-json
```

Alternatively, use VS Code's **Chat: Open Customizations** command, select **Skills**, and create or manage a workspace or user skill. If installing this repository manually through that UI, copy the repository contents into the skill directory so that `SKILL.md` is at its root.

For other skills-compatible agents, use that agent's documented skill directory and discovery rules. The skill format is portable, but installation locations and supported features are host-specific. After installation, reload or refresh the agent's skill list if required, and check that `opcua-nodeset-to-standard-json` is discoverable.

### Python runtime used by the agent

The agent should first inspect the available Python environment and reuse the workspace's configured interpreter when its dependencies are present. If they are missing, create an isolated environment in the skill directory and install the declared requirements; avoid changing the user's global Python environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

On macOS or Linux, use `python3 -m venv .venv` and `.venv/bin/python -m pip install -r requirements.txt`. The runtime requires Python 3.11+ and the packages in [requirements.txt](requirements.txt). Conversion itself is offline after dependencies are installed; no model API key or OPC UA server is required.

## How the agent uses this skill

The user supplies or points the agent to a NodeSet2 XML and requests conversion, mapping, or review. The agent—not the user—performs the repository, environment, and command-line steps:

1. **Recognize and scope the task.** Load this skill for NodeSet2 conversion or mapping-review requests. Do not use it for generic XML conversion, live-server browsing, or unrelated OPC UA questions.
2. **Find inputs and establish the target.** Locate the XML, any existing run configuration, and the intended standard bundle. Prefer user-supplied files over examples. If the target profile or required output is unclear, ask before mapping.
3. **Prepare execution.** Check Python 3.11+ and the required packages. Reuse an existing suitable interpreter or prepare the isolated environment above. Do not ask the user to run setup commands unless they prefer to do so.
4. **Configure and run safely.** Reuse a matching supplied config or create a run-specific config and output directory. Never overwrite source XML, user config, or bundle. Keep semantic alignment off in the ordinary skill workflow; the agent performs its audit after conversion.
5. **Verify artifacts before interpreting them.** Check the process result and `result_package.json`, including run identity, bundle ID/version, mode, counts, and every listed output path. Stop and report errors if parsing, validation, or export failed.
6. **Audit the mappings.** Read the mapping evidence, review queue, unmapped results, standard model, and canonical model when present. Compare candidate codes with the source NodeId, names, data type, unit, parent/sibling context, hierarchy, and bundle constraints.
7. **Deliver a traceable result.** Report output paths, bundle/run identity, status totals, material findings, unresolved questions, and the agent verdict separately from converter status. Write `agent_review.json` beside the run package when a persisted audit is requested or expected. Do not silently edit converter outputs.

The normative, detailed instructions are in [SKILL.md](SKILL.md). The agent should follow that file if this overview and the skill instructions differ.

## Architecture and implementation

The implementation is a staged Python pipeline with explicit data contracts:

1. **Load and validate inputs** — `runner.py` reads the run configuration, loads the target bundle through `StandardBundle`, validates its schema and policy, and checks that the configured bundle ID matches.
2. **Parse NodeSet2** — `layer1/` reads the XML `UANodeSet`, extracts supported node facts (IDs, classes, names, descriptions, data types, engineering units, and references), resolves parent relationships, and builds canonical paths. It does not claim full OPC UA NodeSet schema validation.
3. **Build evidence and candidates** — `layer2/` derives node, parent, and sibling features; generates entity or variable candidates from the bundle allowlist; and scores candidates using configured aliases, patterns, data types, units, and context.
4. **Classify and preserve review evidence** — the mapper records candidate scores, selected codes, conflicts, normalized units, review triggers, and converter statuses. Mandatory triggers can require review even when a score crosses the auto-accept threshold.
5. **Build and package results** — the standard-model builder applies the selected run mode, while `exporters/` writes JSON artifacts and a self-referencing package manifest.
6. **Audit separately** — the invoking agent or a human checks source context against the bundle and reports a separate verdict. The audit must not silently rewrite the converter output.

The bundle in `config/default_bundle.json` is explicitly a **demonstration profile** (`conformance_claim: none`), not an authoritative industrial vocabulary. Use a reviewed, versioned bundle for production semantics.

## Design philosophy

This project follows a strict separation of responsibilities:

1. Deterministic converter
   - reads the NodeSet
   - extracts source facts
   - scores candidate mappings
   - preserves evidence in structured outputs

2. Invoking agent or reviewer
   - checks the selected concept against source context
   - validates hierarchy, unit, data type, and parent compatibility
   - decides whether the mapping is confirmed, ambiguous, or unsupported

3. Bundle as an allowlist
   - only known standardized concepts are valid candidates
   - no silent invention of new target codes
   - unsupported concepts remain unmapped or require bundle extension

This philosophy is explicitly described in `SKILL.md`. The Python implementation does not call an LLM or external model service during the conversion step; the agent review happens after conversion, using the generated artifacts as evidence.

## Runtime workflow

The Agent owns the operational flow:

1. Locate the user's NodeSet and the intended target bundle; ask only when a required decision is unclear.
2. Prepare or reuse a suitable Python environment and run config without modifying user inputs.
3. Run `runner.py` into a unique output directory and verify the result manifest.
4. Review the generated evidence and audit mappings against the source and bundle.
5. Return artifact paths and findings, keeping the agent verdict separate from converter status.

This is a review-first workflow, not a blind auto-accept pipeline.

## Agent workflow and acceptance criteria

The agent should follow these gates for each run:

### Before running

- Confirm the source is NodeSet2 XML and select the intended target profile. Prefer the user's bundle; the repository's default bundle is a demonstration profile and is not an authoritative industrial standard.
- Read the bundle's standards registry, structure schema, entity and variable concepts, unit dictionary, scoring rules, review policy, and output contract. Ask a focused question if the standard or required output is materially ambiguous.
- Use a unique run directory. Preserve all user inputs, and do not send the full NodeSet XML to an external model or service.

### Conversion and verification

- Run the deterministic converter using the selected workspace Python environment and a matching config.
- Verify every path in `result_package.json`, including the manifest's self-reference, before treating the run as successful.
- Treat converter statuses (`auto_accepted`, `needs_review`, `unmapped`, `rejected`) as machine decisions, not as the agent's semantic verdict.
- Audit every mapped or review-required node. Prioritize low scores, close candidate ties, unit/type conflicts, unresolved parents, synthetic hierarchy, and bundle gaps; also check auto-accepted mappings for systematic errors.

### Review and delivery

- Check source NodeId, name and description, NodeClass, data type, ValueRank, access level, units, references, parent path, sibling context, candidate alternatives, hard constraints, and the exact loaded bundle code.
- Recommend only codes already declared by the bundle. If the concept is absent, report a bundle gap instead of inventing a code.
- Use the verdicts `confirmed`, `incorrect`, `ambiguous`, `insufficient_evidence`, or `bundle_gap`. Keep them separate from converter status and do not silently rewrite its outputs.
- Report the run ID, source, bundle/version, mode, output locations, summary counts, material findings, and limitations. Persist `agent_review.json` when requested or expected.
- On any parse, bundle-validation, or export error, stop and report the actionable error; do not characterize partial files as a successful run.

See [SKILL.md](SKILL.md) for the full audit checklist and `agent_review.json` shape.

## Manual CLI use

Agents normally run the converter as part of the Skill workflow. This section is for maintainers, diagnostics, and users who explicitly want to invoke the deterministic converter themselves. First install the runtime dependencies as described above.

Run a sample conversion:

```powershell
.\.venv\Scripts\python.exe runner.py --input examples/input.json --output-dir outputs/example-run
```

Or use a project configuration with a custom NodeSet:

```powershell
.\.venv\Scripts\python.exe runner.py --input examples/factory_multiline_input.json --output-dir outputs/factory_multiline_run
```

If the virtual environment is activated, `python runner.py ...` works as well. On macOS/Linux, use `.venv/bin/python runner.py ...`.

`--input` points to a JSON run configuration. The configuration's `input_file.path` and `target_standard.bundle_path` are resolved relative to the project root; a relative `--output-dir` is also rooted at the project. The run-configuration path itself is resolved from the current working directory, so pass an absolute path when invoking the runner from elsewhere.

## Inputs and output contract

### Run configuration

The JSON configuration selects:

- source XML file
- target bundle path
- bundle ID
- runtime mode
- optional semantic mode
- which optional artifacts to include

The sample is [examples/input.json](examples/input.json). Required artifacts cannot be disabled. `include_canonical_model` defaults to `true`.

### Supported run modes

- `fast`: deterministic conversion with semantic alignment forced off.
- `review`: review-oriented conversion using the bundle thresholds. The default bundle uses `0.90` for auto-accept, `0.65` for review, and `0.40` for rejection; mandatory review triggers still take precedence.
- `strict`: uses the auto-accept threshold as the acceptance boundary. Only `auto_accepted` records are eligible for the standard model; all other records remain available in audit outputs.

### Semantic modes

- `off`: no adapter-based semantic enhancement
- `assist` and `enhanced`: optional in-process adapter modes for callers that explicitly inject an adapter through the Python API.

The command-line runner does not inject an adapter or call an external model. In the ordinary skill workflow, keep semantic alignment off and let the invoking agent perform the separate post-run audit.

## Generated artifacts

Each run writes a package of artifacts under the selected output directory, including:

- `standard_model.json`
- `mapping_results.json`
- `review_queue.json`
- `unmapped_nodes.json`
- `result_package.json`
- optional `canonical_model.json`

The package manifest records the output files and metadata, including run ID, source file, bundle version, mode, and summary counts.

## Customize and extend

Choose the smallest extension point that matches the change:

### Add or tune a target profile (no Python changes)

Create a versioned bundle JSON following the contract in [SKILL.md](SKILL.md) and the schema enforced by [standard_bundle.py](models/standard_bundle.py). Define provenance, hierarchy, entity and variable codes, aliases, data-type and unit constraints, scoring rules, review thresholds, and required outputs. Every selectable code must be declared in the bundle; keep demonstration concepts clearly labeled. Point a run config's `target_standard.bundle_path` and `bundle_id` at the new bundle, then add bundle-validation and end-to-end fixtures.

### Change deterministic conversion behavior

Use the existing stages rather than adding logic to `runner.py` indiscriminately:

- XML facts and supported NodeSet nodes: `layer1/parser.py` and the canonical contracts in `models/canonical_model.py`.
- Name normalization, references, hierarchy paths: the corresponding `layer1/` modules and `utils/`.
- Features and candidate scoring: `layer2/feature_builder.py`, `layer2/entity_mapper.py`, `layer2/variable_mapper.py`, and `layer2/scorer.py`.
- Statuses and review triggers: `layer2/review_splitter.py`, `layer2/mapper.py`, and bundle `review_policy`.
- Output structure and manifests: `layer2/standard_model_builder.py` and `exporters/`.

Add or update focused tests under `tests/`, preserve stable source evidence and output contracts, update `SKILL.md` if agent behavior changes, and update both READMEs when public behavior or setup changes.

### Add an optional semantic adapter

The Python API accepts an explicitly injected callable adapter through `run(..., semantic_adapter=...)`. It receives a prompt string and must return a JSON string or object that passes the validation in `layer2/semantic_response_parser.py`. The CLI does not configure an adapter, and the standard Agent Skill flow keeps this feature off; do not introduce hidden network calls or credentials into the converter.

### Validate and contribute

Run `python -m pytest` from the project root. Tests use local fixtures and deterministic fake adapters; they do not require an OPC UA server or model API. Keep changes scoped, avoid committing generated run output or local environments, and document any deliberate output-contract change.

## Review model and audit behavior

The converter records evidence, not conclusions alone. For each node, the output captures:

- source node metadata
- extracted features and tokens
- candidate mappings
- selected mapping and score
- review triggers
- structure and unit conflicts
- normalized unit information
- final review status

This makes it possible for an agent to answer questions such as:

- Why was this node mapped to this concept instead of a sibling concept?
- Did the parent object and sibling signals support the selection?
- Was a unit or data-type conflict present?
- Was the hierarchy synthetic rather than explicit?

## Standards and provenance expectations

The bundle is treated as an explicit, versioned semantic contract. It may reference:

- OPC UA Core specifications
- IEC 62264 / ISA-95 concepts
- UCUM unit references where applicable
- OPC UA companion specifications when in scope

However, the project is intentionally offline and traceable. It does not claim conformance beyond the bundle and source evidence that were actually loaded.

## Safety and limits

This project is conservative by design:

- it never invents bundle codes silently
- it preserves ambiguity instead of forcing a guess
- it records synthetic hierarchy containers explicitly
- it requires review for ambiguous or conflicting mappings
- it avoids presenting incomplete artifacts as valid output

If no defensible concept exists in the bundle, the node should remain unmapped or be flagged as a bundle-gap candidate for human review.

## Testing

```powershell
python -m pytest
```

The test suite uses local fixtures and deterministic fake adapter responses. No network access, OPC UA server, or remote model API is required.

## Contribution and reuse

This project is designed to be adapted by teams that need:

- plant hierarchy normalization
- OPC UA semantic mapping review
- bundle-driven industrial data harmonization
- traceable, evidence-based mapping outputs

Contributions are welcome when they improve determinism, evidence quality, bundle coverage, or review clarity.

## Summary

This project is best understood as a deterministic OPC UA mapping pipeline with an explicit agent-review layer. It provides machine-readable evidence, review-oriented outputs, and a disciplined semantic workflow that is suitable for industrial data-model harmonization and human-in-the-loop auditing.
