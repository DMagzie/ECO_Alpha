from em_model import EMModel
def test_validate_flags_missing():
    w = EMModel({}).validate()
    assert any("Missing required key" in m for m in w)
