"""Tests for holons.identity — holon.yaml parser."""

from holons.identity import parse_holon


def test_parse_holon(tmp_path):
    holon_yaml = tmp_path / "holon.yaml"
    holon_yaml.write_text(
        'uuid: "abc-123"\n'
        'given_name: "test-holon"\n'
        'family_name: "Test"\n'
        'motto: "A test holon."\n'
        'composer: "Tester"\n'
        'clade: "deterministic/pure"\n'
        'status: draft\n'
        'born: "2026-01-01"\n'
        'lang: "python"\n'
        'parents: []\n'
        'reproduction: "manual"\n'
        'generated_by: "dummy-test"\n'
        'proto_status: draft\n'
    )

    identity = parse_holon(holon_yaml)
    assert identity.uuid == "abc-123"
    assert identity.given_name == "test-holon"
    assert identity.family_name == "Test"
    assert identity.motto == "A test holon."
    assert identity.clade == "deterministic/pure"
    assert identity.lang == "python"


def test_parse_holon_missing_fields(tmp_path):
    holon_yaml = tmp_path / "holon.yaml"
    holon_yaml.write_text('uuid: "minimal"\n')

    identity = parse_holon(holon_yaml)
    assert identity.uuid == "minimal"
    assert identity.given_name == ""


def test_parse_holon_invalid_mapping(tmp_path):
    holon_yaml = tmp_path / "holon.yaml"
    holon_yaml.write_text("- not\n- a\n- mapping\n")

    try:
        parse_holon(holon_yaml)
        assert False, "should have raised"
    except ValueError as e:
        assert "mapping" in str(e)
