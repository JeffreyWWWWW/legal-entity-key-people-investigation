# Skill Version Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从 Plugin 唯一版本源自动读取版本，并在首次响应、调查 JSON、正式 JSON 与 Excel 概览中一致显示当前 Skill 版本。

**Architecture:** 在技能脚本目录增加一个小型版本读取模块，解析仓库根目录下的 `.codex-plugin/plugin.json`，校验 `X.Y.Z` 格式并向 Python/Node 侧提供版本值。初始化脚本把版本写入状态顶层 `skill_version`；Schema 强制该字段；Excel 渲染器从状态读取并展示；Skill 文案规定首次响应播报。

**Tech Stack:** Python 3、JSON Schema Draft 2020-12、Node.js ESM、现有 `@oai/artifact-tool` 工作簿渲染链路、pytest。

## Global Constraints

- 当前 Plugin 版本基线保持 `1.0.1`，本次功能不修改 `.codex-plugin/plugin.json` 版本。
- `plugin.json` 顶层 `version` 是唯一版本事实来源；脚本不得新增独立硬编码版本常量。
- JSON 字段名固定为 `skill_version`，值必须为三段式语义化版本 `X.Y.Z`。
- Excel“01-任务概览”显示标签 `Skill 版本`；正式 JSON 直接交付同一状态字段。
- 旧状态缺少 `skill_version` 时 Schema 校验失败，渲染器不得绕过校验生成报告。
- 现有 `规范版本`、`渲染元数据.渲染器版本` 语义保持不变。

## File Map

- Create: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/version_source.py`：读取并校验 `plugin.json.version`，供 Python 脚本调用。
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/init_state.py`：写入顶层 `skill_version`。
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/render_review_workbook.mjs`：从状态读取版本并加入概览行，移除独立版本硬编码。
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/references/schemas/investigation-state.schema.json`：新增必填字段与格式约束。
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/SKILL.md`：规定首次响应顶部版本播报。
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/references/workflow.md`：记录版本字段与交付显示要求。
- Create: `tests/test_skill_version_reporting.py`：版本读取、初始化和 Schema 行为测试。
- Create: `tests/test_render_review_workbook.mjs`：概览行构建测试（若现有测试工具链支持 Node 测试，则使用 `node --test`）。

### Task 1: Add A Single Version Source

**Files:**
- Create: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/version_source.py`
- Test: `tests/test_skill_version_reporting.py`

**Interfaces:**
- Produces `get_skill_version() -> str`, which resolves `<skill root>/.codex-plugin/plugin.json`, parses JSON, requires a string matching `^[0-9]+\\.[0-9]+\\.[0-9]+$`, and raises `ValueError` with a clear message for unreadable/invalid metadata.

- [ ] **Step 1: Write failing tests**

```python
def test_get_skill_version_matches_plugin_json():
    assert get_skill_version() == "1.0.1"

def test_get_skill_version_rejects_invalid_version(tmp_path, monkeypatch):
    metadata = tmp_path / "plugin.json"
    metadata.write_text('{"version":"1"}', encoding="utf-8")
    monkeypatch.setattr(version_source, "PLUGIN_JSON", metadata)
    with pytest.raises(ValueError, match="语义化版本"):
        version_source.get_skill_version()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_skill_version_reporting.py -q`

Expected: FAIL because `version_source` and `get_skill_version` do not exist.

- [ ] **Step 3: Implement minimal reader**

Resolve `PLUGIN_JSON` from `Path(__file__).resolve().parents[3] / ".codex-plugin" / "plugin.json"`; read UTF-8 JSON; validate the `version` value against the exact three-part regex; raise `ValueError("无法读取 Plugin 版本")` or `ValueError("Plugin 版本必须是语义化版本 X.Y.Z")` with the original exception chained.

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_skill_version_reporting.py -q`

Expected: PASS for valid and invalid metadata cases.

- [ ] **Step 5: Commit**

```bash
git add plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/version_source.py tests/test_skill_version_reporting.py
git commit -m "feat: add plugin skill version source"
```

### Task 2: Persist And Validate `skill_version`

**Files:**
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/init_state.py`
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/references/schemas/investigation-state.schema.json`
- Test: `tests/test_skill_version_reporting.py`

**Interfaces:**
- `build_state(args)` returns a state whose top-level `skill_version` equals `get_skill_version()`.
- Schema top-level `required` includes `skill_version`; property type is string with `^[0-9]+\\.[0-9]+\\.[0-9]+$`.

- [ ] **Step 1: Add failing initialization and schema tests**

```python
def test_build_state_persists_skill_version(args):
    state = init_state.build_state(args)
    assert state["skill_version"] == "1.0.1"

def test_schema_rejects_missing_skill_version(valid_state):
    invalid = copy.deepcopy(valid_state)
    del invalid["skill_version"]
    errors = list(Draft202012Validator(schema).iter_errors(invalid))
    assert any("skill_version" in error.message for error in errors)
```

- [ ] **Step 2: Run targeted tests and observe failure**

