import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/legal-entity-key-people-investigation/skills/legal-entity-key-people-investigation/scripts"
sys.path.insert(0, str(SCRIPTS))

from validate_state import (
    ValidationError,
    query_supports_independent_conclusion,
    validate_entity_evidence,
    validate_evidence_quality,
    validate_evidence_source_scope,
    validate_position_quality,
    validate_query_quality,
)


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


@pytest.mark.parametrize("access_result", ["访问受限", "付费墙", "失败"])
def test_blocked_access_cannot_be_independent_verification(access_result):
    query = {
        "是否独立核验": True,
        "数据源": "LinkedIn",
        "数据源类型": "第三方数据库",
        "实际访问位置": "https://example.com/profile",
        "访问内容摘要": "页面跳转到登录墙",
        "未命中范围": "",
        "命中情况": "已发现",
        "访问结果": access_result,
    }
    with pytest.raises(ValidationError, match="成功访问"):
        validate_query_quality(query)


def test_unlocated_quote_cannot_be_independent_verification():
    query = {
        "是否独立核验": True,
        "数据源": "行业组织页面",
        "数据源类型": "媒体",
        "实际访问位置": "https://example.com/news",
        "访问内容摘要": "搜索索引显示相关文字，但页面内无法定位",
        "未命中范围": "",
        "原文定位状态": "无法定位",
        "命中情况": "已发现",
        "访问结果": "成功",
    }
    with pytest.raises(ValidationError, match="原文"):
        validate_query_quality(query)


def test_media_evidence_cannot_be_stronger_than_lead():
    evidence = {"来源类别": "行业媒体", "证据等级": "较强证据"}
    with pytest.raises(ValidationError):
        validate_evidence_quality(evidence)


def test_combined_sources_require_separate_evidence_records():
    evidence = {
        "来源类别": "第三方数据库",
        "证据等级": "线索证据",
        "发布主体": "LinkedIn / D&B / Datanyze",
        "原始URL": "https://example.com/profile",
    }
    with pytest.raises(ValidationError, match="单一来源"):
        validate_evidence_quality(evidence)


def test_joint_filing_attribution_is_not_treated_as_combined_sources():
    evidence = {
        "来源类别": "监管文件",
        "证据等级": "强证据",
        "发布主体": "U.S. Securities and Exchange Commission / Example Issuer",
        "原始URL": "https://www.sec.gov/example",
    }
    validate_evidence_quality(evidence)


def test_evidence_subject_name_requires_verified_mapping():
    evidence = {
        "证据编号": "EVD-001",
        "核验状态": "已核验",
        "原文主体名称": ["CURT Group"],
        "主体引用": ["ENT-001"],
        "主体映射关系引用": [],
    }
    entities = {
        "ENT-001": {
            "规范法律名称": "Curt Manufacturing, LLC",
            "原始名称": ["Curt Manufacturing, LLC"],
            "名称变体": ["CURT Manufacturing LLC"],
        }
    }
    with pytest.raises(ValidationError, match="原文主体"):
        validate_evidence_source_scope(evidence, entities, {})


def test_unmapped_lead_can_be_retained_for_follow_up():
    evidence = {
        "证据编号": "EVD-001",
        "核验状态": "待核验",
        "原文主体名称": [],
        "主体引用": ["ENT-001"],
        "主体映射关系引用": [],
    }
    entities = {"ENT-001": {"规范法律名称": "Target, LLC"}}
    validate_evidence_source_scope(evidence, entities, {})


def test_unverified_entity_alias_does_not_bypass_subject_mapping():
    evidence = {
        "证据编号": "EVD-001",
        "核验状态": "已核验",
        "原文主体名称": ["CURT Group"],
        "主体引用": ["ENT-001"],
        "主体映射关系引用": [],
    }
    entities = {
        "ENT-001": {
            "规范法律名称": "Curt Manufacturing, LLC",
            "原始名称": ["CURT Group"],
            "名称变体": ["CURT Group"],
        }
    }
    with pytest.raises(ValidationError, match="原文主体"):
        validate_evidence_source_scope(evidence, entities, {})


def test_verified_mapping_allows_different_source_subject_name():
    evidence = {
        "证据编号": "EVD-001",
        "核验状态": "已核验",
        "原文主体名称": ["CURT Group"],
        "主体引用": ["ENT-001"],
        "主体映射关系引用": ["REL-001"],
    }
    entities = {
        "ENT-001": {
            "规范法律名称": "Curt Manufacturing, LLC",
            "原始名称": ["Curt Manufacturing, LLC"],
            "名称变体": [],
        },
        "ENT-002": {
            "规范法律名称": "CURT Group",
            "原始名称": ["CURT Group"],
            "名称变体": [],
        },
    }
    relationships = {
        "REL-001": {
            "起点主体引用": "ENT-002",
            "终点主体引用": "ENT-001",
            "关系类型": "商业名称",
            "核验状态": "已核验",
        }
    }
    validate_evidence_source_scope(evidence, entities, relationships)


