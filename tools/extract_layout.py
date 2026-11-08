"""Extract one portfolio PDF page into a builder spec (positions, sizes, colors, shapes, images).

The designer starts a "modified" page from this spec instead of inventing a layout,
and the reviewer compares the result with the rendered original (pNN.png).

Figma PDF exports draw glyphs as filled paths (Type3 fonts report black text), so a
filled path lying inside a text line is treated as that text's color, not as a shape.

Usage: python tools/extract_layout.py PORTFOLIO.pdf --pages 10 13 --out data/design/layouts/<row>
Writes pNN.json (one-slide spec, "base" = "<pdf name>#pNN"), pNN.png (original page), assets/.
"""
import argparse
import io
import json
import sys
from pathlib import Path

import pymupdf
from PIL import Image

W = 1920
LS = " "
# ink pixels / (text width x size x rows). Calibrated on the real portfolio: regular text
# measured 0.13-0.22, bold 0.22-0.33 (symbols like arrows are unreliable).
BOLD_DENSITY = 0.22


def ink_density(shot, box, color, height) -> float:
    """Share of the text box covered by pixels close to the text color."""
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(shot.width, max(x1, x0 + 1)), min(shot.height, max(y1, y0 + 1))
    target = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    region = shot.crop((x0, y0, x1, y1))
    ink = sum(1 for p in region.getdata() if sum(abs(p[i] - target[i]) for i in range(3)) < 120)
    return ink / max(1, (x1 - x0) * height)


def hexcolor(rgb, alpha=1.0):
    vals = [round((c * alpha + (1 - alpha)) * 255) for c in rgb[:3]]
    return "#" + "".join(f"{max(0, min(255, v)):02X}" for v in vals)


def _inside(inner, outer, tx, ty=None):
    ty = tx if ty is None else ty
    return (inner.x0 >= outer.x0 - tx and inner.y0 >= outer.y0 - ty
            and inner.x1 <= outer.x1 + tx and inner.y1 <= outer.y1 + ty)


def _lines(page):
    """Text lines as lists of chars with bbox, origin, size and reported color."""
    out = []
    for b in page.get_text("rawdict")["blocks"]:
        if b["type"] != 0:
            continue
        for ln in b["lines"]:
            chars = []
            for sp in ln["spans"]:
                for ch in sp["chars"]:
                    if ch["c"] in (LS, "\n"):
                        continue
                    chars.append({"c": ch["c"], "bbox": pymupdf.Rect(ch["bbox"]), "origin": ch["origin"],
                                  "size": sp["size"], "color": sp["color"]})
            if chars and "".join(c["c"] for c in chars).strip():
                out.append(chars)
    return out


