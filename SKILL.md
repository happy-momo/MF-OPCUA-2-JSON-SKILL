---
name: opcua-nodeset-to-standard-json
description: "Convert OPC UA NodeSet2 XML into a bundle-constrained standard JSON package, then independently audit semantic mappings, hierarchy, units, and evidence as the invoking agent. Use when a user supplies a NodeSet2 XML, asks for standard-model conversion, or requests mapping review."
---

# OPC UA NodeSet2 to Standard JSON

## Purpose and Responsibility Boundary

This skill converts an OPC UA NodeSet2 XML into a canonical model, a deterministic bundle-constrained mapping, and review artifacts. The invoking agent then performs the semantic review using its own reasoning capability and reports findings. The Python project does not call an AI model, agent API, external LLM service, or subprocess; do not request or configure API keys, providers, endpoints, or model credentials.

The deterministic converter is responsible for extracting source facts, generating permitted candidates, scoring them, applying configured rules, and preserving an audit trail. The invoking agent is responsible for checking whether the selected meanings and hierarchy are actually supported by the source context and the declared target-standard profile. The agent must not silently turn its interpretation into an authoritative standard code.

The bundle is the allowlist and semantic contract. Never invent target codes. If no bundle candidate is defensible, leave the node unmapped and report the missing concept or needed bundle extension.

## Invocation Boundaries

Invoke this skill when the user provides or references an OPC UA NodeSet2 XML (`UANodeSet`) and asks to convert it, map it to a target profile, validate the conversion, or review existing NodeSet mappings. Strong cues include `NodeSet2`, `UANodeSet`, OPC UA information model export, bundle-constrained mapping, and OPC UA standard JSON.

Do not invoke it for generic XML-to-JSON conversion, arbitrary OPC UA questions without a NodeSet conversion or mapping task, live-server browsing, or standard modeling with no NodeSet source. If the user asks only to review existing converter artifacts, do not rerun conversion unless inputs or bundle changed; perform the artifact audit and report the run identity.

Inputs may include an explicit standard bundle, a target-standard profile, or only the repository's configured default bundle.

Before running:

1. Locate the NodeSet2 XML, run configuration, and intended bundle. Prefer the user's explicit target standard and bundle over repository examples.
2. Read the bundle's `standards_registry`, `structure_schema`, `entity_types`, `variable_semantics`, `unit_dictionary`, `rules`, and `review_policy` before interpreting a result.
3. If the target standard or required output contract is materially ambiguous, ask a focused question. Do not treat the demonstration bundle as an authoritative industrial standard.
4. Preserve user files. Use a new run-specific output directory, not a shared output directory that can mix results from separate runs. Never write over the source XML, run configuration, or bundle.

## Conversion Workflow

1. Run the deterministic converter using the supplied configuration, normally:

   ```text
   python <absolute-project-path>/runner.py --input <absolute-config-path> --output-dir <absolute-project-path>/outputs/<run-id>
   ```

   The config argument is resolved from the current working directory. Paths inside the config are resolved from the project root, not from the config file's directory. From another working directory, use absolute paths for the runner and config; keep the config's XML and bundle paths project-root-relative or absolute. Use the workspace's configured Python environment. Do not send the full XML to an AI model.

2. Confirm the command succeeded and inspect `result_package.json`. Verify the bundle ID/version, run mode, node and status counts, review-trigger counts, and that every path in `outputs` exists. Confirm `result_package` is listed in its own manifest. A successful process exit alone is not sufficient.
3. Read `mapping_results.json`, `review_queue.json`, `unmapped_nodes.json`, and `standard_model.json`. Read `canonical_model.json` when present; otherwise use mapping records' `source_node` and `preprocessed_features`. Inspect `review_triggers` and `constraint_conflicts`; a high score does not override a mandatory review trigger.
4. Perform the agent semantic audit below over every mapped or review-required node. Do not sample only a few records. Prioritize `needs_review`, `unmapped`, low scores, close candidate ties, unit/type conflicts, and any semantic fallback; still spot-check auto-accepted records for systematic errors.
5. Return the generated package paths and a concise review report. If the environment supports writing review artifacts and the user expects a persisted audit, write `agent_review.json` beside the package; otherwise report the same information in the response. Keep the agent verdict separate from converter status and never change mapping results or the standard model silently as part of review.

For a persisted audit, use a stable structure with `schema_version`, `run_id`, `source_file`, `bundle_id`, `bundle_version`, `reviewed_count`, and `findings`. Each finding should include `node_id`, `converter_status`, `selected_code`, `score`, `verdict`, `evidence`, `conflicts`, and `recommended_code` (null unless recommending an existing bundle code). Allowed verdicts are `confirmed`, `incorrect`, `ambiguous`, `insufficient_evidence`, and `bundle_gap`.

## Agent Semantic Audit

For each reviewed node, compare the source evidence against the selected bundle concept and the next-best candidates:

- Name evidence: `BrowseName`, `DisplayName`, and `Description`; distinguish abbreviations and direction/position qualifiers such as inlet/outlet, suction/discharge, actual/setpoint, and measured/commanded.
- OPC UA evidence: `NodeClass`, `DataType`, `ValueRank`, access level, parent path, reference types, and the surrounding equipment model. Do not infer a semantic type from a tag alone when the type definition or context contradicts it.
- Physical meaning: quantity kind, measurement direction/role, expected data type, engineering unit, and compatible parent entity. A dimensional or unit mismatch is a substantive warning, not a cosmetic alias difference.
- Context: parent equipment type and sibling signals. Check whether the interpretation fits the equipment and whether a sibling pattern suggests a different concept.
- Bundle contract: selected code must exist in the loaded bundle, must be valid for the node class and parent, and must satisfy any mandatory data-type/unit constraints. A human-readable label is not a substitute for a code.
- Confidence and disposition: distinguish model score from semantic certainty. Recommend `confirmed`, `incorrect`, `ambiguous`, `insufficient_evidence`, or `bundle_gap`; cite NodeId and the evidence that supports the finding.

