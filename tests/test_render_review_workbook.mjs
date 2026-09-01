import test from "node:test";
import assert from "node:assert/strict";

import {
  buildCoverageRows,
  buildOverviewRows,
} from "../plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/render_review_workbook.mjs";

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

test("coverage distinguishes verified conclusions from leads", () => {
  const state = {
    "目标主体引用": ["ENT-001"],
    "公司主体": [{ "主体编号": "ENT-001", "规范法律名称": "Example Co" }],
    "查询记录": [
      {
        "查询编号": "QRY-001",
        "查询对象类型": "主体",
        "查询对象引用": "ENT-001",
        "查询维度": "技术与研发负责人",
        "是否独立核验": true,
        "访问结果": "成功",
        "命中情况": "已发现",
        "命中证据引用": ["EVD-001"],
      },
    ],
    "证据记录": [
      { "证据编号": "EVD-001", "证据等级": "线索证据", "核验状态": "待核验" },
    ],
  };

  const row = buildCoverageRows(state).find((item) => item[2] === "技术与研发负责人");
  assert.equal(row[3], "仅有线索");
});

test("coverage rejects verified evidence bound to another entity", () => {
  const state = {
    "目标主体引用": ["ENT-001"],
    "公司主体": [{ "主体编号": "ENT-001", "规范法律名称": "Example Co" }],
    "查询记录": [{
      "查询编号": "QRY-001",
      "查询对象类型": "主体",
      "查询对象引用": "ENT-001",
      "查询维度": "主体身份",
      "是否独立核验": true,
      "访问结果": "成功",
      "命中情况": "已发现",
      "命中证据引用": ["EVD-001"],
    }],
    "证据记录": [{
      "证据编号": "EVD-001",
      "证据等级": "强证据",
      "核验状态": "已核验",
      "主体引用": ["ENT-002"],
    }],
  };

  const row = buildCoverageRows(state).find((item) => item[2] === "主体身份");
  assert.equal(row[3], "仅有线索");
});

test("coverage attributes position queries to the position entity", () => {
  const state = {
    "目标主体引用": ["ENT-001"],
    "公司主体": [{ "主体编号": "ENT-001", "规范法律名称": "Example Co" }],
    "主体关系": [],
    "核心人员": [],
    "人员身份": [{ "身份编号": "POS-001", "所属主体引用": "ENT-001" }],
    "查询记录": [{
      "查询编号": "QRY-001",
      "查询对象类型": "人员身份",
      "查询对象引用": "POS-001",
      "查询维度": "最高管理层",
      "是否独立核验": true,
      "访问结果": "成功",
      "命中情况": "已发现",
      "命中证据引用": ["EVD-001"],
    }],
    "证据记录": [{
      "证据编号": "EVD-001",
      "证据等级": "较强证据",
      "核验状态": "已核验",
      "人员身份引用": ["POS-001"],
      "证明范围": ["CEO"],
    }],
  };

  const row = buildCoverageRows(state).find((item) => item[2] === "最高管理层");
  assert.equal(row[3], "已形成独立结论");
  assert.equal(row[4], "QRY-001");
});

test("coverage rejects evidence whose proof scope does not answer the query dimension", () => {
  const state = {
    "目标主体引用": ["ENT-001"],
    "公司主体": [{ "主体编号": "ENT-001", "规范法律名称": "Example Co" }],
    "查询记录": [{
      "查询编号": "QRY-001",
      "查询对象类型": "主体",
      "查询对象引用": "ENT-001",
      "查询维度": "技术与研发负责人",
      "是否独立核验": true,
      "访问结果": "成功",
      "命中情况": "已发现",
      "命中证据引用": ["EVD-001"],
    }],
    "证据记录": [{
      "证据编号": "EVD-001",
      "证据等级": "强证据",
      "核验状态": "已核验",
      "主体引用": ["ENT-001"],
      "证明范围": ["主体身份"],
    }],
  };

  const row = buildCoverageRows(state).find((item) => item[2] === "技术与研发负责人");
  assert.equal(row[3], "仅有线索");
});