def extract_page(page, assets_dir: Path, prefix: str) -> dict:
    s = W / page.rect.width
    H = round(page.rect.height * s)
    drawings = page.get_drawings()
    glyph = set()

    # 1. text: color each char by the topmost filled path that covers it and lies within
    #    the text lines it touches (one glyph path may span a whole multi-line paragraph)
    lines = _lines(page)
    boxes = []
    for chars in lines:
        lbox = pymupdf.Rect(chars[0]["bbox"])
        for c in chars:
            lbox |= c["bbox"]
        boxes.append((lbox, max(c["size"] for c in chars)))
    glyph_ok = {}
    for i, d in enumerate(drawings):
        if d.get("fill") is None:
            continue
        hit = [(b, sz) for b, sz in boxes if b.intersects(d["rect"])]
        if hit:
            union = pymupdf.Rect(hit[0][0])
            for b, _ in hit:
                union |= b
            sz = max(sz for _, sz in hit)
            # wider on the sides: list bullets are painted with the glyphs but are not text
            glyph_ok[i] = _inside(d["rect"], union, sz * 0.8, sz * 0.3)
    runs = []
    for chars, (lbox, size) in zip(lines, boxes):
        cands = [i for i, ok in glyph_ok.items() if ok and drawings[i]["rect"].intersects(lbox)]
        cur, line_runs = None, []
        for c in chars:
            cx, cy = (c["bbox"].x0 + c["bbox"].x1) / 2, (c["bbox"].y0 + c["bbox"].y1) / 2
            hit = [i for i in cands if drawings[i]["rect"].contains(pymupdf.Point(cx, cy))]
            if hit:
                i = hit[-1]
                col = hexcolor(drawings[i]["fill"], drawings[i].get("fill_opacity") or 1)
                # Figma sometimes paints the same glyphs twice: every same-color hit is glyph paint
                glyph.update(j for j in hit if hexcolor(drawings[j]["fill"], drawings[j].get("fill_opacity") or 1) == col)
            else:
                v = c["color"]
                col = f"#{v:06X}"
            if cur and cur["color"] == col and abs(cur["chars"][-1]["size"] - c["size"]) < 0.5:
                cur["chars"].append(c)
            else:
                cur = {"color": col, "chars": [c]}
                line_runs.append(cur)
        for r in line_runs:
            r["_single"] = len(line_runs) == 1  # only single-color lines merge into paragraphs
        runs.extend(line_runs)

    texts = []
    for r in runs:
        ch = r["chars"]
        size = max(c["size"] for c in ch)
        x0 = min(c["bbox"].x0 for c in ch)
        x1 = max(c["bbox"].x1 for c in ch)
        texts.append({"text": "".join(c["c"] for c in ch).strip(), "x0": x0, "x1": x1,
                      "top": min(c["bbox"].y0 for c in ch), "bottom": max(c["bbox"].y1 for c in ch),
                      "base": ch[0]["origin"][1],
                      "size": size, "color": r["color"], "single": r["_single"], "rows": 1, "lh": None})
    texts.sort(key=lambda t: (t["base"], t["x0"]))
    merged = []
    for t in texts:
        prev = next((m for m in reversed(merged) if m["single"] and t["single"]
                     and abs(m["x0"] - t["x0"]) <= 2 and abs(m["size"] - t["size"]) < 0.5
                     and m["color"] == t["color"]), None)
        gap = t["base"] - prev["last_base"] if prev else None
        if prev and 0 < gap <= prev["size"] * 2 and (prev["lh"] is None or abs(gap - prev["lh"]) <= 2):
            prev["text"] += "\n" + t["text"]
            prev["lh"] = gap
            prev["rows"] += 1
            prev["x1"] = max(prev["x1"], t["x1"])
            prev["bottom"] = t["bottom"]
            prev["last_base"] = t["base"]
        else:
            t["last_base"] = t["base"]
            merged.append(t)

    elements = []
    # 2. shapes (drawing order), skipping glyph paths
    shapes = []
    full = [i for i, d in enumerate(drawings)
            if d.get("fill") is not None and d["rect"].width >= page.rect.width - 1 and d["rect"].height >= page.rect.height - 1]
    for i, d in enumerate(drawings):
        if i in glyph or (i in full and i != full[-1]):
            continue
        r = d["rect"] & page.rect
        items = d["items"]
        if d.get("fill") is None and len(items) == 1 and items[0][0] == "l":
            p1, p2 = items[0][1], items[0][2]
            if abs(p1.x - p2.x) + abs(p1.y - p2.y) < 0.5:
                continue
            shapes.append({"type": "line", "x": p1.x * s, "y": p1.y * s, "w": (p2.x - p1.x) * s, "h": (p2.y - p1.y) * s,
                           "stroke": hexcolor(d.get("color") or (0, 0, 0), d.get("stroke_opacity") or 1),
                           "weight": max(0.5, round((d.get("width") or 1) * s, 1))})
            continue
        if r.is_empty or r.width < 0.5 or r.height < 0.5:
            continue
        e = {"type": "rect", "x": r.x0 * s, "y": r.y0 * s, "w": r.width * s, "h": r.height * s}
        if d.get("fill") is not None:
            e["fill"] = hexcolor(d["fill"], d.get("fill_opacity") or 1)
        if d.get("color") is not None and d.get("width"):
            e["stroke"] = hexcolor(d["color"], d.get("stroke_opacity") or 1)
            e["strokeWeight"] = max(0.5, round(d["width"] * s, 1))
        if "fill" not in e and "stroke" not in e:
            continue
        if any(it[0] == "c" for it in items):
            e["note"] = "곡선 포함: 둥근 모서리나 아이콘일 수 있음, 원본 그림으로 확인"
        if i == (full[-1] if full else None):
            e["note"] = "페이지 배경"
        shapes.append(e)
    # a white fill stacked exactly on another shape hides it in the export but adds nothing
    keep = []
    for e in shapes:
        if e.get("fill") == "#FFFFFF" and any(
                o is not e and o["type"] == "rect" and all(abs(o[k] - e[k]) <= 3 for k in "xywh") for o in shapes):
            continue
        keep.append(e)
    for n, e in enumerate(keep, 1):
        e["name"] = f"{'Line' if e['type'] == 'line' else 'Shape'}/{n:02d}"
        elements.append(e)

    # 3. images
    assets = {}
    assets_dir.mkdir(parents=True, exist_ok=True)
    clips = [d["scissor"] for d in page.get_drawings(extended=True) if d.get("type") == "clip"]
    for n, info in enumerate(page.get_image_info(xrefs=True), 1):
        xref = info.get("xref")
        full = pymupdf.Rect(info["bbox"])
        if not xref or (full & page.rect).is_empty:
            continue
        img = page.parent.extract_image(xref)
        data, ext = img["image"], img["ext"]
        # an image shown through a clip: keep only the visible part (the clip that overlaps it most)
        best = max(clips, key=lambda c: (full & c).get_area(), default=None)
        vis = full & best if best is not None and not (full & best).is_empty else pymupdf.Rect(full)
        vis &= page.rect
        if vis != full:
            with Image.open(io.BytesIO(data)) as src:
                fx, fy = src.width / full.width, src.height / full.height
                cut = src.crop((round((vis.x0 - full.x0) * fx), round((vis.y0 - full.y0) * fy),
                                round((vis.x1 - full.x0) * fx), round((vis.y1 - full.y0) * fy)))
                buf = io.BytesIO()
                cut.save(buf, format="PNG")
            data, ext = buf.getvalue(), "png"
        r = vis
        fname = f"{prefix}-img{n}.{ext}"
        (assets_dir / fname).write_bytes(data)
        key = f"{prefix}_img{n}"
        assets[key] = fname
        elements.append({"type": "image", "name": f"Image/{n:02d}", "key": key, "fit": "FILL",
                         "x": r.x0 * s, "y": r.y0 * s, "w": r.width * s, "h": r.height * s})

    # 4. text on top; weight is not in Type3 font names, so estimate it from ink density
    pix = page.get_pixmap(matrix=pymupdf.Matrix(s, s), alpha=False)
    shot = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    for n, t in enumerate(merged, 1):
        size = round(t["size"] * s)
        lh = round(t["lh"] * s) if t["lh"] else round(size * 1.4)
        h = t["rows"] * lh
        x = t["x0"] * s
        y = max(0, t["top"] * s - (lh - size) / 2)
        y = min(y, H - h)
        # room for font differences (preview uses the local Korean font, not the PDF's)
        w = min((t["x1"] - t["x0"]) * s * 1.2 + size * 0.5, W - x)
        dens = ink_density(shot, (t["x0"] * s, t["top"] * s, t["x1"] * s, t["bottom"] * s), t["color"], size * t["rows"])
        note = f"굵기는 잉크 밀도 {dens:.2f}로 추정(기준 {BOLD_DENSITY})"
        if abs(dens - BOLD_DENSITY) < 0.03:
            note += ": 경계값이라 원본 그림으로 확인"
        elements.append({"type": "text", "name": f"Text/{n:02d}", "text": t["text"], "x": x, "y": y, "w": w, "h": h,
                         "size": size, "lh": lh, "bold": dens >= BOLD_DENSITY, "color": t["color"], "align": "LEFT",
                         "note": note})

    for e in elements:
        for k in ("x", "y", "w", "h"):
            e[k] = round(e[k], 1)
    return {"name": prefix, "elements": elements, "_assets": assets}


def extract(pdf: Path, pages, out: Path) -> list:
    doc = pymupdf.open(pdf)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for pno in pages:
        page = doc[pno - 1]
        prefix = f"p{pno:02d}"
        slide = extract_page(page, out / "assets", prefix)
        assets = {k: {"path": f"assets/{v}"} for k, v in slide.pop("_assets").items()}
        slide["base"] = f"{pdf.name}#{prefix}"
        spec = {"width": W, "height": round(page.rect.height * W / page.rect.width), "assets": assets, "slides": [slide]}
        (out / f"{prefix}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        page.get_pixmap(matrix=pymupdf.Matrix(W / page.rect.width, W / page.rect.width)).save(out / f"{prefix}.png")
        written.append(out / f"{prefix}.json")
    return written


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("pdf", type=Path)
    p.add_argument("--pages", type=int, nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    for path in extract(a.pdf, a.pages, a.out):
        sys.stdout.buffer.write(f"{path}\n".encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
