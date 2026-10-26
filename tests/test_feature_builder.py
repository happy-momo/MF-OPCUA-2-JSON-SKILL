from pathlib import Path

from layer1.parser import parse_nodeset
from layer2.feature_builder import build_feature_index, build_features
from utils.token_utils import tokens


ROOT = Path(__file__).resolve().parents[1]


def test_feature_tokens_and_siblings():
    model = parse_nodeset(ROOT / "examples" / "sample_nodeset.xml")
    node = next(item for item in model.nodes if item.browse_name.endswith("T_Out_102"))
    features = build_features(node, model)
    assert features == build_features(node, model, build_feature_index(model))
    assert "outlet" in features["tokens"]
    assert any("Pressure" in sibling for sibling in features["sibling_names"])
    assert tokens("T_Out_102") == {"out", "102"}