import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

if __package__:
    from .state_model import derive_overall_status, state_hash
else:
    from state_model import derive_overall_status, state_hash


ROOT = Path(__file__).resolve().parents[1]


def _windows_long_path(path: Path) -> Path:
    resolved = path.resolve()
    if os.name == "nt" and not str(resolved).startswith("\\\\?\\"):
        return Path(f"\\\\?\\{resolved}")
    return resolved


SCHEMA_PATH = _windows_long_path(
    ROOT / "references/schemas/investigation-state.schema.json"
)
ID_FIELDS = {
    "输入材料": "材料编号",
    "公司主体": "主体编号",
    "主体关系": "关系编号",
    "核心人员": "人员编号",
    "人员身份": "身份编号",
    "证据记录": "证据编号",
    "查询记录": "查询编号",
    "冲突与待确认项": "事项编号",
    "主体调查结果": "结果编号",
    "用户确认记录": "确认编号",
}
HIGH_RISK_IDENTITIES = {"法人代表", "登记负责人", "自然人股东", "最终受益人", "实际控制人"}
REQUIRED_COMPLETION_QUERY_DIMENSIONS = {
    "主体身份",
    "主体关系",
    "控制与所有权",
    "创始人",
    "最高管理层",
    "技术与研发负责人",
}
GENERIC_SOURCES = {"原始官网、监管文件或公开登记入口", "原始官网、监管文件或公开登记入口等"}
INSTITUTION_NAMES = {"Vanguard", "BlackRock", "Morgan Stanley", "贝莱德", "先锋集团", "摩根士丹利"}
EVIDENCE_LEVELS = {"线索证据": 0, "较强证据": 1, "强证据": 2}
SOURCE_LIST_SEPARATORS = (" / ", "、", "；", ";")
LEAD_SOURCE_CATEGORIES = {"行业媒体", "新闻媒体", "第三方数据库", "搜索服务"}
QUERY_DIMENSION_PROOF_SCOPES = {
    "主体身份": {"主体身份"},
    "控制与所有权": {"控制与所有权", "自然人股东", "最终受益人", "实际控制人", "母公司", "子公司"},
    "创始人": {"创始人", "联合创始人"},
    "最高管理层": {"最高管理层", "董事长", "CEO", "总裁", "其他核心管理人员"},
    "技术与研发负责人": {"技术与研发负责人", "技术负责人", "研发负责人", "工程负责人"},
    "目标业务负责人": {"目标业务负责人"},
}


class ValidationError(ValueError):
    pass


def validate_query_quality(query: dict) -> None:
    """Validate provenance fields when present; legacy records remain migratable."""
    if not query.get("是否独立核验"):
        return
    source = str(query.get("数据源", "")).strip()
    if source in GENERIC_SOURCES:
        raise ValidationError("独立核验不得使用泛化占位数据源")
    if query.get("数据源类型") in {"搜索服务", "用户材料", "搜索摘要"}:
        raise ValidationError("搜索服务、用户材料和搜索摘要不得标为独立核验")
    if query.get("访问结果") != "成功":
        raise ValidationError("独立核验必须成功访问原始来源")
    if not str(query.get("实际访问位置", "")).strip() or not str(query.get("访问内容摘要", "")).strip():
        raise ValidationError("独立核验必须填写实际访问位置和访问内容摘要")
    if query.get("命中情况") == "已发现" and query.get("原文定位状态") != "已定位":
        raise ValidationError("独立核验发现事实时必须定位原文")
    if query.get("命中情况") == "已查询但未发现" and not str(query.get("未命中范围", "")).strip():
        raise ValidationError("已查询但未发现必须填写未命中范围")


def validate_evidence_quality(evidence: dict) -> None:
    category = evidence.get("来源类别")
    level = evidence.get("证据等级")
    if category in LEAD_SOURCE_CATEGORIES and level in {"较强证据", "强证据"}:
        raise ValidationError(f"{category}最高只能标为线索证据")
    publisher = str(evidence.get("发布主体", ""))
    if category in LEAD_SOURCE_CATEGORIES and any(
        separator in publisher for separator in SOURCE_LIST_SEPARATORS
    ):
        raise ValidationError("每条证据记录只能对应单一来源和单一原始URL")


def _normalized_legal_name(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value).casefold())


def _entity_legal_names(entity: dict) -> set[str]:
    name = _normalized_legal_name(entity.get("规范法律名称", ""))
    return {name} if name else set()


