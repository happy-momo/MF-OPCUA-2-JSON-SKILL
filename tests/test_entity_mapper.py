from pathlib import Path

from layer1.parser import parse_nodeset
from layer2.entity_mapper import map_entity
from layer2.feature_builder import build_features
from models.standard_bundle import StandardBundle


ROOT = Path(__file__).resolve().parents[1]


def test_reactor_entity_mapping():
    model = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    bundle = StandardBundle.load(ROOT / "config" / "default_bundle.json")
    node = next(item for item in model.nodes if item.browse_name.endswith("Reactor1"))
    assert map_entity(build_features(node, model), bundle)[0]["code"] == "Reactor"


def test_inactive_or_wrong_node_class_entities_are_not_candidates():
    model = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    bundle = StandardBundle.load(ROOT / "config" / "default_bundle.json")
    node = next(item for item in model.nodes if item.browse_name.endswith("Reactor1"))
    reactor = next(item for item in bundle.entity_types if item["code"] == "Reactor")
    features = build_features(node, model)

    reactor["status"] = "inactive"
    assert all(item["code"] != "Reactor" for item in map_entity(features, bundle))

    reactor["status"] = "active"
    reactor["node_classes"] = ["Variable"]
    assert all(item["code"] != "Reactor" for item in map_entity(features, bundle))