Run: `pytest tests/test_skill_version_reporting.py -q`

Expected: FAIL because initialization and Schema do not yet define the field.

- [ ] **Step 3: Implement state and Schema changes**

Import `get_skill_version` in `init_state.py` and add `"skill_version": get_skill_version(),` next to `规范版本`. Update Schema `required` and `properties` with the exact pattern above. Keep `state_hash` behavior unchanged so the new field participates in the fact hash.

- [ ] **Step 4: Run targeted and existing validation tests**

Run: `pytest tests/test_skill_version_reporting.py -q` and `pytest -q`

Expected: all tests PASS; a state without `skill_version` fails validation.

- [ ] **Step 5: Commit**

```bash
git add plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/init_state.py plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/references/schemas/investigation-state.schema.json tests/test_skill_version_reporting.py
git commit -m "feat: persist and validate skill version"
```

### Task 3: Show Version In Excel And Remove Renderer Hardcoding

**Files:**
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/render_review_workbook.mjs`
- Create/Modify: `tests/test_render_review_workbook.mjs`

**Interfaces:**
- `buildOverviewRows(state, hash)` returns a row `['Skill 版本', state.skill_version]`.
- Renderer keeps the existing `RENDERER_VERSION` constant only for `渲染元数据` bookkeeping; it must not use that constant as the Skill version or overwrite `state.skill_version`.

- [ ] **Step 1: Write failing Node test**

Import `buildOverviewRows`, construct a minimal state with `skill_version: "1.0.1"`, and assert the returned rows contain `['Skill 版本', '1.0.1']`.

- [ ] **Step 2: Run test to verify failure**

Run: `node --test tests/test_render_review_workbook.mjs`

Expected: FAIL because the overview has no `Skill 版本` row.

- [ ] **Step 3: Implement overview change**

Add `['Skill 版本', state['skill_version']]` beside the existing `规范版本` row. Ensure no new hardcoded `1.0.1` appears in the renderer. Keep existing validation invocation and workbook structure intact.

- [ ] **Step 4: Run Node test and renderer regression checks**

Run: `node --test tests/test_render_review_workbook.mjs`; then render a validated fixture with the existing command and inspect the first sheet for `Skill 版本`.

Expected: PASS and the first sheet contains the label and state value.

- [ ] **Step 5: Commit**

```bash
git add plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/render_review_workbook.mjs tests/test_render_review_workbook.mjs
git commit -m "feat: show skill version in workbook overview"
```

### Task 4: Document First-Response And Delivery Contract

**Files:**
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/SKILL.md`
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/references/workflow.md`
- Test: `tests/test_skill_version_reporting.py`

**Interfaces:**
- Skill instructions explicitly require the first response after takeover to begin with `Skill 版本：<current plugin.json version>` and prohibit repeating it for every later message in the same task.
- Workflow instructions state that formal JSON carries `skill_version` and Excel overview carries `Skill 版本`.

- [ ] **Step 1: Add documentation assertions**

```python
def test_skill_docs_require_first_response_version_notice():
    skill = SKILL_PATH.read_text(encoding="utf-8")
    assert "Skill 版本" in skill
    assert "首次响应" in skill
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_skill_version_reporting.py::test_skill_docs_require_first_response_version_notice -q`

Expected: FAIL because the Skill documentation has no first-response version contract.

- [ ] **Step 3: Update documentation**

Add a concise “版本播报” rule to `SKILL.md`; add `skill_version` and Excel overview display to `workflow.md`. Use `<version>` placeholders in instructions so future releases follow `plugin.json` automatically; do not hardcode `1.0.1` in the behavioral rule.

- [ ] **Step 4: Run documentation and full tests**

Run: `pytest -q` and `git diff --check`

Expected: all tests PASS and no whitespace errors.

- [ ] **Step 5: Commit**

```bash
git add plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/SKILL.md plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/references/workflow.md tests/test_skill_version_reporting.py
git commit -m "docs: define skill version reporting contract"
```

### Task 5: End-to-End Verification

**Files:**
- Test/fixture: `tests/test_skill_version_reporting.py`

- [ ] **Step 1: Run the complete test suite**

Run: `pytest -q`

Expected: PASS with no failures.

- [ ] **Step 2: Initialize a real state fixture**

Run the existing `init_state.py` command with a temporary output path and valid required arguments; parse the output and assert `skill_version == "1.0.1"`.

- [ ] **Step 3: Validate the fixture**

Run the existing `validate_state.py STATE_PATH` command.

Expected: exit code 0 and the state is accepted.

- [ ] **Step 4: Render and inspect the workbook**

Run the existing `render_review_workbook.mjs STATE OUTPUT.xlsx` command with configured `CODEX_PYTHON` and `CODEX_NODE_MODULES`; inspect the overview sheet or generated preview for `Skill 版本` and `1.0.1`.

- [ ] **Step 5: Check final diff and status**

Run: `git diff --check` and `git status --short`

Expected: only intended implementation, documentation, and test changes remain.
