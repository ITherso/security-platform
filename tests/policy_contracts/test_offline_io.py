import json

import pytest

from security_platform.policy_contracts import offline_io


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}',
                                b'{"a":1e999}', b'[]', b'"secret-policy"', b'\xff'])
def test_invalid_input_is_fixed_error_without_content(tmp_path, raw):
    source = tmp_path / "input.json"
    source.write_bytes(raw)
    with pytest.raises(offline_io.OfflineInputError) as caught:
        offline_io.read_input(source)
    assert str(caught.value) == "offline_input_invalid"


def test_input_bytes_and_depth_are_bounded(tmp_path, monkeypatch):
    source = tmp_path / "input.json"
    source.write_text('{"value":"' + 'a' * 100 + '"}', encoding="utf-8")
    monkeypatch.setattr(offline_io, "MAX_INPUT_BYTES", 30)
    with pytest.raises(offline_io.OfflineInputError, match="offline_input_too_large"):
        offline_io.read_input(source)
    monkeypatch.setattr(offline_io, "MAX_INPUT_BYTES", 10000)
    source.write_text('{"value":' + '[' * 30 + '0' + ']' * 30 + '}', encoding="utf-8")
    with pytest.raises(offline_io.OfflineInputError, match="offline_input_too_complex"):
        offline_io.read_input(source)


def test_output_is_complete_deterministic_and_input_is_preserved(tmp_path):
    source, target = tmp_path / "input.json", tmp_path / "output.json"
    source.write_text('{"original":true}', encoding="utf-8")
    target.write_text("old", encoding="utf-8")
    offline_io.write_output(target, {"b": 2, "a": 1}, input_path=source)
    assert json.loads(target.read_bytes()) == {"a": 1, "b": 2}
    assert source.read_bytes() == b'{"original":true}'
    assert list(tmp_path.glob(".security-policy-*.tmp")) == []


def test_invalid_output_does_not_replace_existing_file(tmp_path):
    source, target = tmp_path / "input.json", tmp_path / "output.json"
    source.write_text("{}", encoding="utf-8")
    target.write_text("existing-policy", encoding="utf-8")
    with pytest.raises(offline_io.OfflineInputError, match="offline_output_unavailable"):
        offline_io.write_output(target, {"value": float("nan")}, input_path=source)
    assert target.read_text() == "existing-policy"
    assert list(tmp_path.glob(".security-policy-*.tmp")) == []


def test_input_output_alias_is_rejected(tmp_path):
    source = tmp_path / "input.json"
    source.write_text("{}", encoding="utf-8")
    with pytest.raises(offline_io.OfflineInputError, match="offline_output_is_input"):
        offline_io.write_output(source, {"would_overwrite": True}, input_path=source)
    assert source.read_bytes() == b"{}"


def test_failed_replace_preserves_previous_output_and_cleans_temporary(tmp_path, monkeypatch):
    source, target = tmp_path / "input.json", tmp_path / "output.json"
    source.write_text("{}", encoding="utf-8")
    target.write_text("previous-output", encoding="utf-8")
    def unavailable(*args):
        raise OSError("private-policy-must-not-escape")
    monkeypatch.setattr(offline_io.os, "replace", unavailable)
    with pytest.raises(offline_io.OfflineInputError) as caught:
        offline_io.write_output(target, {"candidate": "new"}, input_path=source)
    assert str(caught.value) == "offline_output_unavailable"
    assert target.read_text() == "previous-output"
    assert list(tmp_path.glob(".security-policy-*.tmp")) == []
