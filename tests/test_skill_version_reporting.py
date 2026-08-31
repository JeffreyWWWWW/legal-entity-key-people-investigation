import importlib.util
import argparse
import copy
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


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

INIT_STATE_PATH = SCRIPT_PATH.with_name("init_state.py")
sys.path.insert(0, str(INIT_STATE_PATH.parent))
init_spec = importlib.util.spec_from_file_location("init_state", INIT_STATE_PATH)
init_state = importlib.util.module_from_spec(init_spec)
assert init_spec.loader is not None
init_spec.loader.exec_module(init_state)

SCHEMA_PATH = INIT_STATE_PATH.parents[1] / "references" / "schemas" / "investigation-state.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
SKILL_PATH = INIT_STATE_PATH.parents[1] / "SKILL.md"
WORKFLOW_PATH = INIT_STATE_PATH.parents[1] / "references" / "workflow.md"


def _build_args():
    return argparse.Namespace(
        entity=["Example Co"], source=[], timestamp="2026-08-31T00:00:00Z",
        task_id="TASK-001", project_name="", as_of="2026-08-31", request="",
        topic="", topic_description="", keyword=[],
    )


def test_get_skill_version_matches_plugin_json():
    assert version_source.get_skill_version() == "1.1.0"


def test_get_skill_version_rejects_invalid_version(tmp_path, monkeypatch):
    metadata = tmp_path / "plugin.json"
    metadata.write_text('{"version":"1"}', encoding="utf-8")
    monkeypatch.setattr(version_source, "PLUGIN_JSON", metadata)

    with pytest.raises(ValueError, match="语义化版本"):
        version_source.get_skill_version()


def test_get_skill_version_rejects_invalid_utf8_metadata(tmp_path, monkeypatch):
    metadata = tmp_path / "plugin.json"
    metadata.write_bytes(b'{"version":"1.0.1"}\xff')
    monkeypatch.setattr(version_source, "PLUGIN_JSON", metadata)

    with pytest.raises(ValueError, match="无法读取 Plugin 版本"):
        version_source.get_skill_version()


def test_build_state_persists_skill_version():
    state = init_state.build_state(_build_args())
    assert state["skill_version"] == version_source.get_skill_version()


def test_schema_rejects_missing_skill_version():
    state = init_state.build_state(_build_args())
    invalid = copy.deepcopy(state)
    del invalid["skill_version"]
    errors = list(Draft202012Validator(SCHEMA).iter_errors(invalid))
    assert any("skill_version" in error.message for error in errors)


def test_skill_doc_requires_version_banner_and_field_mapping():
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "Skill 版本：X.Y.Z" in text
    assert "plugin.json" in text
    assert "`skill_version`" in text
    assert "state.json" in text
    assert "后续回复不重复播报版本" in text


def test_workflow_doc_describes_formal_version_field():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "skill_version" in text
    assert "正式 JSON" in text
    assert "正式 Excel" in text
    assert "Skill 版本：X.Y.Z" in text
    assert "后续回复不重复输出版本行" in text
    assert "01-任务概览" in text
    assert "Skill 版本" in text
