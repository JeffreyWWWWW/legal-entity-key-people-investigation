# Task 3 Report: Surface `skill_version` in the Workbook and Guard Main Execution

## Changes

- Updated `plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/render_review_workbook.mjs` so the overview sheet now includes a `Skill 版本` row sourced from `state["skill_version"]`.
- Wrapped the module entrypoint in a main-guard so importing the workbook helpers in tests does not auto-run the renderer.
- Added `tests/test_render_review_workbook.mjs` to verify the overview row exposes the skill version.

## Verification

- `node --test .\tests\test_render_review_workbook.mjs` passed.
- `git diff --check` passed.

## Concerns

- The repo keeps `tests/` ignored by default, so the test file must be staged with `-f`.
