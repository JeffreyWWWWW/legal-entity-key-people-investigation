import argparse
import hashlib
import json
import sys
from pathlib import Path

if __package__:
    from .state_model import canonical_json, derive_overall_status, state_hash
else:
    from state_model import canonical_json, derive_overall_status, state_hash


SOURCE_TYPES = {
    ".json": "JSON",
    ".xlsx": "Excel",
    ".xls": "Excel",
    ".docx": "Word",
    ".pdf": "PDF",
    ".png": "图片",
    ".jpg": "图片",
    ".jpeg": "图片",
}


def build_state(args: argparse.Namespace) -> dict:
    entities = []
    results = []
    for index, name in enumerate(args.entity, start=1):
        entity_id = f"ENT-{index:03d}"
        entities.append(
            {
                "主体编号": entity_id,
                "原始名称": [name],
                "规范法律名称": name,
                "注册地": "",
                "唯一识别信息": [],
                "名称变体": [],
                "主体身份状态": "待核验",
                "是否目标主体": True,
                "证据引用": [],
                "待复核事项": [],
            }
        )
        results.append(
            {
                "结果编号": f"RES-{index:03d}",
                "主体引用": entity_id,
                "调查进度": "调查中",
                "事实核验状态": "待核验",
                "人员身份引用": [],
                "查询记录引用": [],
                "阻塞原因": [],
                "复核建议": [],
            }
        )

    sources = []
    for index, source_text in enumerate(args.source, start=1):
        source = Path(source_text).resolve()
        digest = hashlib.sha256(source.read_bytes()).hexdigest().upper()
        sources.append(
            {
                "材料编号": f"SRC-{index:03d}",
                "类型": SOURCE_TYPES.get(source.suffix.lower(), "其他"),
                "原始名称": source.name,
                "路径或对话引用": str(source),
                "SHA256": digest,
                "登记时间": args.timestamp,
                "用途": "用户提供的调查输入",
            }
        )

    state = {
        "规范版本": "1.0.0",
        "任务元数据": {
            "任务编号": args.task_id,
            "项目名称": args.project_name,
            "调查基准日": args.as_of,
            "创建时间": args.timestamp,
            "更新时间": args.timestamp,
            "原始请求": args.request,
        },
        "输入材料": sources,
        "技术主题": {
            "主题名称": args.topic,
            "主题描述": args.topic_description,
            "产品或技术关键词": list(dict.fromkeys(args.keyword)),
            "用户原文引用": [],
        },
        "目标主体引用": [item["主体编号"] for item in entities],
        "公司主体": entities,
        "主体关系": [],
        "核心人员": [],
        "人员身份": [],
        "证据记录": [],
        "查询记录": [],
        "冲突与待确认项": [],
        "主体调查结果": results,
        "阶段判断": {
            "整体状态": "调查中",
            "主体总数": len(entities),
            "已识别人员数": 0,
            "已核验身份数": 0,
            "未解决关键事项": [],
            "需要用户确认": False,
            "用户可执行动作": [],
        },
        "用户确认记录": [],
        "渲染元数据": {
            "状态内容哈希": "",
            "渲染器版本": "",
            "最近渲染时间": None,
        },
    }
    state["阶段判断"]["整体状态"] = derive_overall_status(state)
    state["渲染元数据"]["状态内容哈希"] = state_hash(state)
    return state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化法律主体核心人员调查状态")
    parser.add_argument("output", type=Path)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--project-name", default="")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--timestamp", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--topic-description", default="")
    parser.add_argument("--keyword", action="append", default=[])
    parser.add_argument("--entity", action="append", required=True)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--request", default="")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists() and not args.force:
        print(f"初始化失败：输出文件已存在：{args.output}", file=sys.stderr)
        return 1
    try:
        state = build_state(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(canonical_json(state) + "\n", encoding="utf-8")
    except OSError as error:
        print(f"初始化失败：{error}", file=sys.stderr)
        return 1
    print(f"已初始化：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
