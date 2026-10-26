from pathlib import Path

from layer1.parser import parse_nodeset
from layer2.feature_builder import build_features
from layer2.unit_normalizer import normalize_unit
from layer2.variable_mapper import map_variable
from models.standard_bundle import StandardBundle


ROOT = Path(__file__).resolve().parents[1]


def test_outlet_temperature_and_unit_mapping():
    model = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    bundle = StandardBundle.load(ROOT / "config" / "default_bundle.json")
    node = next(item for item in model.nodes if item.browse_name.endswith("T_Out_102"))
    features = build_features(node, model)
    assert map_variable(features, bundle)[0]["code"] == "OutletTemperature"
    assert normalize_unit("degC", bundle.unit_dictionary) == "Cel"


def test_hard_constraints_exclude_unit_type_and_parent_conflicts():
    model = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    bundle = StandardBundle.load(ROOT / "config" / "default_bundle.json")
    node = next(item for item in model.nodes if item.browse_name.endswith("T_Out_102"))
    features = build_features(node, model)
    features.update({"data_type": "String", "engineering_unit": "rpm", "parent_entity_code": "Reactor"})
    assert map_variable(features, bundle) == []


def test_inactive_or_wrong_node_class_variables_are_not_candidates():
    model = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    bundle = StandardBundle.load(ROOT / "config" / "default_bundle.json")
    node = next(item for item in model.nodes if item.browse_name.endswith("T_Out_102"))
    outlet_temperature = next(item for item in bundle.variable_semantics if item["code"] == "OutletTemperature")
    features = build_features(node, model)

    outlet_temperature["status"] = "deprecated"
    assert all(item["code"] != "OutletTemperature" for item in map_variable(features, bundle))

    outlet_temperature["status"] = "active"
    outlet_temperature["node_classes"] = ["Object"]
    assert all(item["code"] != "OutletTemperature" for item in map_variable(features, bundle))