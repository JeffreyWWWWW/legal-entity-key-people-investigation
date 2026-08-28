# 法律主体核心人员调查 Plugin

这是一个可版本化安装的 Codex Plugin，用于围绕指定产品或技术主题，核验目标法律主体的控制关系、管理层和技术负责人，并产出一致的 JSON 调查底稿与 Excel 审阅件。

## 自动触发条件

当请求的目标是围绕指定法律主体及其产品、业务或技术主题，调查控制关系或核心人员时，
Plugin 会自动匹配。例如：

- “调查某公司在 AI 芯片业务上的实控人、管理层和技术负责人。”
- “核验某企业做储能产品的创始人、法人和研发负责人。”
- “围绕某技术方案，梳理甲公司及相关主体的核心人员和证据。”

若已明确要调查某公司的技术负责人或管理层、但尚缺产品或技术主题，Plugin 会先接管请求
并收集缺失信息，不启动外部调查。仅查工商登记信息、从品牌或 SKU 找制造商、专利检索、
发明人验证和 FTO 分析不会自动使用本 Plugin。

## 远程安装

前提：已安装支持 Plugin 的 Codex CLI，并可访问发布该 Plugin 的 Git 仓库。

GitHub 仓库：https://github.com/JeffreyWWWWW/legal-entity-key-people-investigation

执行：

```powershell
codex plugin marketplace add JeffreyWWWWW/legal-entity-key-people-investigation --ref main
codex plugin add legal-entity-key-people-investigation@jeffrey-legal-research
```

安装或更新后，请新建一个 Codex 任务，让新任务加载当前 Plugin 版本。

## 更新

先刷新 Marketplace，再重新安装 Plugin：

```powershell
codex plugin marketplace upgrade jeffrey-legal-research
codex plugin add legal-entity-key-people-investigation@jeffrey-legal-research
```

更新完成后，请新建一个 Codex 任务，让新任务加载最新的 Skill 触发规则与调查流程。

## 从本地克隆安装

需要在发布前试用，或无法直接访问远程仓库时，可先克隆仓库，再从本地路径添加 Marketplace：

```powershell
git clone https://github.com/JeffreyWWWWW/legal-entity-key-people-investigation.git
codex plugin marketplace add <local-repository-path>
codex plugin add legal-entity-key-people-investigation@jeffrey-legal-research
```

`<local-repository-path>` 是占位符，请替换为克隆后的实际目录。

## 发布新版本

Plugin 遵循语义化版本：不兼容变更升级主版本，向后兼容的新功能升级次版本，向后兼容的修复升级补丁版本。

1. 更新 `plugins/legal-entity-key-people-investigation/.codex-plugin/plugin.json` 中的 `version`。
2. 运行 Plugin、Skill、状态 Schema、Excel 渲染和全量测试。
3. 提交版本变更，并在目标 Git 仓库的默认分支上发布。
4. 使用与 Plugin 版本一致的 Git tag，例如 `v1.0.1`。
5. 通知使用者运行更新命令，并新建 Codex 任务。

仓库的 Marketplace 定义位于 `.agents/plugins/marketplace.json`，安装内容位于 `plugins/legal-entity-key-people-investigation/`。
