"""지원 회사 이름·실명이 커밋 파일과 커밋 메시지에 들어가지 않았는지 검사.

이름 목록은 data/private_terms.json(git 제외)에만 있다. 목록이 없는 환경(저장소를 받은 다른 사람)에서는 건너뛴다.
"""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TERMS_FILE = ROOT / "data" / "private_terms.json"


def find_terms(text: str, terms: list[str], allow: list[str] = ()) -> list[str]:
    """allow: 이름을 포함하지만 이름이 아닌 일반 단어(예: '슬라이드'). 먼저 지우고 검사한다."""
    low = text.lower()
    for word in allow:
        low = low.replace(word.lower(), " ")
    return [t for t in terms if t.lower() in low]


def load_terms():
    if not TERMS_FILE.exists():
        pytest.skip("data/private_terms.json 없음")
    data = json.loads(TERMS_FILE.read_text(encoding="utf-8"))
    return data["terms"], data.get("allow", [])


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True).stdout.decode("utf-8", "replace")


def test_find_terms_catches_planted_name():
    # 가상의 회사 이름으로 시험한다(실제 이름을 넣으면 이 파일이 검사에 걸린다)
    assert find_terms("docs: Acmecorp 공고 실행", ["acmecorp"]) == ["acmecorp"]
    assert find_terms("docs: 실제 채용공고 실행", ["acmecorp"]) == []


def test_allowed_common_word_is_not_a_hit():
    # 실제로 겪은 거짓 실패(일반 단어 안에 짧은 회사 이름이 들어 있는 경우)를 가상의 이름 '나크'로 재현
    assert find_terms("모나크 전체를 벡터로", ["나크"], allow=["모나크"]) == []
    assert find_terms("나크 포트폴리오", ["나크"], allow=["모나크"]) == ["나크"]


def test_tracked_files_have_no_private_terms():
    terms, allow = load_terms()
    hits = {}
    # 추적 중인 파일 + 아직 추적 전이지만 커밋될 수 있는 새 파일(.gitignore 제외 대상은 뺌)
    candidates = git("ls-files").splitlines() + git("ls-files", "--others", "--exclude-standard").splitlines()
    for rel in candidates:
        path = ROOT / rel
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        found = find_terms(text, terms, allow) + find_terms(rel, terms, allow)
        if found:
            hits[rel] = found
    assert not hits, f"커밋 대상 파일에 비공개 이름: {hits}"


def test_commit_messages_have_no_private_terms():
    terms, allow = load_terms()
    hits = find_terms(git("log", "--format=%B"), terms, allow)
    assert not hits, f"커밋 메시지에 비공개 이름: {hits}"
