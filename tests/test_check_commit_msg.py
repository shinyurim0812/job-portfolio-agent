"""커밋 메시지 검사기: 커밋이 만들어지기 전에(commit-msg 훅) 비공개 이름을 막는다."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "check_commit_msg.py"


def run(tmp_path, message, terms=("acmecorp",), allow=()):
    terms_file = tmp_path / "terms.json"
    terms_file.write_text(json.dumps({"terms": list(terms), "allow": list(allow)}), encoding="utf-8")
    msg = tmp_path / "MSG"
    msg.write_text(message, encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), str(msg), "--terms", str(terms_file)], capture_output=True)


def test_blocks_message_with_private_term(tmp_path):
    r = run(tmp_path, "feat: Acmecorp 공고 반영")
    assert r.returncode == 1


def test_passes_clean_message(tmp_path):
    assert run(tmp_path, "feat: 공고 반영").returncode == 0


def test_allow_word_is_not_a_hit(tmp_path):
    assert run(tmp_path, "모나크 정리", terms=("나크",), allow=("모나크",)).returncode == 0


def test_missing_terms_file_passes(tmp_path):
    msg = tmp_path / "MSG"
    msg.write_text("feat: x", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(msg), "--terms", str(tmp_path / "none.json")])
    assert r.returncode == 0