def validate_evidence_source_scope(
    evidence: dict,
    entities: dict[str, dict],
    relationships: dict[str, dict],
) -> None:
    cited_entity_ids = set(evidence.get("主体引用", []))
    source_names = {
        _normalized_legal_name(name)
        for name in evidence.get("原文主体名称", [])
        if str(name).strip()
    }
    if evidence.get("核验状态") == "已核验" and cited_entity_ids and not source_names:
        raise ValidationError(f"{evidence.get('证据编号', '证据')}缺少原文主体名称")
    if evidence.get("核验状态") != "已核验":
        return

    mapping_ids = evidence.get("主体映射关系引用", [])
    for cited_entity_id in cited_entity_ids:
        entity = entities.get(cited_entity_id)
        if not entity:
            continue
        if source_names & _entity_legal_names(entity):
            continue
        mapped = False
        for relationship_id in mapping_ids:
            if relationship_id in evidence.get("主体关系引用", []):
                continue
            relationship = relationships.get(relationship_id)
            if not relationship or relationship.get("核验状态") != "已核验":
                continue
            endpoints = {
                relationship.get("起点主体引用"),
                relationship.get("终点主体引用"),
            }
            if cited_entity_id not in endpoints:
                continue
            other_ids = endpoints - {cited_entity_id}
            if any(
                source_names & _entity_legal_names(entities[entity_id])
                for entity_id in other_ids
                if entity_id in entities
            ):
                mapped = True
                break
        if not mapped:
            raise ValidationError(
                f"{evidence.get('证据编号', '证据')}原文主体未直接记载{cited_entity_id}且缺少已核验映射关系"
            )


def validate_entity_evidence(entity: dict, evidence_index: dict[str, dict]) -> None:
    if entity.get("主体身份状态") != "已核验":
        return
    entity_id = entity.get("主体编号")
    matching = [
        evidence_index[evidence_id]
        for evidence_id in entity.get("证据引用", [])
        if evidence_id in evidence_index
    ]
    if not any(
        item.get("核验状态") == "已核验"
        and item.get("证据等级") in {"较强证据", "强证据"}
        and entity_id in item.get("主体引用", [])
        and "主体身份" in item.get("证明范围", [])
        for item in matching
    ):
        raise ValidationError(f"{entity_id}缺少已核验的主体身份较强或强证据")


def query_supports_independent_conclusion(query: dict, evidence_index: dict[str, dict]) -> bool:
    if not query.get("是否独立核验") or query.get("访问结果") != "成功":
        return False
    if query.get("命中情况") == "已查询但未发现":
        return bool(str(query.get("未命中范围", "")).strip())
    if query.get("命中情况") != "已发现":
        return False
    reference_fields = {
        "主体": "主体引用",
        "主体关系": "主体关系引用",
        "人员身份": "人员身份引用",
    }
    reference_field = reference_fields.get(query.get("查询对象类型"))
    if query.get("查询对象类型") == "人员":
        return False
    query_target = query.get("查询对象引用")
    allowed_scopes = QUERY_DIMENSION_PROOF_SCOPES.get(query.get("查询维度"))
    return any(
        evidence_index[evidence_id].get("核验状态") == "已核验"
        and evidence_index[evidence_id].get("证据等级") in {"较强证据", "强证据"}
        and (
            allowed_scopes is None
            or bool(allowed_scopes & set(evidence_index[evidence_id].get("证明范围", [])))
        )
        and (
            reference_field is None
            or query_target in evidence_index[evidence_id].get(reference_field, [])
        )
        for evidence_id in query.get("命中证据引用", [])
        if evidence_id in evidence_index
    )


def validate_position_quality(position: dict, target_ids: set[str], relationship_ids: set[str]) -> None:
    name = str(position.get("规范姓名", "")).strip()
    if name in INSTITUTION_NAMES:
        raise ValidationError("机构名称不得写入自然人集合")
    if "所属主体引用" in position:
        direct_subject = position.get("证据直接记载主体")
        if direct_subject and direct_subject != position.get("所属主体引用"):
            if position.get("所属主体引用") in target_ids and not position.get("关联路径引用"):
                raise ValidationError("证据直接记载主体与所属主体不一致且缺少关联路径")
        if position.get("所属主体引用") in target_ids and position.get("主体层级") != "目标主体":
            raise ValidationError("目标主体身份的主体层级不一致")


