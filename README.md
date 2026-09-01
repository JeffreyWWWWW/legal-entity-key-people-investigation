# 法律主体核心人员调查

面向 ChatGPT 和 Codex 的法律主体核心人员调查 Plugin。围绕指定公司、机构或其他法律主体，结合具体产品、业务或技术主题，核验其控制关系、管理层以及技术与研发负责人，并生成可追溯的 JSON 调查底稿和 Excel 审阅件。

当前版本：`1.3.0`

## 核心能力

- 核验目标主体的规范法律名称及必要识别信息。
- 梳理与目标业务有关的股东、实际控制人、创始人、法定代表人和最高管理层。
- 识别技术负责人、研发负责人及有证据支持的业务负责人。
- 按主体身份、主体关系、控制与所有权、管理层、技术与研发等维度保存独立查询记录。
- 区分原始来源、第三方线索、未命中、访问失败、登录墙和付费墙等证据状态。
- 使用统一 JSON 状态作为事实底稿，通过 Schema 和业务规则校验后生成 Excel 审阅件。
- 在正式 JSON 和 Excel 中记录 `skill_version`，便于追溯调查所依据的 Plugin 版本。

## 适用范围

本 Plugin 适合以下任务：

- “调查某公司在 AI 芯片业务上的实控人、管理层和技术负责人。”
- “核验某企业做储能产品的创始人、法定代表人和研发负责人。”
- “围绕某项技术方案，梳理目标公司及相关主体的核心人员和证据。”

正式调查至少需要两项输入：

1. 一个或多个目标法律主体；
2. 产品、业务或技术主题。

缺少任一项时，Plugin 会先收集缺失信息。主体存在同名、注册地冲突或母子公司歧义时，会先请求确认调查范围。

以下任务不属于本 Plugin 的范围：

- 仅查询企业名称、统一社会信用代码、注册地址或工商变更；
- 从品牌、商标或具体 SKU 反查权利人、运营方或制造商；
- 专利检索、发明人验证、专利分析或 FTO 分析；
- 未指定目标法律主体和业务主题的纯自然人履历调查。

## 安装

### 从 GitHub 安装

前提：已安装支持 Plugin 的 Codex CLI，并可访问本仓库。

```powershell
codex plugin marketplace add JeffreyWWWWW/legal-entity-key-people-investigation --ref main
codex plugin add legal-entity-key-people-investigation@legal-entity-key-people-investigation
```

安装完成后，新建一个 ChatGPT 或 Codex 任务，使新任务加载当前 Plugin 版本。

### 从本地仓库安装

适用于本地开发、发布前验证或无法直接访问 GitHub 的环境。

```powershell
git clone https://github.com/JeffreyWWWWW/legal-entity-key-people-investigation.git
codex plugin marketplace add <local-repository-path>
codex plugin add legal-entity-key-people-investigation@legal-entity-key-people-investigation
```

将 `<local-repository-path>` 替换为克隆后的仓库绝对路径。

## 快速开始

安装后，在新任务中直接描述目标主体和调查主题。例如：

```text
调查 Example Robotics Co., Ltd. 在仓储机器人业务上的实际控制人、最高管理层和技术负责人，核验原始来源并生成 JSON 底稿与 Excel 审阅件。
```

也可以显式调用 Skill：

```text
$legal-entity-key-people-investigation
调查目标主体在储能系统业务上的创始人、控制人、管理层和研发负责人。
```

首次响应会显示当前 Skill 版本。调查过程中，用户提供的自然语言、JSON、Excel 和辅助材料都可以作为输入线索，但不会替代外部来源核验。

## 输出物

调查状态以 JSON 为唯一事实底稿，Excel 由通过校验的 JSON 确定性生成。

| 输出 | 默认位置 | 用途 |
| --- | --- | --- |
| 内部状态 | `working/legal-entity-key-people-investigation/state.json` | 调查过程中的唯一事实状态 |
| 正式 JSON | `outputs/<项目或主体范围>_法律主体核心人员调查底稿_<YYYYMMDD>.json` | 可追溯、可继续处理的正式底稿 |
| 正式 Excel | `outputs/<项目或主体范围>_法律主体核心人员调查审阅件_<YYYYMMDD>.xlsx` | 供人工审阅和确认的交付件 |

同一调查范围和基准日重新生成时会覆盖同名交付物，不追加随机编号。用户更正内容时，先更新 JSON 并重新校验，再生成新的 Excel；Excel 不作为机器事实来源。

## 可选 Tavily 配置

Tavily 用于发现候选网页，不是必需依赖，也不能代替企业登记、监管文件、公司官网或官方公告等原始来源核验。

在启动 Codex 的环境中设置 `TAVILY_API_KEY`：

```powershell
$env:TAVILY_API_KEY = "<your-api-key>"
```

也可以从 Skill 目录单独调用检索脚本：

```powershell
python scripts/tavily_search.py "Example Corp CTO research leader"
```

脚本不会自动加载 `.env`。不要把 API Key 写入仓库、调查状态、查询记录、日志或交付物。未配置 Tavily 或调用失败时，调查可继续使用其他可用检索方式。

## 更新

刷新 Marketplace 后重新安装 Plugin：

```powershell
codex plugin marketplace upgrade legal-entity-key-people-investigation
codex plugin add legal-entity-key-people-investigation@legal-entity-key-people-investigation
```

更新完成后新建任务，以加载最新的 Skill 触发规则、调查流程和版本信息。

## 仓库结构

```text
.
|-- .agents/plugins/marketplace.json
|-- plugins/legal-entity-key-people-investigation/
|   |-- .codex-plugin/plugin.json
|   `-- skills/legal-entity-key-people-investigation/
|       |-- SKILL.md
|       |-- agents/openai.yaml
|       |-- references/
|       `-- scripts/
|-- tests/
`-- README.md
```

- `.agents/plugins/marketplace.json`：仓库 Marketplace 定义。
- `.codex-plugin/plugin.json`：Plugin 名称、版本、能力和界面元数据。
- `SKILL.md`：触发条件、调查边界、启动门槛和交付要求。
- `references/`：调查工作流、证据规则、状态 Schema 和 Tavily 使用说明。
- `scripts/`：状态初始化、迁移、校验、交付路径生成和 Excel 渲染脚本。
- `tests/`：工作流契约、质量门槛、版本、迁移、Tavily 和 Excel 渲染测试。

## 开发与验证

本仓库当前使用 Python 3.11、Node.js 24 和支持 Plugin 的 Codex CLI 进行本地验证。

运行 Python 测试：

```powershell
pytest -q
```

运行 Excel 渲染相关 Node.js 测试：

```powershell
node --test tests/test_render_review_workbook.mjs
```

校验调查状态：

```powershell
python plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts/validate_state.py <state-path>
```

Excel 渲染依赖 Codex 工作区提供的 Node.js 模块，并通过 `CODEX_NODE_MODULES` 定位。一般使用者无需手动调用渲染脚本，Plugin 会按调查工作流完成校验和交付。

## 发布版本

本项目遵循语义化版本。发布新版本时：

1. 更新 `plugins/legal-entity-key-people-investigation/.codex-plugin/plugin.json` 中的 `version`；
2. 运行 Plugin、Skill、状态 Schema、Excel 渲染和全量测试；
3. 提交版本变更并发布到默认分支；
4. 创建与 Plugin 版本一致的 Git tag，例如 `v1.3.1`；
5. 通知使用者刷新 Marketplace、重新安装 Plugin，并新建任务。

## 许可证

仓库当前未包含许可证文件。在明确许可证之前，请勿假定代码或调查流程可被自由复制、修改或再分发。
