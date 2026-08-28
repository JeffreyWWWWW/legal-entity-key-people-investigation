# 法律主体核心人员调查 Plugin

这是一个可版本化安装的 Codex Plugin，用于围绕指定产品或技术主题，核验目标法律主体的控制关系、管理层和技术负责人，并产出一致的 JSON 调查底稿与 Excel 审阅件。

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

安装或更新后，请新建一个 Codex 任务。

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
