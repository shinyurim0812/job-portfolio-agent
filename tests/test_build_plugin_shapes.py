"""빌더 확장: Ellipse, Line 화살표(Line 2개로 만든 화살촉), 모든 방향의 선, Vector 미사용.

사용자 ZIP 규칙: 텍스트는 Text, 도형은 Rectangle·Ellipse·Line, 화살표도 Line 등 기본 요소로,
Vector/SVG Path 금지, 이미지는 Rectangle + 이미지 채우기.
"""
import importlib.util
import json
import math
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "figma" / "scripts" / "build_plugin.py"
RUNTIME = ROOT / "tools" / "figma" / "assets" / "figma-runtime.js"
FONT = Path("C:/Windows/Fonts/malgun.ttf")

spec_mod = importlib.util.spec_from_file_location("build_plugin", BUILDER)
bp = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(bp)


def write_spec(tmp_path, elements, w=1920, h=1080):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps({"width": w, "height": h, "slides": [{"name": "s", "elements": elements}]},
                            ensure_ascii=False), encoding="utf-8")
    return p


def test_ellipse_is_accepted(tmp_path):
    data = bp.load_spec(write_spec(tmp_path, [
        {"type": "ellipse", "name": "Deco/Dot", "x": 100, "y": 100, "w": 40, "h": 40, "fill": "#142B57"}]))
    assert data["slides"][0]["elements"][0]["type"] == "ellipse"


def test_line_can_point_left_or_up(tmp_path):
    data = bp.load_spec(write_spec(tmp_path, [
        {"type": "line", "name": "Flow/Back", "x": 500, "y": 500, "w": -200, "h": -100, "stroke": "#252B33"}]))
    assert len(data["slides"][0]["elements"]) == 1


def test_line_endpoint_outside_canvas_fails(tmp_path):
    with pytest.raises(ValueError, match="outside canvas"):
        bp.load_spec(write_spec(tmp_path, [
            {"type": "line", "name": "Flow/Out", "x": 100, "y": 100, "w": -200, "h": 0, "stroke": "#252B33"}]))


def test_arrow_end_adds_two_head_lines_meeting_at_tip(tmp_path):
    data = bp.load_spec(write_spec(tmp_path, [
        {"type": "line", "name": "Flow/Step", "x": 100, "y": 200, "w": 300, "h": 0, "stroke": "#252B33", "arrow": "end"}]))
    els = data["slides"][0]["elements"]
    heads = [e for e in els if e["name"].startswith("Flow/ArrowHead")]
    assert len(els) == 3 and len(heads) == 2
    tip = (400, 200)
    for hd in heads:
        assert (hd["x"], hd["y"]) == tip
        # 화살촉은 선의 진행 방향 반대쪽(왼쪽)으로 뻗는다
        assert hd["w"] < 0
        assert all(hd[k] == els[0][k] for k in ("stroke",))


def test_arrow_both_adds_four_heads(tmp_path):
    data = bp.load_spec(write_spec(tmp_path, [
        {"type": "line", "name": "Flow/Two", "x": 100, "y": 200, "w": 0, "h": 300, "stroke": "#252B33", "arrow": "both"}]))
    assert len([e for e in data["slides"][0]["elements"] if "ArrowHead" in e["name"]]) == 4


def test_invalid_arrow_value_fails(tmp_path):
    with pytest.raises(ValueError, match="arrow"):
        bp.load_spec(write_spec(tmp_path, [
            {"type": "line", "name": "Flow/X", "x": 100, "y": 200, "w": 300, "h": 0, "stroke": "#252B33", "arrow": "middle"}]))


def test_rect_radius_all_corners(tmp_path):
    data = bp.load_spec(write_spec(tmp_path, [
        {"type": "rect", "name": "Card/A", "x": 100, "y": 100, "w": 400, "h": 300, "fill": "#FFFFFF", "radius": 16}]))
    assert data["slides"][0]["elements"][0]["radius"] == 16


def test_rect_radius_too_large_fails(tmp_path):
    with pytest.raises(ValueError, match="radius"):
        bp.load_spec(write_spec(tmp_path, [
            {"type": "rect", "name": "Card/A", "x": 100, "y": 100, "w": 40, "h": 30, "fill": "#FFFFFF", "radius": 20}]))


def test_dashed_stroke_accepted_and_validated(tmp_path):
    data = bp.load_spec(write_spec(tmp_path, [
        {"type": "ellipse", "name": "Bg/Ring", "x": 100, "y": 100, "w": 600, "h": 260, "stroke": "#FFFFFF", "dash": [6, 6]}]))
    assert data["slides"][0]["elements"][0]["dash"] == [6, 6]
    with pytest.raises(ValueError, match="dash"):
        bp.load_spec(write_spec(tmp_path, [
            {"type": "ellipse", "name": "Bg/Ring", "x": 100, "y": 100, "w": 600, "h": 260, "stroke": "#FFFFFF", "dash": [0]}]))


def test_runtime_applies_radius_and_dash():
    js = RUNTIME.read_text(encoding="utf-8")
    assert "cornerRadius" in js and "dashPattern" in js


def test_runtime_uses_only_native_nodes():
    js = RUNTIME.read_text(encoding="utf-8")
    for forbidden in ("createVector", "vectorPaths", "vectorNetwork", "createNodeFromSvg", "flatten("):
        assert forbidden not in js, forbidden
    assert "createEllipse" in js


def test_runtime_line_rotation_sign_matches_screen_coordinates():
    # Figma 문서: rotation = Math.atan2(-m10, m00). 화면 좌표(y 아래)에서 아래로 향하는 선은 음수 회전.
    js = RUNTIME.read_text(encoding="utf-8")
    assert "-Math.atan2(e.h,e.w)" in js


@pytest.mark.skipif(not FONT.exists(), reason="Korean font not available")
def test_full_build_1920_with_shapes(tmp_path):
    s = write_spec(tmp_path, [
        {"type": "text", "name": "Header/Title", "text": "구조도", "x": 80, "y": 60, "w": 800, "h": 80,
         "size": 48, "lh": 64, "bold": True, "color": "#252B33"},
        {"type": "rect", "name": "Flow/BoxA", "x": 80, "y": 300, "w": 300, "h": 120, "fill": "#F5F7FA", "stroke": "#DAE1EB"},
        {"type": "ellipse", "name": "Flow/Dot", "x": 420, "y": 340, "w": 40, "h": 40, "fill": "#142B57"},
        {"type": "line", "name": "Flow/Arrow", "x": 480, "y": 360, "w": 300, "h": 0, "stroke": "#252B33", "arrow": "end"},
    ])
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(BUILDER), "--spec", str(s), "--out", str(out), "--font", str(FONT)],
                       capture_output=True)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    with zipfile.ZipFile(out / "portfolio-plugin.zip") as z:
        names = set(z.namelist())
        code = z.read("code.js").decode("utf-8")
    assert not any(n.endswith((".png", ".pdf")) for n in names)
    assert '"width": 1920' in code or '"width":1920' in code
