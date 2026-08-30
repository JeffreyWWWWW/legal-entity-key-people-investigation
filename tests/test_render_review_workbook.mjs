import test from "node:test";
import assert from "node:assert/strict";

import { buildOverviewRows } from "../plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/render_review_workbook.mjs";

test("overview includes the skill version from state", () => {
  const state = {
    skill_version: "1.0.1",
    "规范版本": "1.0",
    "任务元数据": { "任务编号": "TASK-001", "调查基准日": "2026-08-31" },
    "输入材料": [],
    "公司主体": [{
      "主体编号": "E-001",
      "原始名称": "Example Co",
      "规范法律名称": "Example Co",
    }],
    "目标主体引用": ["E-001"],
    "技术主题": { "主题名称": "主题", "主题描述": "描述" },
    "阶段判断": {
      "整体状态": "待核验",
      "主体总数": 1,
      "已识别人员数": 0,
      "已核验身份数": 0,
      "未解决关键事项": [],
      "需要用户确认": false,
      "用户可执行动作": [],
    },
  };

  const rows = buildOverviewRows(state, "HASH");
  assert.deepEqual(rows.find(([label]) => label === "Skill 版本"), ["Skill 版本", "1.0.1"]);
});
