import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts"
sys.path.insert(0, str(SCRIPTS))

from migrate_state import migrate_state


def test_migration_conservatively_downgrades_unmapped_verified_facts():
    state = {
        "规范版本": "1.1.0",
        "skill_version": "1.2.0",
        "公司主体": [
            {
                "主体编号": "ENT-001",
                "主体身份状态": "已核验",
                "证据引用": ["EVD-001"],
            }
        ],
        "主体关系": [
            {"关系编号": "REL-001", "核验状态": "已核验", "证据引用": ["EVD-001"]}
        ],
        "人员身份": [
            {
                "身份编号": "POS-001",
                "所属主体引用": "ENT-001",
                "核验状态": "已核验",
                "可靠性": "高",
                "证据引用": ["EVD-001"],
            }
        ],
        "证据记录": [
            {
                "证据编号": "EVD-001",
                "主体引用": ["ENT-001"],
                "来源类别": "官方公告",
                "证据等级": "较强证据",
                "核验状态": "已核验",
                "持续有效说明": "",
            }
        ],
        "查询记录": [
            {
                "查询编号": "QRY-001",
                "是否独立核验": True,
                "命中情况": "已发现",
                "后续动作": "",
            }
        ],
        "主体调查结果": [
            {
                "结果编号": "RES-001",
                "调查进度": "调查完成",
                "事实核验状态": "部分核验",
            }
        ],
        "技术主题": {"主题名称": "牵引产品"},
        "目标主体引用": ["ENT-001"],
        "冲突与待确认项": [],
        "用户确认记录": [],
        "阶段判断": {
            "整体状态": "待审阅",
            "已核验身份数": 1,
            "需要用户确认": True,
        },
        "渲染元数据": {"状态内容哈希": "OLD"},
    }

    migrated = migrate_state(state)

    assert migrated["规范版本"] == "1.2.0"
    assert migrated["skill_version"] == "1.3.0"
    assert migrated["查询记录"][0]["是否独立核验"] is False
    assert migrated["查询记录"][0]["原文定位状态"] == "无法定位"
    assert migrated["证据记录"][0]["核验状态"] == "待核验"
    assert migrated["公司主体"][0]["主体身份状态"] == "待核验"
    assert migrated["主体关系"][0]["核验状态"] == "待核验"
    assert migrated["人员身份"][0]["核验状态"] == "待核验"
    assert migrated["人员身份"][0]["可靠性"] == "待判断"
    assert migrated["主体调查结果"][0]["调查进度"] == "调查中"
    assert migrated["主体调查结果"][0]["事实核验状态"] == "待核验"
    assert migrated["阶段判断"]["已核验身份数"] == 0
    assert migrated["阶段判断"]["整体状态"] == "调查中"
    assert migrated["阶段判断"]["需要用户确认"] is False
    assert migrated["渲染元数据"]["状态内容哈希"] == ""


def test_migration_reduces_combined_source_record_to_the_available_url():
    state = {
        "规范版本": "1.1.0",
        "skill_version": "1.2.0",
        "查询记录": [],
        "人员身份": [],
        "公司主体": [],
        "主体关系": [],
        "主体调查结果": [],
        "阶段判断": {},
        "渲染元数据": {},
        "证据记录": [
            {
                "证据编号": "EVD-001",
                "发布主体": "LinkedIn / D&B / Datanyze",
                "原始URL": "https://www.linkedin.com/in/example",
                "URL或文件路径": "https://www.linkedin.com/in/example",
                "来源类别": "第三方数据库",
                "证据等级": "线索证据",
                "核验状态": "待核验",
                "主体引用": [],
                "关键原文": "多个数据库一致显示候选职务",
                "持续有效说明": "",
            }
        ],
    }

    migrated = migrate_state(state)
    evidence = migrated["证据记录"][0]

    assert evidence["发布主体"] == "www.linkedin.com"
    assert evidence["关键原文"] == "迁移记录仅保留现有原始URL；原多源摘要不可作为原文。"
    assert "原多源发布主体：LinkedIn / D&B / Datanyze" in evidence["持续有效说明"]
