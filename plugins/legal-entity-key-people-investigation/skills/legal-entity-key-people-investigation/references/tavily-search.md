# Tavily 检索说明

Tavily 是可选的线索检索后端。它用于发现候选网页，不替代企业登记、监管文件、公司官网
或官方公告等原始来源核验。

## 配置

在运行 Codex 或调用脚本的环境中设置 `TAVILY_API_KEY`。不要把密钥作为检索脚本参数，
也不要写进仓库文件、状态 JSON、查询记录、日志或交付物。

PowerShell 当前会话示例：

```powershell
$env:TAVILY_API_KEY = "<your-api-key>"
```

仓库忽略 `.env` 文件，但脚本不会自动加载 `.env`；如使用密钥管理器或启动脚本，应由其
把密钥注入环境变量。

## 调用

从 Skill 目录运行：

```powershell
python scripts/tavily_search.py "Example Corp CTO research leader"
```

可选参数：

- `--max-results 1..20`，默认 `5`；
- `--search-depth basic|advanced`，默认 `advanced`；
- `--timeout <秒>`，默认 `20`。

脚本输出标准 JSON。`status` 的处理规则：

| 状态 | 含义 | 后续处理 |
|---|---|---|
| `ok` | Tavily 请求成功 | 将结果作为候选 URL；逐一访问原始来源 |
| `unavailable` | 未配置 `TAVILY_API_KEY` | 改用可用的浏览器或人工检索方式 |
| `error` | 网络、限流、认证或响应错误 | 保存真实失败状态；不得写成“已查询但未发现” |

`status: ok` 且 `results` 为空，只能说明该次具体查询没有返回候选结果。完成“未发现”判断
仍须满足工作流中各查询维度的独立核验门槛。

## 写入调查状态

每次调用对应一个明确的查询维度，记录实际查询词和调用时间。Tavily 命中本身的
`是否独立核验`为 `false`；候选 URL 经实际访问后，另建原始来源证据及独立核验查询。
不得把 Tavily 摘要填入原始来源的`关键原文`字段。
