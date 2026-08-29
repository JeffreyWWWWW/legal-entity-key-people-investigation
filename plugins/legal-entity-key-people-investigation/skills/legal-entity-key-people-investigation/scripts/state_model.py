import copy
import hashlib
import json
import re


WINDOWS_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def canonical_json(state: dict) -> str:
    return json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def state_hash(state: dict) -> str:
    facts = copy.deepcopy(state)
    facts.pop("渲染元数据", None)
    return hashlib.sha256(canonical_json(facts).encode("utf-8")).hexdigest().upper()


def next_id(records: list[dict], key: str, prefix: str) -> str:
    pattern = re.compile(rf"^{re.escape(prefix)}-([0-9]+)$")
    suffixes = [
        int(match.group(1))
        for record in records
        if (match := pattern.match(str(record.get(key, ""))))
    ]
    return f"{prefix}-{max(suffixes, default=0) + 1:03d}"


def sanitize_filename_component(value: str) -> str:
    cleaned = WINDOWS_INVALID_FILENAME_CHARS.sub("_", value).strip().rstrip(". ")
    cleaned = re.sub(r"_+", "_", cleaned)
    if not cleaned:
        return "未命名项目"
    if cleaned.upper() in WINDOWS_RESERVED_NAMES:
        return f"_{cleaned}"
    return cleaned


def chinese_count(value: int) -> str:
    digits = "零一二三四五六七八九"
    if value < 10:
        return digits[value]
    if value < 20:
        return "十" + (digits[value % 10] if value % 10 else "")
    if value < 100:
        return digits[value // 10] + "十" + (digits[value % 10] if value % 10 else "")
    return str(value)


def delivery_scope(state: dict) -> str:
    project_name = state.get("任务元数据", {}).get("项目名称", "").strip()
    if project_name:
        return sanitize_filename_component(project_name)

    target_ids = state.get("目标主体引用", [])
    if len(target_ids) == 1:
        target_id = target_ids[0]
        for entity in state.get("公司主体", []):
            if entity.get("主体编号") == target_id:
                name = entity.get("规范法律名称", "").strip()
                if name:
                    return sanitize_filename_component(name)
    return f"{chinese_count(len(target_ids))}主体"


def delivery_filenames(state: dict) -> tuple[str, str]:
    scope = delivery_scope(state)
    investigation_date = state.get("任务元数据", {}).get("调查基准日", "")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", investigation_date):
        raise ValueError("任务元数据.调查基准日必须为 YYYY-MM-DD")
    date_token = investigation_date.replace("-", "")
    return (
        f"{scope}_法律主体核心人员调查底稿_{date_token}.json",
        f"{scope}_法律主体核心人员调查审阅件_{date_token}.xlsx",
    )


def derive_overall_status(state: dict) -> str:
    topic = state.get("技术主题", {}).get("主题名称", "").strip()
    targets = state.get("目标主体引用", [])
    if not topic or not targets:
        return "待补充输入"

    if any(
        issue.get("是否关键") is True and issue.get("状态") == "未解决"
        for issue in state.get("冲突与待确认项", [])
    ):
        return "待确认范围"

    results = state.get("主体调查结果", [])
    if not results:
        return "调查中"

    approvals = state.get("用户确认记录", [])
    confirmed_objects = {
        reference
        for approval in approvals
        if approval.get("确认类型") in {"确认结果", "接受限制"}
        for reference in approval.get("关联对象引用", [])
    }
    resolved = [
        result.get("调查进度") == "调查完成"
        and result.get("事实核验状态") in {"已核验", "部分核验", "未发现"}
        for result in results
    ]
    confirmed = [result.get("结果编号") in confirmed_objects for result in results]
    if all(resolved) and all(confirmed):
        return "已完成"
    if any(resolved) and any(not item for item in resolved):
        return "部分完成"
    if any(resolved):
        return "待审阅"

    unresolved = [result for result, is_resolved in zip(results, resolved) if not is_resolved]
    if unresolved and all(
        result.get("调查进度") == "待人工查询" and bool(result.get("阻塞原因"))
        for result in unresolved
    ):
        return "已阻塞"
    return "调查中"
