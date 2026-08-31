# v1.2.0 Quality Gates Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with test-first development and verification checkpoints.

**Goal:** Upgrade the legal-entity investigation plugin so query provenance, role coverage, entity boundaries, evidence grades, migration, and workbook review output are enforced automatically.

**Architecture:** Extend the JSON Schema with explicit provenance and relationship fields. Keep business rules in `validate_state.py`, add a standalone non-destructive migration script, and derive workbook sheets deterministically from validated state. Preserve old inputs and outputs; migration writes a new state copy.

**Tech Stack:** Python 3, jsonschema, pytest, Node.js workbook renderer.

## Global Constraints

- Plugin version becomes `1.2.0`; state schema version becomes `1.1.0`; renderer version becomes `1.1.0`.
- Existing state files remain readable only through migration; migration never fabricates facts.
- Search-service output, user material, and search snippets cannot be independent verification or original evidence.
- Completion requires every required role dimension to have an independent conclusion per target entity.
- Query timestamps rendered to Excel are ISO text.

### Task 1: Add failing quality-gate tests

**Files:**
- Create: `tests/test_quality_gates.py`

Write fixtures that mutate a minimal valid state and assert validation rejects generic data sources, Tavily evidence, media evidence graded above lead evidence, missing query details, parent-company misattachment, institution-as-person, and CEO-only completion. Add migration and renderer contract tests as fixtures become available.

### Task 2: Extend schema and state model

**Files:**
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/references/schemas/investigation-state.schema.json`
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/state_model.py`

Add query provenance fields, evidence source decomposition, position relationship fields, coverage matrix definitions, and schema version compatibility constants. Ensure derived status requires coverage-aware results.

### Task 3: Enforce business rules

**Files:**
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/validate_state.py`

Implement deterministic checks for provenance, source/evidence grade ceilings, query no-hit scope, direct-employment/entity alignment, institution names, relationship paths, and all required role dimensions. Preserve existing reference and summary checks.

### Task 4: Add non-destructive migration

**Files:**
- Create: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/migrate_state.py`
- Create: `tests/test_migrate_state.py`

Provide `migrate_state(input, output)` and CLI behavior. Copy legacy fields into new fields only when unambiguous; otherwise use empty values plus explicit review issues. Never overwrite the input.

### Task 5: Upgrade workbook renderer

**Files:**
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/render_review_workbook.mjs`
- Create: `tests/test_renderer_contract.py`

Render ISO query times as text, expose provenance and entity-path columns, add overview coverage statistics, and add `06-覆盖矩阵` sheet. Bump renderer version and retain deterministic sheet order.

### Task 6: Update documentation and versions

**Files:**
- Modify: `plugins/legal-entity-key-people-investigation/.codex-plugin/plugin.json`
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/SKILL.md`
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/references/workflow.md`
- Modify: `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/references/evidence-rules.md`

Document the new required fields, completion matrix, migration command, and evidence ceilings.

### Verification

Run `pytest -q`, validate representative migrated state with `python scripts/validate_state.py`, and run renderer contract tests. Inspect `git diff` and confirm no generated source inputs changed.
