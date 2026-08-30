---
name: legal-entity-key-people-investigation
description: Use when a user asks to investigate a named company or other legal entity's controlling persons or key people in connection with a product, business, or technology topic. Covers legal representatives, shareholders or actual controllers, founders, executives, and technical or R&D leaders. Also use to collect a missing entity or topic before starting. Do not use for standalone company registry lookups, brand-to-manufacturer tracing, patent searches, inventor verification, or FTO analysis.
---

# 法律主体核心人员调查

## 用途

独立接收目标主体线索和产品或技术主题，建立可追溯的主体关系、核心人员、人员身份、
证据和查询记录。不得读取或依赖其他 Skill 的内部状态或阶段确认记录。

首次响应的顶部必须先播报 Skill 版本，格式为 `Skill version: X.Y.Z`，其中版本号取自
`plugins/legal-entity-key-people-investigation/.codex-plugin/plugin.json` 的 `version` 字段。

## 何时触发

当用户的目标是围绕**指定法律主体**及其**产品、业务或技术主题**，识别或核验与该业务
有关的控制关系或核心人员时触发。目标主体可为公司、企业、机构、集团或其明确的子公司；
人员目标可为法人代表、股东或实际控制人、创始人、高管、技术负责人、研发负责人或业务
负责人。

下列请求应触发：

- “调查某公司在 AI 芯片业务上的实控人、管理层和技术负责人。”
- “帮我核验某企业做储能产品的创始人、法人和研发负责人。”
- “围绕某技术方案，梳理甲公司及其相关主体的核心人员和证据。”
- “我想查某公司的技术负责人。”即使尚未给出具体产品或技术，也先接管材料收集并请求补充主题。

下列请求不应触发，应交由更匹配的能力处理：

- 仅查询企业名称、统一社会信用代码、注册地址、成立时间或工商变更，且不涉及核心人员
  与业务主题的调查。
- 从品牌、商标或 SKU 反查权利人、运营方或制造商。
- 检索、筛选、分析专利，制作专利检索式，验证发明人，或进行 FTO 分析。
- 只查询自然人的履历、联系方式或任职信息，且未指定需要调查的法律主体与业务主题。

当请求同时可能属于本 Skill 和相邻任务时，以用户的主要交付目标判断：需要“主体 - 业务
主题 - 核心人员 - 证据”的可追溯调查底稿时触发本 Skill；主要目标是品牌制造关系或专利
结论时不触发本 Skill。

## 启动门槛

Skill 被触发后，正式调查前必须同时取得：

1. 一个或多个目标主体线索；
2. 产品或技术主题。

缺少任一项时，接收已提供的材料，明确指出缺少的主体或主题并请求补充，不开始外部调查。
主体存在关键同名、注册地冲突或母子公司歧义时，先展示《调查任务确认单》，等待用户明确
范围。

## 调查边界

- 只调查与目标主体和目标业务相关的法人代表、自然人股东或实际控制人、创始人、最高
  管理人员、技术或研发负责人及有证据支持的业务负责人。
- 关联主体采用相关性驱动的一跳扩展；更深一层只在可靠证据表明目标业务位于该主体时纳入。
- 不重新调查品牌归属或具体 SKU 制造商。
- 不使用智慧芽或其他专利数据库。
- 不查询、筛选或分析专利，不验证人员是否为发明人或申请人，不生成专利检索式。

## 结果门槛

将自然语言、JSON、Excel 和辅助材料规范化为
`working/legal-entity-key-people-investigation/state.json`。JSON 是唯一事实底稿；Excel 只从
通过 Schema 和业务规则校验的 JSON 确定性渲染，不保存 Excel 专属事实。

在对话中说明调查结论、证据边界和待确认项，并提供 Excel 审阅件。用户更正时先更新
JSON，再重新校验和渲染。正式交付时按工作流规定的范围和调查日期生成同名范围的 JSON
底稿与 Excel 审阅件；同一范围、同一调查日期重新生成时覆盖同名文件，不追加随机编号。
不得把沉默视为确认，也不得自动执行后续工作。

正式 JSON 与正式 Excel 都必须携带同一 `skill_version` 值；它是当前 Skill 版本的语义化
版本号，也是 `state.json` 中可追溯的版本字段。

## 支持资源

- 接收、调查、保存和交付流程见[工作流](references/workflow.md)。
- 人员范围、主体扩展和证据证明边界见[证据规则](references/evidence-rules.md)。
- 标准状态结构见[调查状态 Schema](references/schemas/investigation-state.schema.json)。