def _validate_schema(state: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(state),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        error = errors[0]
        path = ".".join(str(part) for part in error.absolute_path) or "根对象"
        raise ValidationError(f"Schema {path}：{error.message}")


def _build_indexes(state: dict) -> dict[str, dict[str, dict]]:
    indexes = {}
    seen = set()
    for collection, id_field in ID_FIELDS.items():
        index = {}
        for record in state.get(collection, []):
            record_id = record[id_field]
            if record_id in seen:
                raise ValidationError(f"编号重复：{record_id}")
            seen.add(record_id)
            index[record_id] = record
        indexes[collection] = index
    return indexes


def _require(indexes: dict, collection: str, record_id: str, owner: str) -> None:
    if record_id not in indexes[collection]:
        raise ValidationError(f"{owner}引用不存在：{record_id}")


def _validate_references(state: dict, indexes: dict) -> None:
    for entity_id in state["目标主体引用"]:
        _require(indexes, "公司主体", entity_id, "目标主体")
        if not indexes["公司主体"][entity_id]["是否目标主体"]:
            raise ValidationError(f"目标主体引用未标记为目标主体：{entity_id}")

    for entity in state["公司主体"]:
        for evidence_id in entity["证据引用"]:
            _require(indexes, "证据记录", evidence_id, entity["主体编号"])

    for relationship in state["主体关系"]:
        relationship_id = relationship["关系编号"]
        _require(indexes, "公司主体", relationship["起点主体引用"], relationship_id)
        _require(indexes, "公司主体", relationship["终点主体引用"], relationship_id)
        for evidence_id in relationship["证据引用"]:
            _require(indexes, "证据记录", evidence_id, relationship_id)

    for position in state["人员身份"]:
        position_id = position["身份编号"]
        _require(indexes, "核心人员", position["人员引用"], position_id)
        _require(indexes, "公司主体", position["所属主体引用"], position_id)
        if position_id not in indexes["核心人员"][position["人员引用"]]["身份引用"]:
            raise ValidationError(f"{position_id}与{position['人员引用']}缺少双向关联")
        for evidence_id in position["证据引用"]:
            _require(indexes, "证据记录", evidence_id, position_id)

    for person in state["核心人员"]:
        person_id = person["人员编号"]
        for position_id in person["身份引用"]:
            _require(indexes, "人员身份", position_id, person_id)
            if indexes["人员身份"][position_id]["人员引用"] != person_id:
                raise ValidationError(f"{person_id}与{position_id}缺少双向关联")

    for evidence in state["证据记录"]:
        evidence_id = evidence["证据编号"]
        for entity_id in evidence["主体引用"]:
            _require(indexes, "公司主体", entity_id, evidence_id)
        for relationship_id in evidence["主体关系引用"]:
            _require(indexes, "主体关系", relationship_id, evidence_id)
        for position_id in evidence["人员身份引用"]:
            _require(indexes, "人员身份", position_id, evidence_id)
        for relationship_id in evidence["主体映射关系引用"]:
            _require(indexes, "主体关系", relationship_id, evidence_id)

    query_targets = {
        "主体": "公司主体",
        "主体关系": "主体关系",
        "人员": "核心人员",
        "人员身份": "人员身份",
    }
    for query in state["查询记录"]:
        query_id = query["查询编号"]
        _require(indexes, query_targets[query["查询对象类型"]], query["查询对象引用"], query_id)
        for evidence_id in query["命中证据引用"]:
            _require(indexes, "证据记录", evidence_id, query_id)

    for result in state["主体调查结果"]:
        result_id = result["结果编号"]
        _require(indexes, "公司主体", result["主体引用"], result_id)
        for position_id in result["人员身份引用"]:
            _require(indexes, "人员身份", position_id, result_id)
        for query_id in result["查询记录引用"]:
            _require(indexes, "查询记录", query_id, result_id)

    result_entities = Counter(
        result["主体引用"] for result in state["主体调查结果"]
    )
    target_entities = set(state["目标主体引用"])
    if any(result_entities[entity_id] != 1 for entity_id in target_entities):
        raise ValidationError("目标主体调查结果必须一一对应")

    for issue_id in state["阶段判断"]["未解决关键事项"]:
        _require(indexes, "冲突与待确认项", issue_id, "阶段判断")


def _validate_relationship_evidence(state: dict, indexes: dict) -> None:
    for relationship in state["主体关系"]:
        if relationship["核验状态"] != "已核验":
            continue
        matching = [
            indexes["证据记录"][evidence_id]
            for evidence_id in relationship["证据引用"]
            if evidence_id in indexes["证据记录"]
        ]
        if not any(
            evidence["核验状态"] == "已核验"
            and evidence["证据等级"] != "线索证据"
            and relationship["关系编号"] in evidence["主体关系引用"]
            and relationship["起点主体引用"] in evidence["主体引用"]
            and relationship["终点主体引用"] in evidence["主体引用"]
            and relationship["关系类型"] in evidence["证明范围"]
            for evidence in matching
        ):
            raise ValidationError(f"{relationship['关系编号']}缺少证明关系类型和两端主体的证据")


def _validate_position_evidence(state: dict, indexes: dict) -> None:
    target_ids = set(state["目标主体引用"])
    for position in state["人员身份"]:
        if position["所属主体引用"] in target_ids and position["主体层级"] != "目标主体":
            raise ValidationError(f"{position['身份编号']}主体层级与目标主体不一致")
        if position["所属主体引用"] not in target_ids and position["主体层级"] == "目标主体":
            raise ValidationError(f"{position['身份编号']}主体层级与关联主体不一致")

        if position["身份时态"] == "历史" and position["时效状态"] != "仅证明历史身份":
            raise ValidationError("历史身份必须标记为仅证明历史身份")
        if position["身份时态"] == "当前" and position["时效状态"] == "仅证明历史身份":
            raise ValidationError("当前身份不得标记为仅证明历史身份")
        if position["身份时态"] == "时点不明" and position["时效状态"] != "当前性待复核":
            raise ValidationError("时点不明身份不得标记为当前性充分或仅证明历史身份")
        if position["结束日期"] is not None and position["身份时态"] != "历史":
            raise ValidationError("存在结束日期的身份必须标记为历史")

        if position["核验状态"] != "已核验":
            continue
        matching = [
            indexes["证据记录"][evidence_id]
            for evidence_id in position["证据引用"]
            if evidence_id in indexes["证据记录"]
        ]
        scoped = [
            evidence
            for evidence in matching
            if evidence["核验状态"] == "已核验"
            and position["身份编号"] in evidence["人员身份引用"]
            and position["所属主体引用"] in evidence["主体引用"]
            and position["身份类型"] in evidence["证明范围"]
        ]
        if not scoped:
            raise ValidationError(
                f"{position['身份编号']}缺少证明人员、所属主体和身份类型的证据；证据主体层级不匹配"
            )
        if position["身份类型"] in HIGH_RISK_IDENTITIES and all(
            evidence["证据等级"] == "线索证据" for evidence in scoped
        ):
            raise ValidationError(f"线索证据不得单独确认{position['身份类型']}")
        if position["身份时态"] == "当前" and position["时效状态"] == "当前性充分" and not any(
            evidence["持续有效说明"].strip() for evidence in scoped
        ):
            raise ValidationError(f"{position['身份编号']}缺少当前持续有效说明")


def _validate_expansion_scope(state: dict, indexes: dict) -> None:
    for relationship in state["主体关系"]:
        if relationship["扩展层数"] == 2:
            if not relationship["纳入理由"].strip():
                raise ValidationError("二跳例外主体缺少纳入理由")
            if relationship["目标业务相关性"] != "直接相关":
                raise ValidationError("二跳例外主体必须与目标业务直接相关")


def _validate_query_results(state: dict, indexes: dict) -> None:
    for query in state["查询记录"]:
        validate_query_quality(query)
        if query["命中情况"] == "已查询但未发现" and query["访问结果"] != "成功":
            raise ValidationError(f"{query['查询编号']}未成功访问时不得记录已查询但未发现")
        if query["命中情况"] == "已发现" and not query["命中证据引用"]:
            raise ValidationError(f"{query['查询编号']}记录已发现但没有命中证据")

    for result in state["主体调查结果"]:
        entity_id = result["主体引用"]
        queries = [
            indexes["查询记录"][query_id]
            for query_id in result["查询记录引用"]
        ]
        for query in queries:
            query_type = query["查询对象类型"]
            query_target = query["查询对象引用"]
            belongs_to_entity = (
                (query_type == "主体" and query_target == entity_id)
                or (
                    query_type == "主体关系"
                    and entity_id
                    in {
                        indexes["主体关系"][query_target]["起点主体引用"],
                        indexes["主体关系"][query_target]["终点主体引用"],
                    }
                )
                or (
                    query_type == "人员身份"
                    and indexes["人员身份"][query_target]["所属主体引用"] == entity_id
                )
                or (
                    query_type == "人员"
                    and any(
                        indexes["人员身份"][position_id]["所属主体引用"] == entity_id
                        for position_id in indexes["核心人员"][query_target]["身份引用"]
                    )
                )
            )
            if not belongs_to_entity:
                raise ValidationError(
                    f"{query['查询编号']}查询对象与结果主体不匹配：{entity_id}"
                )
        progress = result["调查进度"]
        fact_status = result["事实核验状态"]
        verified_positions = [
            indexes["人员身份"][position_id]
            for position_id in result["人员身份引用"]
            if indexes["人员身份"][position_id]["核验状态"] == "已核验"
        ]
        if progress != "调查完成" and fact_status in {"已核验", "部分核验", "未发现"}:
            raise ValidationError(
                f"{result['结果编号']}调查进度为{progress}时不得标记为{fact_status}"
            )
        if progress != "调查完成":
            continue

        if fact_status == "已核验" and not verified_positions:
            raise ValidationError(f"{result['结果编号']}已核验但没有已核验人员身份")
        if fact_status == "部分核验" and not verified_positions:
            raise ValidationError(f"{result['结果编号']}部分核验但没有已核验人员身份")
        independent_queries = [query for query in queries if query["是否独立核验"]]
        if not independent_queries:
            raise ValidationError(f"{result['结果编号']}调查完成但没有独立核验查询")
        covered_dimensions = {
            query["查询维度"]
            for query in independent_queries
            if query_supports_independent_conclusion(query, indexes["证据记录"])
        }
        missing_dimensions = sorted(REQUIRED_COMPLETION_QUERY_DIMENSIONS - covered_dimensions)
        if missing_dimensions:
            raise ValidationError(
                f"{result['结果编号']}调查完成但查询维度不足：{'、'.join(missing_dimensions)}"
            )
        if result["事实核验状态"] != "未发现":
            continue
        people_dimensions = {"控制与所有权", "最高管理层", "技术与研发负责人"}
        no_hit_dimensions = {
            query["查询维度"]
            for query in independent_queries
            if query["查询维度"] in people_dimensions
            and query["访问结果"] == "成功"
            and query["命中情况"] == "已查询但未发现"
        }
        if no_hit_dimensions != people_dimensions:
            raise ValidationError("未发现必须覆盖全部人员查询维度并分别记录成功未命中")


def _validate_summary(state: dict) -> None:
    judgment = state["阶段判断"]
    expected = {
        "主体总数": len(state["公司主体"]),
        "已识别人员数": len(state["核心人员"]),
        "已核验身份数": sum(position["核验状态"] == "已核验" for position in state["人员身份"]),
    }
    for field, value in expected.items():
        if judgment[field] != value:
            raise ValidationError(f"阶段判断.{field}必须为{value}")

    unresolved = [
        issue["事项编号"]
        for issue in state["冲突与待确认项"]
        if issue["是否关键"] and issue["状态"] == "未解决"
    ]
    if judgment["未解决关键事项"] != unresolved:
        raise ValidationError(f"阶段判断.未解决关键事项必须为{unresolved}")
    overall = derive_overall_status(state)
    if judgment["整体状态"] != overall:
        raise ValidationError(f"阶段判断.整体状态必须为{overall}")
    expected_confirmation = overall in {"待补充输入", "待确认范围", "待审阅", "部分完成"}
    if judgment["需要用户确认"] is not expected_confirmation:
        raise ValidationError(f"阶段判断.需要用户确认必须为{str(expected_confirmation).lower()}")


def validate_state(state: dict) -> None:
    _validate_schema(state)
    indexes = _build_indexes(state)
    _validate_references(state, indexes)
    _validate_relationship_evidence(state, indexes)
    _validate_position_evidence(state, indexes)
    _validate_expansion_scope(state, indexes)
    _validate_query_results(state, indexes)
    relationship_ids = set(indexes["主体关系"])
    target_ids = set(state["目标主体引用"])
    for position in state["人员身份"]:
        validate_position_quality(position, target_ids, relationship_ids)
    for person in state["核心人员"]:
        validate_position_quality(person, target_ids, relationship_ids)
    for evidence in state["证据记录"]:
        validate_evidence_quality(evidence)
        validate_evidence_source_scope(
            evidence,
            indexes["公司主体"],
            indexes["主体关系"],
        )
    for entity in state["公司主体"]:
        validate_entity_evidence(entity, indexes["证据记录"])
    _validate_summary(state)
    stored_hash = state["渲染元数据"]["状态内容哈希"]
    if stored_hash and stored_hash != state_hash(state):
        raise ValidationError("渲染元数据.状态内容哈希与事实底稿不一致")


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：python scripts/validate_state.py STATE_PATH", file=sys.stderr)
        return 2
    try:
        state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        validate_state(state)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"校验失败：{error}", file=sys.stderr)
        return 1
    print("调查状态校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
