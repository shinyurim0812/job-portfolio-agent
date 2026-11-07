"""check_analysis: AI가 '공고 원문'이라고 적은 인용이 공고에 실제로 있는지 등.

샘플 공고는 테스트용으로 지어낸 문장이다(실제 회사 공고 아님).
"""
import copy

import pytest

from check_analysis import check, normalize

JD = """■ 주요업무
• 고객사의 흩어진 요청(회의록, 메일, 스프레드시트)을 읽고 요청 뒤의 목적을 찾아, 만들 기능을 한 문장으로 정리합니다.
• 코딩 에이전트에게 작업을 맡깁니다. 목표와 완료 조건,
검증 방법을 먼저 정하고 결과를 확인합니다.
• 시안을 배포된 주소로 만들어 사용자에게 보여 주고, 의견을 받아 다시 고칩니다.
■ 이런 분을 찾습니다
요청 뒤의 목적을 읽습니다. 크게 맡기고 확인합니다. 끈기가 있습니다.
"""

GOOD = {
    "title_dept": {"analysis": "인턴. 부서: 미기재"},
    "core_tasks": [
        {"name": "요청 정리", "quote": "흩어진 요청(회의록, 메일, 스프레드시트)을 읽고 요청 뒤의 목적을 찾아", "analysis": "..."},
        # 원문에서는 줄바꿈으로 끊긴 문장 — 정규화 후 일치해야 함
        {"name": "에이전트 위임", "quote": "목표와 완료 조건, 검증 방법을 먼저 정하고 결과를 확인합니다.", "analysis": "..."},
        {"name": "시안 배포", "quote": "“시안을 배포된 주소로 만들어 사용자에게 보여 주고”", "analysis": "..."},
    ],
    "requirements": {"required": ["코딩 도구로 배포 경험"], "preferred": []},
    "background": {"facts": [], "inferences": []},
    "core_competencies": [
        {"name": "요청 뒤의 목적", "explanation": "..."},
        {"name": "크게 맡기고 확인합니다", "explanation": "..."},
        {"name": "끈기", "explanation": "..."},
    ],
    "cover_letter_tips": ["..."],
}


def test_good_analysis_passes():
    r = check(GOOD, JD)
    assert r["ok"], r["errors"]


def test_altered_quote_fails():
    bad = copy.deepcopy(GOOD)
    bad["core_tasks"][0]["quote"] = "흩어진 요청을 읽고 LLM 기반 솔루션을 설계합니다"
    r = check(bad, JD)
    assert not r["ok"]
    assert any("core_tasks[0]" in e for e in r["errors"])


def test_one_character_change_fails():
    bad = copy.deepcopy(GOOD)
    bad["core_tasks"][1]["quote"] = "목표와 완료 조건, 검증 방법을 먼저 정하고 결과를 확인한다."
    assert not check(bad, JD)["ok"]


def test_requires_exactly_three_core_tasks():
    bad = copy.deepcopy(GOOD)
    bad["core_tasks"] = bad["core_tasks"][:2]
    r = check(bad, JD)
    assert not r["ok"]
    assert any("3" in e for e in r["errors"])


def test_duplicate_quotes_fail():
    bad = copy.deepcopy(GOOD)
    bad["core_tasks"][2]["quote"] = bad["core_tasks"][0]["quote"]
    assert not check(bad, JD)["ok"]


def test_too_short_quote_fails():
    bad = copy.deepcopy(GOOD)
    bad["core_tasks"][2]["quote"] = "시안"
    assert not check(bad, JD)["ok"]


def test_missing_section_fails():
    bad = copy.deepcopy(GOOD)
    del bad["background"]
    r = check(bad, JD)
    assert not r["ok"]
    assert any("background" in e for e in r["errors"])


def test_competency_name_must_come_from_jd():
    bad = copy.deepcopy(GOOD)
    bad["core_competencies"][2]["name"] = "리더십"
    assert not check(bad, JD)["ok"]


@pytest.mark.parametrize("a,b", [
    ("목표와  완료 조건", "목표와\n완료 조건"),
    ("“인용”", '"인용"'),
    ("• 고객사의", "고객사의"),
])
def test_normalize_equivalences(a, b):
    assert normalize(a) == normalize(b)
