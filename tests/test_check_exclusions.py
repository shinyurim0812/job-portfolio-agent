"""check_exclusions: 제외 경험(페이지 ID 또는 키워드)이 결과물에 섞였는지."""
from check_exclusions import scan

EXCL = {"page_ids": ["35a90cad-ee72-825a-bfed-074bb10c8c37"], "keywords": ["의도 분류", "Night intent"]}


def test_clean_text_passes():
    assert scan("RAG 챗봇을 배포하고 응답 지연을 줄였다.", EXCL) == []


def test_keyword_hit_case_insensitive():
    hits = scan("시뮬레이션에서 night INTENT 라벨을 정리", EXCL)
    assert len(hits) == 1
    assert hits[0]["match"].lower() == "night intent"


def test_keyword_hit_reports_line():
    hits = scan("첫 줄\n둘째 줄에 의도 분류 포함", EXCL)
    assert hits[0]["line"] == 2


def test_page_id_hit_with_or_without_dashes():
    assert scan("source: 35a90cadee72825abfed074bb10c8c37", EXCL)
    assert scan("source: 35a90cad-ee72-825a-bfed-074bb10c8c37", EXCL)
