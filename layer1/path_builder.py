from __future__ import annotations

from models.canonical_model import CanonicalNode


def build_paths(nodes: list[CanonicalNode]) -> None:
    by_id = {node.node_id: node for node in nodes}
    visiting: set[str] = set()

    def path_for(node: CanonicalNode) -> str:
        if node.node_id in visiting:
            return f"/{node.browse_name}"
        visiting.add(node.node_id)
        parent = by_id.get(node.parent_node_id or "")
        if parent is None:
            result = f"/{node.browse_name}"
        else:
            result = f"{path_for(parent).rstrip('/')}/{node.browse_name}"
        visiting.remove(node.node_id)
        node.path = result
        return result

    for item in nodes:
        path_for(item)