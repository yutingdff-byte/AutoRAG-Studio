from diff.model_normalizer import ModelRelation, model_relation, normalize_model


def test_model_alias_ignores_brand_prefix():
    assert model_relation("哈弗猛龙PLUS", "猛龙PLUS") == ModelRelation.ALIAS


def test_model_family_tracks_variants_without_exact_match():
    assert model_relation("哈弗大狗PLUS", "哈弗大狗PLUS PHEV") == ModelRelation.VARIANT
    assert model_relation("哈弗猛龙", "哈弗猛龙PLUS") == ModelRelation.FAMILY


def test_short_alias_h9_can_link_to_full_model():
    assert model_relation("H9", "二代哈弗H9") == ModelRelation.ALIAS


def test_h6_and_h6l_are_conflict_not_family():
    assert model_relation("哈弗H6", "哈弗H6L") == ModelRelation.CONFLICT


def test_normalized_model_preserves_business_suffix():
    assert normalize_model("哈弗06T").without_brand == "06T"
