import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_state import ValidationError, validate_state


FIXTURE = ROOT / "tests/fixtures/minimal-valid-state.json"


def load_state():
    state = json.loads(FIXTURE.read_text(encoding="utf-8"))
    state["任务元数据"].setdefault("项目名称", "")
    return state


def set_overview(state, overall, confirmation):
    state["阶段判断"].update({
        "整体状态": overall,
        "已识别人员数": len(state["核心人员"]),
        "已核验身份数": sum(
            position["核验状态"] == "已核验" for position in state["人员身份"]
        ),
        "需要用户确认": confirmation,
    })


def add_verified_ceo(state):
    state["核心人员"] = [{
        "人员编号": "PER-001",
        "规范姓名": "Test Executive",
        "原始姓名": ["Test Executive"],
        "去重辅助信息": [],
        "身份引用": ["POS-001"],
    }]
    state["人员身份"] = [{
        "身份编号": "POS-001",
        "人员引用": "PER-001",
        "所属主体引用": "ENT-001",
        "身份类型": "CEO",
        "职务原文": "Chief Executive Officer",
        "主体层级": "目标主体",
        "身份时态": "当前",
        "开始日期": None,
        "结束日期": None,
        "时效状态": "当前性充分",
        "目标业务相关性": "间接相关",
        "纳入理由": "目标主体最高管理人员",
        "核验状态": "已核验",
        "可靠性": "高",
        "证据引用": ["EVD-001"],
        "复核建议": "",
        "关联路径引用": [],
        "证据直接记载主体": "ENT-001",
        "是否直接任职证据": True,
    }]
    state["证据记录"] = [{
        "证据编号": "EVD-001",
        "来源类型": "公司官网管理层页面",
        "标题": "Executive leadership",
        "URL或文件路径": "https://example.com/leadership",
        "文件日期": "2026-08-29",
        "查询日期": "2026-08-29",
        "关键原文": "Test Executive is Chief Executive Officer.",
        "证明范围": ["CEO"],
        "主体引用": ["ENT-001"],
        "主体关系引用": [],
        "人员身份引用": ["POS-001"],
        "证据等级": "较强证据",
        "核验状态": "已核验",
        "持续有效说明": "官网在调查基准日仍列示该职务。",
        "来源类别": "公司官网",
        "发布主体": "Progress Mfg. Inc.",
        "来源标题": "Executive leadership",
        "原始URL": "https://example.com/leadership",
        "原文主体名称": ["Progress Mfg. Inc."],
        "主体映射关系引用": [],
    }]
    state["公司主体"][0]["证据引用"] = ["EVD-001"]
    state["主体调查结果"][0]["人员身份引用"] = ["POS-001"]


class CompletionGateRegressionTests(unittest.TestCase):
    def test_investigation_in_progress_cannot_be_verified(self):
        state = load_state()
        state["主体调查结果"][0]["事实核验状态"] = "已核验"

        with self.assertRaisesRegex(ValidationError, "调查中.*已核验"):
            validate_state(state)

    def test_completed_verified_result_requires_verified_position(self):
        state = load_state()
        state["主体调查结果"][0].update({
            "调查进度": "调查完成",
            "事实核验状态": "已核验",
        })
        set_overview(state, "待审阅", True)

        with self.assertRaisesRegex(ValidationError, "已核验.*人员身份"):
            validate_state(state)

    def test_user_report_query_cannot_complete_partial_investigation(self):
        state = load_state()
        add_verified_ceo(state)
        state["查询记录"] = [{
            "查询编号": "QRY-001",
            "查询对象类型": "主体",
            "查询对象引用": "ENT-001",
            "数据源": "用户提供 Word 报告及其列示公开来源",
            "查询维度": "最高管理层",
            "是否独立核验": False,
            "查询词": ["Progress Mfg. Inc."],
            "查询时间": "2026-08-29T09:00:00+08:00",
            "访问结果": "成功",
            "命中情况": "已发现",
            "命中证据引用": ["EVD-001"],
            "阻塞原因": "",
            "后续动作": "",
            "数据源类型": "用户材料",
            "实际访问位置": "用户提供 Word 报告",
            "访问内容摘要": "报告列示候选最高管理层信息。",
            "未命中范围": "",
            "候选URL": "",
            "原始来源URL": "",
            "原文定位状态": "不适用",
        }]
        state["主体调查结果"][0].update({
            "调查进度": "调查完成",
            "事实核验状态": "部分核验",
            "查询记录引用": ["QRY-001"],
        })
        set_overview(state, "待审阅", True)

        with self.assertRaisesRegex(ValidationError, "独立.*查询"):
            validate_state(state)

    def test_single_generic_no_hit_query_cannot_prove_no_people_found(self):
        state = load_state()
        state["查询记录"] = [{
            "查询编号": "QRY-001",
            "查询对象类型": "主体",
            "查询对象引用": "ENT-001",
            "数据源": "公司官网",
            "查询维度": "主体身份",
            "是否独立核验": True,
            "查询词": ["Progress Mfg. Inc."],
            "查询时间": "2026-08-29T09:00:00+08:00",
            "访问结果": "成功",
            "命中情况": "已查询但未发现",
            "命中证据引用": [],
            "阻塞原因": "",
            "后续动作": "",
            "数据源类型": "公司官网",
            "实际访问位置": "https://example.com/",
            "访问内容摘要": "仅执行了一次泛化主体查询。",
            "未命中范围": "公司官网首页",
            "候选URL": "",
            "原始来源URL": "https://example.com/",
            "原文定位状态": "不适用",
        }]
        state["主体调查结果"][0].update({
            "调查进度": "调查完成",
            "事实核验状态": "未发现",
            "查询记录引用": ["QRY-001"],
        })
        set_overview(state, "待审阅", True)

        with self.assertRaisesRegex(ValidationError, "查询维度"):
            validate_state(state)


if __name__ == "__main__":
    unittest.main()
