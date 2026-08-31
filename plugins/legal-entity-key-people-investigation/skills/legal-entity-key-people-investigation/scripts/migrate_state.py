"""Non-destructive migration from v1.0 state records to v1.1 state records."""
import json
import sys
from copy import deepcopy
from pathlib import Path


def migrate_state(state: dict) -> dict:
    result = deepcopy(state)
    result["规范版本"] = "1.1.0"
    result["skill_version"] = "1.2.0"
    for query in result.get("查询记录", []):
        query.setdefault("数据源类型", "其他")
        query.setdefault("实际访问位置", "")
        query.setdefault("访问内容摘要", "")
        query.setdefault("未命中范围", "")
        query.setdefault("候选URL", "")
        query.setdefault("原始来源URL", "")
        if query.get("是否独立核验") and not query.get("实际访问位置"):
            query["是否独立核验"] = False
            query["后续动作"] = (query.get("后续动作", "") + "；迁移后待补充实际访问位置和访问摘要").strip("；")
    for position in result.get("人员身份", []):
        position.setdefault("关联路径引用", [])
        position.setdefault("证据直接记载主体", position.get("所属主体引用", ""))
        position.setdefault("是否直接任职证据", False)
    for evidence in result.get("证据记录", []):
        evidence.setdefault("来源类别", "其他")
        evidence.setdefault("发布主体", "")
        evidence.setdefault("来源标题", evidence.get("标题", ""))
        evidence.setdefault("原始URL", evidence.get("URL或文件路径", ""))
        if evidence.get("来源类别") == "其他":
            evidence["证据等级"] = "线索证据"
    return result


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 2:
        print("用法：python migrate_state.py INPUT OUTPUT", file=sys.stderr)
        return 2
    source, destination = map(Path, argv)
    migrated = migrate_state(json.loads(source.read_text(encoding="utf-8")))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
