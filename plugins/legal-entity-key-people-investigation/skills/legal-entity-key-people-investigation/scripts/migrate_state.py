"""Non-destructive migration to the current investigation state schema."""
import json
import sys
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

if __package__:
    from .state_model import derive_overall_status
    from .version_source import get_skill_version
else:
    from state_model import derive_overall_status
    from version_source import get_skill_version


def migrate_state(state: dict) -> dict:
    result = deepcopy(state)
    result["规范版本"] = "1.2.0"
    result["skill_version"] = get_skill_version()
    downgraded_query_ids = set()
    for query in result.get("查询记录", []):
        was_independent = bool(query.get("是否独立核验"))
        query.setdefault("数据源类型", "其他")
        query.setdefault("实际访问位置", "")
        query.setdefault("访问内容摘要", "")
        query.setdefault("未命中范围", "")
        query.setdefault("候选URL", "")
        query.setdefault("原始来源URL", "")
        query.setdefault("原文定位状态", "不适用")
        if was_independent and not query.get("实际访问位置"):
            query["是否独立核验"] = False
            query["后续动作"] = (query.get("后续动作", "") + "；迁移后待补充实际访问位置和访问摘要").strip("；")
        if was_independent and query.get("命中情况") == "已发现":
            query["是否独立核验"] = False
            query["原文定位状态"] = "无法定位"
            query["后续动作"] = (
                query.get("后续动作", "") + "；迁移记录不能自动证明已定位原文，需重新访问核对"
            ).strip("；")
        if was_independent and not query.get("是否独立核验"):
            downgraded_query_ids.add(query.get("查询编号"))
    for position in result.get("人员身份", []):
        position.setdefault("关联路径引用", [])
        position.setdefault("证据直接记载主体", position.get("所属主体引用", ""))
        position.setdefault("是否直接任职证据", False)
    downgraded_evidence_ids = set()
    for evidence in result.get("证据记录", []):
        evidence.setdefault("来源类别", "其他")
        evidence.setdefault("发布主体", "")
        evidence.setdefault("来源标题", evidence.get("标题", ""))
        evidence.setdefault("原始URL", evidence.get("URL或文件路径", ""))
        evidence.setdefault("原文主体名称", [])
        evidence.setdefault("主体映射关系引用", [])
        publisher = str(evidence.get("发布主体", ""))
        if evidence.get("来源类别") in {"行业媒体", "新闻媒体", "第三方数据库", "搜索服务"} and any(
            separator in publisher for separator in (" / ", "、", "；", ";")
        ):
            source_url = evidence.get("原始URL") or evidence.get("URL或文件路径", "")
            hostname = urlparse(source_url).hostname or "迁移后待确认的单一来源"
            evidence["发布主体"] = hostname
            evidence["关键原文"] = "迁移记录仅保留现有原始URL；原多源摘要不可作为原文。"
            evidence["核验状态"] = "待核验"
            evidence["证据等级"] = "线索证据"
            evidence["持续有效说明"] = (
                evidence.get("持续有效说明", "") + f"；原多源发布主体：{publisher}；需逐源重建证据"
            ).strip("；")
        if evidence.get("来源类别") == "其他":
            evidence["证据等级"] = "线索证据"
        if evidence.get("核验状态") == "已核验" and evidence.get("主体引用") and not evidence["原文主体名称"]:
            evidence["核验状态"] = "待核验"
            evidence["证据等级"] = "线索证据"
            downgraded_evidence_ids.add(evidence.get("证据编号"))
            evidence["持续有效说明"] = (
                evidence.get("持续有效说明", "") + "；迁移后待补充原文主体名称和主体映射证据"
            ).strip("；")

    for relationship in result.get("主体关系", []):
        if set(relationship.get("证据引用", [])) & downgraded_evidence_ids:
            relationship["核验状态"] = "待核验"

    for entity in result.get("公司主体", []):
        if set(entity.get("证据引用", [])) & downgraded_evidence_ids:
            entity["主体身份状态"] = "待核验"

    for position in result.get("人员身份", []):
        if set(position.get("证据引用", [])) & downgraded_evidence_ids:
            position["核验状态"] = "待核验"
            position["可靠性"] = "待判断"

    has_downgrade = bool(downgraded_query_ids or downgraded_evidence_ids)
    if has_downgrade:
        for investigation_result in result.get("主体调查结果", []):
            if investigation_result.get("调查进度") == "调查完成":
                investigation_result["调查进度"] = "调查中"
                investigation_result["事实核验状态"] = "待核验"
        judgment = result.get("阶段判断", {})
        if "已核验身份数" in judgment:
            judgment["已核验身份数"] = sum(
                position.get("核验状态") == "已核验"
                for position in result.get("人员身份", [])
            )
        if "整体状态" in judgment:
            judgment["整体状态"] = derive_overall_status(result)
        if "需要用户确认" in judgment:
            judgment["需要用户确认"] = judgment.get("整体状态") in {
                "待补充输入",
                "待确认范围",
                "待审阅",
                "部分完成",
            }
        metadata = result.get("渲染元数据", {})
        if "状态内容哈希" in metadata:
            metadata["状态内容哈希"] = ""
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
