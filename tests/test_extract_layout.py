"""extract_layout: 기존 포트폴리오 PDF 한 쪽 → 빌더 spec(좌표·글자 크기·색·도형·이미지)."""
import io
import json
import sys
from pathlib import Path

import pytest

pymupdf = pytest.importorskip("pymupdf")
from PIL import Image

from extract_layout import extract_page, extract

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "figma" / "scripts"))
import build_plugin  # noqa: E402

KFONT = Path("C:/Windows/Fonts/malgun.ttf")


def make_pdf(path, with_image=False):
    doc = pymupdf.open()
    page = doc.new_page(width=1920, height=1080)
    page.draw_rect(pymupdf.Rect(0, 875, 1920, 1080), color=None, fill=(0.95, 0.95, 0.95))
    page.draw_rect(pymupdf.Rect(0, 0, 109, 106), color=None, fill=(0.078, 0.169, 0.341))
    page.draw_line((96, 500), (900, 500), color=(0.9, 0.9, 0.9), width=2)
    page.insert_text((96, 180), "Title line", fontsize=56, color=(0.145, 0.145, 0.16))
    page.insert_text((96, 400), "first row", fontsize=30, color=(0.37, 0.37, 0.37))
    page.insert_text((96, 442), "second row", fontsize=30, color=(0.37, 0.37, 0.37))
    if with_image:
        buf = io.BytesIO()
        Image.new("RGB", (40, 20), (200, 30, 30)).save(buf, format="PNG")
        page.insert_image(pymupdf.Rect(1200, 300, 1600, 500), stream=buf.getvalue())
    doc.save(path)


def els(slide, kind):
    return [e for e in slide["elements"] if e["type"] == kind]


def test_text_position_size_color(tmp_path):
    make_pdf(tmp_path / "a.pdf")
    slide = extract_page(pymupdf.open(tmp_path / "a.pdf")[0], tmp_path / "assets", "p01")
    title = next(e for e in els(slide, "text") if e["text"] == "Title line")
    assert title["size"] == 56
    assert title["color"] == "#252529"
    assert abs(title["x"] - 96) <= 2


def test_lines_in_one_block_merge_with_line_height(tmp_path):
    make_pdf(tmp_path / "a.pdf")
    slide = extract_page(pymupdf.open(tmp_path / "a.pdf")[0], tmp_path / "assets", "p01")
    body = next(e for e in els(slide, "text") if "first row" in e["text"])
    assert body["text"] == "first row\nsecond row"
    assert body["lh"] == 42


def test_filled_shapes_become_rects_and_lines(tmp_path):
    make_pdf(tmp_path / "a.pdf")
    slide = extract_page(pymupdf.open(tmp_path / "a.pdf")[0], tmp_path / "assets", "p01")
    fills = {e["fill"] for e in els(slide, "rect")}
    assert "#F2F2F2" in fills and "#142B57" in fills
    line = els(slide, "line")[0]
    assert line["w"] == pytest.approx(804, abs=2) and line["h"] == pytest.approx(0, abs=1)


def test_glyph_shapes_give_text_color_not_rects(tmp_path):
    """Figma PDF는 글자를 도형으로 칠한다: 글자 영역 안의 칠은 도형이 아니라 글자 색이다."""
    doc = pymupdf.open()
    page = doc.new_page(width=1920, height=1080)
    page.insert_text((96, 180), "Glyph text", fontsize=56, color=(0, 0, 0))
    page.draw_rect(pymupdf.Rect(98, 140, 300, 185), color=None, fill=(0.078, 0.169, 0.341))
    doc.save(tmp_path / "g.pdf")
    slide = extract_page(pymupdf.open(tmp_path / "g.pdf")[0], tmp_path / "assets", "p01")
    assert els(slide, "text")[0]["color"] == "#142B57"
    assert not [e for e in els(slide, "rect") if e.get("fill") == "#142B57"]


def test_one_glyph_shape_spanning_two_lines(tmp_path):
    """Figma는 두 줄 문단의 글자를 도형 하나로 칠한다: 상자로 뽑히면 안 된다(원본 13쪽 제목)."""
    doc = pymupdf.open()
    page = doc.new_page(width=1920, height=1080)
    page.insert_text((96, 320), "first line", fontsize=62, color=(0, 0, 0))
    page.insert_text((96, 410), "second line", fontsize=62, color=(0, 0, 0))
    page.draw_rect(pymupdf.Rect(98, 280, 400, 418), color=None, fill=(0.133, 0.133, 0.149))
    doc.save(tmp_path / "two.pdf")
    slide = extract_page(pymupdf.open(tmp_path / "two.pdf")[0], tmp_path / "assets", "p01")
    assert not els(slide, "rect")
    assert {e["color"] for e in els(slide, "text")} == {"#222226"}


