from __future__ import annotations

from models.canonical_model import CanonicalModel, CanonicalNode
from utils.token_utils import tokens


def build_feature_index(model: CanonicalModel) -> dict:
    by_id = {item.node_id: item for item in model.nodes}
    siblings_by_parent: dict[str | None, list[CanonicalNode]] = {}
    for item in model.nodes:
        siblings_by_parent.setdefault(item.parent_node_id, []).append(item)
    return {"by_id": by_id, "siblings_by_parent": siblings_by_parent}


def build_features(node: CanonicalNode, model: CanonicalModel, index: dict | None = None) -> dict:
    index = index or build_feature_index(model)
    by_id = index["by_id"]
    parent = by_id.get(node.parent_node_id or "")
    siblings = [item for item in index["siblings_by_parent"].get(node.parent_node_id, []) if item.node_id != node.node_id]
    text = " ".join((node.browse_name, node.display_name, node.description, node.path))
    return {
        "node_class": node.node_class,
        "browse_name": node.browse_name,
        "display_name": node.display_name,
        "description": node.description,
        "data_type": node.data_type,
        "engineering_unit": node.engineering_unit,
        "path": node.path,
        "parent_node_id": node.parent_node_id,
        "parent_name": parent.browse_name if parent else None,
        "sibling_names": [item.browse_name for item in siblings],
        "tokens": sorted(tokens(text)),
    }