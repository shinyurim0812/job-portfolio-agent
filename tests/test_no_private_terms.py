"""지원 회사 이름·실명이 커밋 파일과 커밋 메시지에 들어가지 않았는지 검사.

이름 목록은 data/private_terms.json(git 제외)에만 있다. 목록이 없는 환경(저장소를 받은 다른 사람)에서는 건너뛴다.
"""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TERMS_FILE = ROOT / "data" / "private_terms.json"


def find_terms(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    return [t for t in terms if t.lower() in low]


def load_terms():
    if not TERMS_FILE.exists():
        pytest.skip("data/private_terms.json 없음")
    return json.loads(TERMS_FILE.read_text(encoding="utf-8"))["terms"]


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True).stdout.decode("utf-8", "replace")


def test_find_terms_catches_planted_name():
    # 가상의 회사 이름으로 시험한다(실제 이름을 넣으면 이 파일이 검사에 걸린다)
    assert find_terms("docs: Acmecorp 공고 실행", ["acmecorp"]) == ["acmecorp"]
    assert find_terms("docs: 실제 채용공고 실행", ["acmecorp"]) == []


def test_tracked_files_have_no_private_terms():
    terms = load_terms()
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
        found = find_terms(text, terms) + find_terms(rel, terms)
        if found:
            hits[rel] = found
    assert not hits, f"커밋 대상 파일에 비공개 이름: {hits}"


def test_commit_messages_have_no_private_terms():
    terms = load_terms()
    hits = find_terms(git("log", "--format=%B"), terms)
    assert not hits, f"커밋 메시지에 비공개 이름: {hits}"