def test_glyph_shape_including_list_bullets(tmp_path):
    """목록 글머리표까지 한 도형으로 칠해 글자 줄보다 왼쪽이 넓은 경우(원본 9쪽 '개인 기여')."""
    doc = pymupdf.open()
    page = doc.new_page(width=1920, height=1080)
    page.insert_text((133, 430), "Express API", fontsize=32, color=(0, 0, 0))
    page.insert_text((144, 476), "voice input", fontsize=32, color=(0, 0, 0))
    page.draw_rect(pymupdf.Rect(115, 409, 300, 484), color=None, fill=(0.15, 0.15, 0.16))
    doc.save(tmp_path / "b.pdf")
    slide = extract_page(pymupdf.open(tmp_path / "b.pdf")[0], tmp_path / "assets", "p01")
    assert not els(slide, "rect")


def test_highlight_box_behind_text_stays_a_rect(tmp_path):
    """글자 뒤 강조 상자(먼저 그림)는 상자로 남고, 그 위 글자 칠(나중에 그림)이 글자 색이 된다."""
    doc = pymupdf.open()
    page = doc.new_page(width=1920, height=1080)
    page.insert_text((600, 985), "highlight", fontsize=32, color=(0, 0, 0))
    page.draw_rect(pymupdf.Rect(597, 955, 790, 992), color=None, fill=(0.122, 0.137, 0.169))
    page.draw_rect(pymupdf.Rect(601, 962, 715, 990), color=None, fill=(1, 1, 1))  # 글자에 맞는 칠
    doc.save(tmp_path / "hl.pdf")
    slide = extract_page(pymupdf.open(tmp_path / "hl.pdf")[0], tmp_path / "assets", "p01")
    assert [e["fill"] for e in els(slide, "rect")] == ["#1F232B"]
    assert els(slide, "text")[0]["color"] == "#FFFFFF"


def test_mixed_sizes_on_one_line_split(tmp_path):
    """큰 숫자 + 작은 단위처럼 한 줄에 크기가 섞이면 따로 뽑는다(실제 포폴 결과 상자)."""
    doc = pymupdf.open()
    page = doc.new_page(width=1920, height=1080)
    tw = pymupdf.TextWriter(page.rect)
    font = pymupdf.Font("helv")
    tw.append((1179, 690), "247", font=font, fontsize=70)
    tw.append(tw.last_point, " codes", font=font, fontsize=36)
    tw.write_text(page)
    doc.save(tmp_path / "m.pdf")
    slide = extract_page(pymupdf.open(tmp_path / "m.pdf")[0], tmp_path / "assets", "p01")
    sizes = {e["text"]: e["size"] for e in els(slide, "text")}
    assert sizes == {"247": 70, "codes": 36}


def test_translucent_fill_is_blended_on_white(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=1920, height=1080)
    page.draw_rect(pymupdf.Rect(0, 875, 1920, 1080), color=None, fill=(0.098, 0.098, 0.098), fill_opacity=0.05)
    doc.save(tmp_path / "t.pdf")
    slide = extract_page(pymupdf.open(tmp_path / "t.pdf")[0], tmp_path / "assets", "p01")
    assert els(slide, "rect")[0]["fill"] in ("#F3F3F3", "#F4F4F4")  # 반올림 차이 허용


def test_images_are_saved_as_assets(tmp_path):
    make_pdf(tmp_path / "a.pdf", with_image=True)
    slide = extract_page(pymupdf.open(tmp_path / "a.pdf")[0], tmp_path / "assets", "p01")
    img = els(slide, "image")[0]
    assert (tmp_path / "assets" / slide["_assets"][img["key"]]).exists()
    assert abs(img["x"] - 1200) <= 2 and abs(img["w"] - 400) <= 2


@pytest.mark.skipif(not KFONT.exists(), reason="Korean font missing")
def test_extracted_spec_builds_and_renders_original(tmp_path):
    make_pdf(tmp_path / "a.pdf", with_image=True)
    out = tmp_path / "layouts"
    extract(tmp_path / "a.pdf", [1], out)
    spec = json.loads((out / "p01.json").read_text(encoding="utf-8"))
    assert spec["width"] == 1920 and spec["slides"][0]["base"] == "a.pdf#p01"
    assert (out / "p01.png").exists()  # 원본 페이지 그림(디자이너·검토자가 비교용으로 연다)
    build_plugin.build(out / "p01.json", tmp_path / "build", "t", str(KFONT))
    assert (tmp_path / "build" / "portfolio-plugin.zip").exists()