def test_relationship_cannot_map_its_own_subject_names():
    evidence = {
        "证据编号": "EVD-001",
        "核验状态": "已核验",
        "原文主体名称": ["CURT Group", "Lippert Components, Inc."],
        "主体引用": ["ENT-001", "ENT-002"],
        "主体关系引用": ["REL-001"],
        "主体映射关系引用": ["REL-001"],
    }
    entities = {
        "ENT-001": {"规范法律名称": "Curt Manufacturing, LLC"},
        "ENT-002": {"规范法律名称": "Lippert Components, Inc."},
    }
    relationships = {
        "REL-001": {
            "起点主体引用": "ENT-002",
            "终点主体引用": "ENT-001",
            "关系类型": "收购方",
            "核验状态": "已核验",
        }
    }
    with pytest.raises(ValidationError, match="ENT-001"):
        validate_evidence_source_scope(evidence, entities, relationships)


def test_each_cited_entity_requires_direct_name_or_verified_mapping():
    evidence = {
        "证据编号": "EVD-001",
        "核验状态": "已核验",
        "原文主体名称": ["Parent Holdings, Inc."],
        "主体引用": ["ENT-001", "ENT-002"],
        "主体映射关系引用": [],
    }
    entities = {
        "ENT-001": {"规范法律名称": "Target, LLC"},
        "ENT-002": {"规范法律名称": "Parent Holdings, Inc."},
    }
    with pytest.raises(ValidationError, match="ENT-001"):
        validate_evidence_source_scope(evidence, entities, {})


def test_verified_entity_requires_verified_non_lead_identity_evidence():
    entity = {
        "主体编号": "ENT-001",
        "主体身份状态": "已核验",
        "证据引用": ["EVD-001"],
    }
    evidence = {
        "EVD-001": {
            "主体引用": ["ENT-001"],
            "证明范围": ["主体身份"],
            "证据等级": "线索证据",
            "核验状态": "待核验",
        }
    }
    with pytest.raises(ValidationError, match="主体身份"):
        validate_entity_evidence(entity, evidence)


def test_lead_evidence_does_not_form_independent_conclusion():
    query = {
        "是否独立核验": True,
        "访问结果": "成功",
        "命中情况": "已发现",
        "命中证据引用": ["EVD-001"],
    }
    evidence = {
        "EVD-001": {"证据等级": "线索证据", "核验状态": "待核验"},
    }
    assert not query_supports_independent_conclusion(query, evidence)


def test_verified_source_forms_independent_conclusion():
    query = {
        "查询对象类型": "人员身份",
        "查询对象引用": "POS-001",
        "是否独立核验": True,
        "访问结果": "成功",
        "命中情况": "已发现",
        "命中证据引用": ["EVD-001"],
    }
    evidence = {
        "EVD-001": {
            "证据等级": "较强证据",
            "核验状态": "已核验",
            "人员身份引用": ["POS-001"],
        },
    }
    assert query_supports_independent_conclusion(query, evidence)


def test_unrelated_verified_evidence_does_not_complete_query():
    query = {
        "查询对象类型": "人员身份",
        "查询对象引用": "POS-001",
        "是否独立核验": True,
        "访问结果": "成功",
        "命中情况": "已发现",
        "命中证据引用": ["EVD-001"],
    }
    evidence = {
        "EVD-001": {
            "证据等级": "强证据",
            "核验状态": "已核验",
            "主体引用": ["ENT-001"],
            "人员身份引用": [],
        },
    }
    assert not query_supports_independent_conclusion(query, evidence)


def test_wrong_proof_scope_does_not_complete_query_dimension():
    query = {
        "查询对象类型": "主体",
        "查询对象引用": "ENT-001",
        "查询维度": "技术与研发负责人",
        "是否独立核验": True,
        "访问结果": "成功",
        "命中情况": "已发现",
        "命中证据引用": ["EVD-001"],
    }
    evidence = {
        "EVD-001": {
            "证据等级": "强证据",
            "核验状态": "已核验",
            "主体引用": ["ENT-001"],
            "证明范围": ["主体身份"],
        },
    }
    assert not query_supports_independent_conclusion(query, evidence)


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
