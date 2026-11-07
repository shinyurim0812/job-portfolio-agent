"""figma_templates: Figma get_metadata XML의 예시 프레임 → 배치 템플릿 spec (Figma 재호출 없이)."""
import json
import sys
from pathlib import Path

from figma_templates import frame_to_slide, convert

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "figma" / "scripts"))
import build_plugin  # noqa: E402

XML = """<canvas id="0:1" name="Page 1" x="0" y="0" width="0" height="0">
  <frame id="1:1" name="5_Background_1" x="5000" y="200" width="1920" height="1080">
    <text id="1:2" name="Section Title" x="898" y="50" width="125" height="26" />
    <rounded-rectangle id="1:3" name="Rectangle 1" x="0" y="479" width="1920" height="636" />
    <rounded-rectangle id="1:4" name="Offcanvas" x="1920" y="0" width="1923" height="1100" />
    <ellipse id="1:5" name="Ellipse 643" x="198" y="641" width="623" height="271" />
    <vector id="1:6" name="Vector 14186" x="891" y="752" width="138" height="1" />
    <text id="1:7" name="가나다라마바사아자차카타파하 가나다라마바사아자차카타파하" x="532" y="281" width="400" height="132" />
    <frame id="1:8" name="Action" x="110" y="420" width="850" height="431">
      <text id="1:9" name="Label" x="110" y="420" width="850" height="39" />
    </frame>
  </frame>
</canvas>"""


def frame(tmp_path):
    p = tmp_path / "meta.xml"
    p.write_text(XML, encoding="utf-8")
    return p


def slide(tmp_path):
    import xml.etree.ElementTree as ET
    root = ET.fromstring("<wrap>" + XML + "</wrap>")
    f = next(e for e in root.iter() if e.get("id") == "1:1")
    return frame_to_slide(f, "ex-background")


def by_name(s, name):
    return next(e for e in s["elements"] if e["name"].endswith(name))


def test_frame_relative_positions_and_types(tmp_path):
    s = slide(tmp_path)
    assert by_name(s, "Section Title")["x"] == 898
    assert by_name(s, "Rectangle 1")["type"] == "rect"
    assert by_name(s, "Ellipse 643")["type"] == "ellipse"
    line = by_name(s, "Vector 14186")
    assert line["type"] == "line" and line["w"] == 138 and line["h"] == 0


def test_offcanvas_nodes_dropped_and_partial_clamped(tmp_path):
    s = slide(tmp_path)
    assert not [e for e in s["elements"] if "Offcanvas" in e["name"]]
    band = by_name(s, "Rectangle 1")
    assert band["y"] + band["h"] <= 1080


def test_group_children_use_frame_coordinates(tmp_path):
    """자식 좌표가 부모 상자 안에 있으면 프레임 기준 좌표로 본다(실제 메타데이터 형태)."""
    assert (by_name(slide(tmp_path), "Label")["x"], by_name(slide(tmp_path), "Label")["y"]) == (110, 420)


def test_text_size_is_estimated_and_marked(tmp_path):
    t = by_name(slide(tmp_path), "가나다라마바사아자차카타파하 가나다라마바사아자차카타파하")
    assert t["text"].startswith("가나다")
    assert 25 <= t["size"] <= 50  # 두 줄 이상으로 추정
    assert "추정" in t["note"]


def test_converted_template_builds(tmp_path):
    out = tmp_path / "templates"
    convert(frame(tmp_path), {"1:1": "ex-background"}, out)
    spec = json.loads((out / "ex-background.json").read_text(encoding="utf-8"))
    assert spec["slides"][0]["base"] == "figma#1:1"
    font = Path("C:/Windows/Fonts/NotoSansKR-VF.ttf")
    if font.exists():
        build_plugin.build(out / "ex-background.json", tmp_path / "b", "t", str(font))
