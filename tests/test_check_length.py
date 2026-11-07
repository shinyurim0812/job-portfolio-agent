"""check_length: 문항별 글자 수 제한."""
from check_length import count, check

Q = {"count_rule": {"mode": "with_spaces", "newline_chars": 1},
     "questions": [{"id": "q1", "limit": 10}, {"id": "q2", "limit": 5}]}


def test_count_with_spaces():
    assert count("가 나\n다", "with_spaces", 1) == 5


def test_count_newline_as_two():
    assert count("가\n나", "with_spaces", 2) == 4


def test_count_without_spaces():
    assert count("가 나\n다", "without_spaces", 1) == 3


def test_within_limit_passes():
    r = check({"answers": [{"id": "q1", "text": "열 글자 이내"}, {"id": "q2", "text": "짧다"}]}, Q)
    assert r["ok"], r


def test_over_limit_fails():
    r = check({"answers": [{"id": "q1", "text": "가" * 11}, {"id": "q2", "text": "짧다"}]}, Q)
    assert not r["ok"]
    assert r["results"][0]["over_by"] == 1


def test_missing_answer_fails():
    r = check({"answers": [{"id": "q1", "text": "답"}]}, Q)
    assert not r["ok"]
