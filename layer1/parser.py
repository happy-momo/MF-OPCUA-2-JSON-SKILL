from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from models.canonical_model import CanonicalModel, CanonicalNode, CanonicalReference, ModelInfo
from .normalizer import local_name, normalize_name, normalize_node_id
from .path_builder import build_paths
from .reference_resolver import PARENT_REFERENCE_TYPES


SUPPORTED_NODES = {"UAObject", "UAVariable", "UAObjectType", "UAVariableType", "UADataType", "UAReferenceType"}
REFERENCE_TYPE_IDS = {"47": "HasComponent", "35": "Organizes", "46": "HasProperty", "49": "HasOrderedComponent"}


def _reference_type(value: str) -> str:
    identifier = value.rsplit("i=", 1)[-1]
    return REFERENCE_TYPE_IDS.get(identifier, identifier)


def _browse_name(value: str) -> str:
    prefix, separator, name = value.partition(":")
    return name if separator and prefix.isdigit() else value


def _child_text(element: ET.Element, name: str) -> str:
    child = next((item for item in element if local_name(item.tag) == name), None)
    if child is None:
        return ""
    return normalize_name("".join(child.itertext()))


def _data_type(element: ET.Element) -> str | None:
    attribute = element.attrib.get("DataType")
    if attribute:
        return attribute
    for child in element:
        if local_name(child.tag) == "DataType":
            return child.attrib.get("NodeId") or normalize_name("".join(child.itertext())) or None
    return None


def _engineering_unit(element: ET.Element) -> str | None:
    for child in element.iter():
        if local_name(child.tag) == "EngineeringUnit":
            return normalize_name("".join(child.itertext())) or None
        if local_name(child.tag) == "EUInformation":
            display = next((item for item in child.iter() if local_name(item.tag) == "DisplayName"), None)
            if display is not None:
                return normalize_name("".join(display.itertext())) or None
    return None


def _references(element: ET.Element) -> list[CanonicalReference]:
    result: list[CanonicalReference] = []
    for container in element:
        if local_name(container.tag) != "References":
            continue
        for ref in container:
            ref_type = _reference_type(ref.attrib.get("ReferenceType", ""))
            result.append(CanonicalReference(
                reference_type=ref_type,
                is_forward=ref.attrib.get("IsForward", "true").lower() != "false",
                target_node_id=normalize_node_id("".join(ref.itertext())),
            ))
    return result


def parse_nodeset(path: str | Path) -> CanonicalModel:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"NodeSet XML not found: {source}")
    if source.suffix.lower() != ".xml":
        raise ValueError(f"Input must be an XML file: {source}")
    try:
        tree = ET.parse(source)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML in {source}: {exc}") from exc
    root = tree.getroot()
    if local_name(root.tag) != "UANodeSet":
        raise ValueError(f"Not a NodeSet2 document: expected UANodeSet root, got {local_name(root.tag)}")

    namespace_uris: list[str] = []
    for item in root:
        if local_name(item.tag) == "NamespaceUris":
            namespace_uris = [normalize_name("".join(uri.itertext())) for uri in item if local_name(uri.tag) == "Uri"]

    raw_nodes = [item for item in root if local_name(item.tag) in SUPPORTED_NODES and item.attrib.get("NodeId")]
    ids = {normalize_node_id(item.attrib["NodeId"]) for item in raw_nodes}
    nodes: list[CanonicalNode] = []
    for element in raw_nodes:
        node_id = normalize_node_id(element.attrib["NodeId"])
        browse_name = normalize_name(_browse_name(element.attrib.get("BrowseName", "")))
        refs = _references(element)
        parent_id = next((ref.target_node_id for ref in refs if not ref.is_forward and ref.reference_type in PARENT_REFERENCE_TYPES), None)
        if parent_id not in ids:
            parent_id = None
        node_class = local_name(element.tag).removeprefix("UA")
        value_rank_text = element.attrib.get("ValueRank")
        try:
            value_rank = int(value_rank_text) if value_rank_text is not None else None
        except ValueError:
            value_rank = None
        nodes.append(CanonicalNode(
            node_id=node_id,
            node_class=node_class,
            browse_name=browse_name,
            display_name=_child_text(element, "DisplayName") or browse_name,
            description=_child_text(element, "Description"),
            parent_node_id=parent_id,
            data_type=_data_type(element),
            value_rank=value_rank,
            access_level=element.attrib.get("AccessLevel"),
            engineering_unit=_engineering_unit(element),
            references=refs,
        ))
    build_paths(nodes)
    return CanonicalModel(model_info=ModelInfo(source_file=source.name, namespaces=namespace_uris), nodes=nodes)