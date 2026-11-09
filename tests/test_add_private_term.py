"""공고의 회사 이름을 비공개 목록에 자동으로 넣는 도구."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "add_private_term.py"


def run(terms_file, *names):
    return subprocess.run([sys.executable, str(SCRIPT), *names, "--terms", str(terms_file)], capture_output=True)


def test_adds_new_names_and_keeps_existing(tmp_path):
    f = tmp_path / "t.json"
    f.write_text(json.dumps({"terms": ["acmecorp"], "allow": ["x"]}), encoding="utf-8")
    assert run(f, "Betacorp", "베타코프").returncode == 0
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["terms"] == ["acmecorp", "Betacorp", "베타코프"]
    assert data["allow"] == ["x"]


def test_skips_duplicates_ignoring_case_and_spaces(tmp_path):
    f = tmp_path / "t.json"
    f.write_text(json.dumps({"terms": ["Acmecorp"]}), encoding="utf-8")
    run(f, "acmecorp", " ACMECORP ", "")
    assert json.loads(f.read_text(encoding="utf-8"))["terms"] == ["Acmecorp"]


def test_creates_file_when_missing(tmp_path):
    f = tmp_path / "new.json"
    assert run(f, "Acmecorp").returncode == 0
    assert json.loads(f.read_text(encoding="utf-8")) == {"terms": ["Acmecorp"], "allow": []}
