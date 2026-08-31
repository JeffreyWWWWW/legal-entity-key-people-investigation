import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts"
sys.path.insert(0, str(SCRIPTS))

from validate_state import ValidationError, validate_query_quality, validate_evidence_quality, validate_position_quality


def test_generic_source_cannot_be_independent_verification():
    query = {
        "是否独立核验": True,
        "数据源": "原始官网、监管文件或公开登记入口",
        "数据源类型": "其他",
        "实际访问位置": "",
        "访问内容摘要": "",
        "命中情况": "已发现",
        "访问结果": "成功",
    }
    with pytest.raises(ValidationError):
        validate_query_quality(query)


def test_no_hit_requires_scope_and_location():
    query = {
        "是否独立核验": True,
        "数据源": "公司官网",
        "数据源类型": "公司官网",
        "实际访问位置": "https://example.com/leadership",
        "访问内容摘要": "未找到管理层页面",
        "未命中范围": "",
        "命中情况": "已查询但未发现",
        "访问结果": "成功",
    }
    with pytest.raises(ValidationError):
        validate_query_quality(query)


def test_media_evidence_cannot_be_stronger_than_lead():
    evidence = {"来源类别": "行业媒体", "证据等级": "较强证据"}
    with pytest.raises(ValidationError):
        validate_evidence_quality(evidence)


def test_parent_position_requires_relationship_path_and_direct_subject():
    position = {
        "主体层级": "目标主体",
        "证据直接记载主体": "ENT-002",
        "所属主体引用": "ENT-001",
        "是否直接任职证据": True,
        "关联路径引用": [],
    }
    with pytest.raises(ValidationError):
        validate_position_quality(position, {"ENT-001"}, set())


def test_institution_name_is_not_a_natural_person():
    person = {"规范姓名": "BlackRock"}
    with pytest.raises(ValidationError):
        validate_position_quality(person, set(), set())
