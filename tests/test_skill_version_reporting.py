import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "legal-entity-key-people-investigation"
    / "skills"
    / "legal-entity-key-people-investigation"
    / "scripts"
    / "version_source.py"
)
spec = importlib.util.spec_from_file_location("version_source", SCRIPT_PATH)
version_source = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(version_source)


def test_get_skill_version_matches_plugin_json():
    assert version_source.get_skill_version() == "1.0.1"


def test_get_skill_version_rejects_invalid_version(tmp_path, monkeypatch):
    metadata = tmp_path / "plugin.json"
    metadata.write_text('{"version":"1"}', encoding="utf-8")
    monkeypatch.setattr(version_source, "PLUGIN_JSON", metadata)

    with pytest.raises(ValueError, match="语义化版本"):
        version_source.get_skill_version()
