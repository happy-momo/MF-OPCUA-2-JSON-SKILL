from __future__ import annotations

from models.canonical_model import CanonicalModel
from models.standard_model import StandardEquipment, StandardHierarchyNode, StandardModel, StandardVariable


def build_standard_model(canonical: CanonicalModel, results: list[dict], bundle, run_mode: str = "review") -> StandardModel:
    by_id = {node.node_id: node for node in canonical.nodes}
    result_by_id = {row["source_node"]["node_id"]: row for row in results}
    allowed_statuses = {"auto_accepted"} if run_mode == "strict" else {"auto_accepted", "needs_review"}
    equipment: dict[str, StandardEquipment] = {}
    variables_by_parent: dict[str, list[StandardVariable]] = {}
    unassigned_variables: list[StandardVariable] = []
    for node in canonical.nodes:
        row = result_by_id.get(node.node_id, {})
        if row.get("final_selection", {}).get("status") not in allowed_statuses:
            continue
        entity_code = (row.get("entity_resolution", {}).get("selected_candidate") or {}).get("code")
        semantic = row.get("semantic_resolution", {}).get("selected_candidate") or {}
        if node.node_class == "Variable":
            if not semantic.get("code"):
                continue
            variable = StandardVariable(source_node_id=node.node_id, code=semantic.get("code"), name=node.display_name or node.browse_name, value_type=node.data_type, unit=row.get("normalized_unit"), confidence=semantic.get("score", 0.0))
            parent = node.parent_node_id or ""
            if parent in equipment:
                variables_by_parent.setdefault(parent, []).append(variable)
            elif run_mode != "strict":
                unassigned_variables.append(variable)
        elif node.node_class == "Object":
            if entity_code:
                equipment[node.node_id] = StandardEquipment(source_node_id=node.node_id, code=entity_code, name=node.display_name or node.browse_name, equipment_type=entity_code)
    for parent_id, variables in variables_by_parent.items():
        if parent_id in equipment:
            equipment[parent_id].variables.extend(variables)

    site = StandardHierarchyNode(level="Site", name="Unspecified Site (synthetic)", synthetic=True, fallback_reason="No source-to-Site mapping is implemented in this profile.")
    area = StandardHierarchyNode(level="Area", name="Unspecified Area (synthetic)", synthetic=True, fallback_reason="No source-to-Area mapping is implemented in this profile.")
    line = StandardHierarchyNode(level="Line", name="Unspecified Line (synthetic)", synthetic=True, fallback_reason="No source-to-Line mapping is implemented in this profile.")
    equipment_nodes = {
        node_id: StandardHierarchyNode(level="Equipment", source_node_id=node_id, code=item.code, name=item.name, equipment=item)
        for node_id, item in equipment.items()
    }
    attached: set[str] = set()
    for node_id, item_node in equipment_nodes.items():
        node = by_id[node_id]
        parent_id = node.parent_node_id
        ancestors: set[str] = set()
        cursor = parent_id
        cyclic = False
        while cursor in by_id and cursor not in ancestors:
            if cursor == node_id:
                cyclic = True
                break
            ancestors.add(cursor)
            cursor = by_id[cursor].parent_node_id
        if parent_id in equipment_nodes and not cyclic:
            equipment_nodes[node.parent_node_id].children.append(item_node)
            attached.add(node_id)
    for node_id, item_node in equipment_nodes.items():
        if node_id not in attached:
            line.children.append(item_node)
    if line.children:
        area.children.append(line)
        site.children.append(area)
    else:
        return StandardModel(standard_id=bundle.bundle_id, bundle_version=bundle.version, unassigned_equipment=list(equipment.values()), unassigned_variables=unassigned_variables, metadata={"source_file": canonical.model_info.source_file, "hierarchy_fallbacks": []})
    return StandardModel(standard_id=bundle.bundle_id, bundle_version=bundle.version, sites=[site], unassigned_equipment=[], unassigned_variables=unassigned_variables, metadata={"source_file": canonical.model_info.source_file, "hierarchy_fallbacks": ["Site", "Area", "Line"], "hierarchy_fallback_reason": "The current profile has no implemented source hierarchy classifier."})