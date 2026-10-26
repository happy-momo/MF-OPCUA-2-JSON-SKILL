from pathlib import Path

import pytest

from layer1.parser import parse_nodeset


ROOT = Path(__file__).resolve().parents[1]


def test_nodeset_parsing_and_paths():
    model = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    assert model.model_info.namespaces == ["urn:example:plant"]
    variable = next(node for node in model.nodes if node.browse_name.endswith("T_Out_102"))
    assert variable.node_class == "Variable"
    assert variable.browse_name == "T_Out_102"
    assert variable.parent_node_id == "ns=2;s=Reactor1"
    assert variable.references[0].reference_type == "HasComponent"
    assert variable.path.endswith("/Reactor1/T_Out_102")
    assert variable.engineering_unit == "degC"
    assert variable.references[0].is_forward is False


def test_invalid_root_is_rejected(tmp_path):
    invalid = tmp_path / "not_nodeset.xml"
    invalid.write_text("<root />", encoding="utf-8")
    with pytest.raises(ValueError, match="Not a NodeSet2"):
        parse_nodeset(invalid)