---
name: legal-entity-key-people-investigation
description: Use when a user asks to investigate a named company or other legal entity's controlling persons or key people in connection with a product, business, or technology topic. Covers legal representatives, shareholders or actual controllers, founders, executives, and technical or R&D leaders. Also use to collect a missing entity or topic before starting. Do not use for standalone company registry lookups, brand-to-manufacturer tracing, patent searches, inventor verification, or FTO analysis.
---

# 法律主体核心人员调查

## 用途

独立接收目标主体线索和产品或技术主题，建立可追溯的主体关系、核心人员、人员身份、
证据和查询记录。不得读取或依赖其他 Skill 的内部状态或阶段确认记录。

首次响应的顶部必须先播报 Skill 版本，格式为 `Skill 版本：X.Y.Z`，其中实际版本号取自
`plugins/legal-entity-key-people-investigation/.codex-plugin/plugin.json` 的 `version` 字段。
同一调查任务的后续回复不重复播报版本，除非用户询问版本或开启新任务。

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
- 证据中的集团名、品牌名、商业名称或交易对象名不得自动映射为目标法律主体；名称不同
  时必须分别建档，并用已核验的主体关系明确连接。
- 不重新调查品牌归属或具体 SKU 制造商。
- 不使用智慧芽或其他专利数据库。
- 不查询、筛选或分析专利，不验证人员是否为发明人或申请人，不生成专利检索式。

## 可选 Tavily 检索

环境中存在 `TAVILY_API_KEY` 时，可用
`python scripts/tavily_search.py "<具体查询词>"` 批量发现候选网页；未配置或调用失败时，
继续使用可用的浏览器或人工检索方式。Tavily 输出只用于建立线索和候选 URL，不属于独立
核验；需要采用其内容时，必须访问候选 URL 的原始来源并按证据规则另建证据。

不要把 API Key 作为检索脚本参数，也不要写入状态 JSON、查询记录、日志或交付物。完整
参数和结果处理规则见
[Tavily 检索说明](references/tavily-search.md)。

## 结果门槛

### 调查完成门槛

不得以输入结构化代替外部调查。输入材料只能建立候选主体和线索；只有按工作流完成必要
查询维度、保存原始来源证据并通过业务校验后，主体结果才能标记为调查完成。没有检出人员
不等于没有开展调查，必须保存各人员角色维度的真实查询和未命中结果。

登录墙、付费墙、访问失败、搜索摘要或页面内无法定位原文的结果都不属于独立核验。行业
媒体、新闻媒体和第三方数据库的线索证据只能显示为“仅有线索”，不能满足调查完成门槛。
多个网站或数据库必须分别建立查询和证据记录，不得合并成一条“多源一致”证据。

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
- 配置 Tavily 或使用检索脚本时见[Tavily 检索说明](references/tavily-search.md)。
- 标准状态结构见[调查状态 Schema](references/schemas/investigation-state.schema.json)。
