"""check_numbers: 초안·spec에 나온 수치가 원천 자료에 있는지."""
from check_numbers import extract_numbers, unsupported, texts_from_spec

SOURCE = "응답 시간을 3.2초에서 1.1초로 줄였다. 사용자 120명이 사용. 정확도 87%. 기간 2025.07~2025.08. 1,200건 처리"


def test_extracts_number_with_unit():
    nums = [n["token"] for n in extract_numbers("정확도 87% 달성, 120명 대상")]
    assert "87%" in nums and "120명" in nums


def test_supported_numbers_pass():
    draft = "사용자 120명에게 배포해 정확도 87%를 확인했고 응답을 1.1초로 줄였다."
    assert unsupported(draft, SOURCE) == []


def test_invented_number_is_flagged():
    draft = "정확도를 95%까지 올렸다."
    bad = unsupported(draft, SOURCE)
    assert [b["token"] for b in bad] == ["95%"]


def test_same_digits_different_unit_is_flagged():
    # 소스에는 120명만 있음. 120건은 다른 사실
    assert [b["token"] for b in unsupported("120건을 처리했다", SOURCE)] == ["120건"]


def test_comma_numbers_match():
    assert unsupported("1200건 처리", SOURCE) == []
    assert unsupported("1,200건 처리", SOURCE) == []


def test_list_markers_and_question_ids_ignored():
    draft = "1. 첫째\n2) 둘째\n## 3. 제목"
    assert unsupported(draft, SOURCE) == []


def test_figma_pdf_spaced_digits_in_source():
    # Figma에서 내보낸 PDF를 pypdf로 추출하면 숫자 사이에 공백이 들어간다 (실제 자료에서 발견)
    source = "2 0 2 6 . 0 1 . 0 2 ~ 2 0 2 6 . 0 2 . 2 8 인턴, AI ROOKIE 본선 (40/721팀)"
    assert unsupported("2026.01.02부터 인턴", source) == []
    assert unsupported("721팀 중 본선", source) == []


def test_spec_only_text_fields_checked():
    spec = {"width": 1600, "slides": [{"name": "p1", "elements": [
        {"type": "text", "text": "정확도 87%", "x": 72, "y": 999, "size": 48},
        {"type": "rect", "x": 10, "y": 20},
    ]}]}
    texts = texts_from_spec(spec)
    assert texts == ["정확도 87%"]