When the agent finds a likely correction, suggest only an existing bundle code. If the right concept is absent, identify the proposed concept in prose as a bundle-gap suggestion, not as a mapped output. A review recommendation does not change the converter's recorded `final_selection` unless the user explicitly requests a revised mapping run.

## Standards and Provenance Policy

Use standards as traceable sources, not as decorative labels. Read the bundle's exact edition, identifier, URI, profile, and applicability note. A code or hierarchy mapping is standards-backed only when the bundle records a precise source identifier and the mapping scope is supported by that source.

The project may use these standards families where applicable:

- OPC UA Core specifications: OPC 10000-3 (Address Space Model), OPC 10000-5 (Information Model), and OPC 10000-6 (Mappings) for NodeSet facts and OPC UA modeling semantics.
- IEC 62264 / ISA-95, including the equipment hierarchy concepts, when the target profile adopts them. `Site`, `Area`, `Line`, and `Equipment` are this project's stable output levels; do not claim that every level name is a direct one-to-one IEC 62264 class. Record explicit profile mappings and any project-specific `Line` interpretation.
- UCUM for machine-readable unit codes where the target profile uses UCUM. Preserve the source unit, normalized code, and alias evidence. Do not claim full UCUM grammar validation or unit conversion unless an implementation actually performs it.
- OPC UA companion specifications, such as the OPC UA for Pumps and Vacuum Pumps specification, only when the source model and target profile are in scope for that specification.

Do not reproduce copyrighted standard clauses. Store identifiers, edition, official landing-page URI, short scope notes, profile-specific mappings, and local interpretation notes. Distinguish normative mappings from local/demo mappings. If a standard edition or code has not been verified from an authoritative source, mark it unverified and require review.

## Bundle Design Contract

`standard_bundle` is versioned, offline, and explicit. A bundle should contain:

- `standards_registry`: authoritative source identifiers, editions, URIs, scope, applicability, and mapping provenance.
- `structure_schema`: stable output levels, definitions, allowed parent levels, source hierarchy terms, profile mapping notes, and fallback behavior for absent source levels.
- `entity_types`: unique code, preferred label, definition, aliases, patterns, allowed node classes, parent constraints, source references, and lifecycle/status metadata as relevant.
- `variable_semantics`: unique code, definition, aliases/patterns, quantity kind, physical dimension, OPC UA data-type constraints, UCUM unit codes, equipment compatibility, measurement role/direction, and source references.
- `unit_dictionary`: canonical unit code, code system, quantity kind/dimension where known, aliases, and explicit conversion metadata only when conversion is implemented and verified. Unknown units remain unknown; never guess a conversion.
- `alias_sets`: aliases keyed only by declared bundle codes.
- `rules`: score weights, missing-evidence policy, candidate limits, data-type aliases, enabled hard constraints, conflict rules, and explainable rule identifiers.
- `review_policy`: validated score thresholds, precedence, mandatory review triggers, and documented strict-mode behavior.
- `output_contract`: output schema/version, required artifacts, and code/level constraints.

Keep the core required output levels stable: `Site`, `Area`, `Line`, `Equipment`, and `Variable`. Additional source or target hierarchy levels may be represented through explicit profile mappings; they must not silently change the base output contract.

## Runtime Modes and Outputs

The command-line runner supports `fast`, `review`, and `strict` run modes and `off`, `assist`, and `enhanced` semantic modes. In this design, semantic modes refer only to an optional caller-injected adapter if one is explicitly available; the ordinary skill workflow uses the invoking agent's separate post-run audit. The agent's review must not be represented as an adapter call in `mapping_results.json`.

Required generated artifacts are `standard_model.json`, `mapping_results.json`, `review_queue.json`, `unmapped_nodes.json`, and `result_package.json`; `canonical_model.json` is optional when requested. Verify the package rather than assuming a successful process wrote every artifact. The result package's `semantic_alignment_used` count, if present, refers only to the in-process adapter, not the invoking agent's audit.

Review statuses are `auto_accepted`, `needs_review`, `unmapped`, and `rejected`. Treat these as converter decisions, not the agent audit verdict. Synthetic hierarchy containers are explicitly marked and are not standard codes. In strict mode, only `auto_accepted` mappings are eligible for `standard_model`; absent or unaccepted equipment parents must not be presented as resolved hierarchy. The agent should identify the source NodeId, converter status, selected code, score, evidence, and recommended disposition.

## Safety, Limits, and Error Handling

- Never overwrite the source XML or supplied bundle.
- Never bypass the loaded bundle allowlist, whether in code output or agent recommendations.
- Do not claim standards conformance, certification, or full unit conversion from a demonstration bundle.
- Do not infer missing facts as though they appeared in the NodeSet. Clearly label contextual inferences.
- If parsing, bundle validation, or export fails, stop semantic review of incomplete artifacts, report the actionable error, and do not present partial output as a successful conversion.
- If mappings are ambiguous or the bundle lacks a concept, preserve the ambiguity and ask for the target-standard decision needed to proceed.

## Project Maintenance Requests

When the user asks to change this project rather than convert a NodeSet, inspect the relevant implementation, bundle, tests, and docs first. State a local behavior hypothesis and a focused check, make scoped changes, run the narrowest relevant tests, then run the full suite when feasible. Preserve existing user changes and report exact validation results.