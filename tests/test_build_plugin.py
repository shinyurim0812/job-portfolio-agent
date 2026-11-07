"""Smoke test: the copied builder actually produces a ZIP from a sample spec.

Guards the path issue found in plan review (build_plugin.py resolves assets via parents[1]).
"""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "figma" / "scripts" / "build_plugin.py"
FONT = Path("C:/Windows/Fonts/malgun.ttf")

pytestmark = pytest.mark.skipif(not FONT.exists(), reason="Korean font not available")


def spec(text, w=1456):
    return {"width": 1600, "height": 900, "slides": [{"name": "샘플", "elements": [
        {"type": "text", "name": "Header/Title", "text": text, "x": 72, "y": 72, "w": w, "h": 100,
         "size": 48, "lh": 64, "bold": True, "color": "#252B33"},
        {"type": "line", "name": "Footer/Divider", "x": 72, "y": 800, "w": 1456, "h": 0, "stroke": "#DAE1EB"},
    ]}]}


def build(tmp_path, data):
    s = tmp_path / "spec.json"
    s.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "출력 폴더"
    r = subprocess.run([sys.executable, str(BUILDER), "--spec", str(s), "--out", str(out),
                        "--name", "테스트", "--font", str(FONT)], capture_output=True)
    return r, out


def test_builds_zip_and_previews(tmp_path):
    r, out = build(tmp_path, spec("한국어 제목 테스트"))
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    with zipfile.ZipFile(out / "portfolio-plugin.zip") as z:
        assert set(z.namelist()) == {"manifest.json", "code.js", "ui.html", "README.md"}
    assert (out / "preview" / "01.png").exists()
    v = json.loads((out / "validation.json").read_text(encoding="utf-8"))
    assert v["text_bounds"] == "passed" and v["actual_figma_execution"] == "not_tested"


def test_overflowing_text_fails(tmp_path):
    r, out = build(tmp_path, spec("아주 긴 제목이 좁은 영역을 넘칩니다", w=120))
    assert r.returncode != 0
    assert "exceeds width" in r.stderr.decode("utf-8", "replace")
    assert not out.exists()
