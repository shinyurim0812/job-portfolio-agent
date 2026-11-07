"""Convert example frames from a saved Figma get_metadata XML into layout template specs.

get_metadata gives node type, name (= text content for text nodes), position and size,
but no colors or font sizes. Font size is estimated from box height and text length and
marked with a note; colors are placeholders to be picked from the reference screenshot.
No Figma call is made (the account allows few read calls per month).

Usage: python tools/figma_templates.py data/design/figma-metadata.xml \
         --frame 360:3025=ex-background --frame 360:3084=ex-insight \
         --refs data/design/figma-refs --out data/design/templates
Writes <name>.json (one-slide spec, "base" = "figma#<id>") and copies <name>.png from --refs.
"""
import argparse
import json
import math
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

TEXT, FILL, STROKE = "#252529", "#E5E5E5", "#252529"
COLOR_NOTE = "색은 자리값: 참고 그림(reference)에서 정한다"


def _f(e, k):
    return float(e.get(k, 0))


def _units(text):
    # rough advance per char in em: Hangul ~1.0, Latin/digits/space ~0.55
    return sum(1.0 if "가" <= ch <= "힣" else 0.55 for ch in text)


def estimate_size(text, w, h):
    units = _units(text) or 1
    for n in range(1, 9):
        size = h / (n * 1.45)
        if units * size <= w * n * 1.1:
            return max(8, round(size)), n
    return max(8, round(h / (8 * 1.45))), 8


def wrap(text, size, w):
    per = max(1, int(w / size))  # conservative: Hangul width ~ 1 em
    words, lines, cur = text.split(), [], ""
    for word in words:
        cand = (cur + " " + word).strip()
        if _units(cand) <= per or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:  # break long words too
        while _units(ln) > per and len(ln) > 1:
            out.append(ln[:per])
            ln = ln[per:]
        out.append(ln)
    return out


def frame_to_slide(frame, name, W=1920, H=1080) -> dict:
    elements = []

    def walk(node, ox, oy, pbox):
        for c in node:
            x, y, w, h = _f(c, "x"), _f(c, "y"), _f(c, "width"), _f(c, "height")
            # metadata children of groups/auto frames may already be in frame coordinates
            if pbox and not (x >= pbox[0] - 1 and y >= pbox[1] - 1 and x + w <= pbox[2] + 1 and y + h <= pbox[3] + 1):
                x, y = x + ox, y + oy
            if c.tag in ("frame", "group", "section", "instance", "component"):
                walk(c, x, y, (x, y, x + w, y + h))
                continue
            x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
            if x1 - x0 <= 0 and y1 - y0 <= 0 or x0 >= W or y0 >= H or x1 <= 0 or y1 <= 0:
                continue
            label = f"{c.tag}/{(c.get('name') or '')[:30]}"
            if c.tag == "text":
                if (x0, y0, x1, y1) != (x, y, x + w, y + h):
                    continue  # text cut by the canvas edge is an off-frame note
                text = c.get("name") or ""
                size, _ = estimate_size(text, w, h)
                lines = wrap(text, size, w)
                lh = round(size * 1.45)
                th = min(len(lines) * lh, H - y0)
                if len(lines) * lh > th:
                    continue
                elements.append({"type": "text", "name": label, "text": "\n".join(lines),
                                 "x": x0, "y": y0, "w": max(w, size), "h": th, "size": size, "lh": lh,
                                 "bold": False, "color": TEXT, "align": "LEFT",
                                 "note": "글자 크기·굵기는 상자 높이로 추정. " + COLOR_NOTE})
            elif min(x1 - x0, y1 - y0) <= (2 if c.tag in ("vector", "line") else 1.5):
                # hairline: a divider or connector drawn as a thin box/vector
                horizontal = (x1 - x0) >= (y1 - y0)
                elements.append({"type": "line", "name": label, "x": x0, "y": y0,
                                 "w": x1 - x0 if horizontal else 0, "h": 0 if horizontal else y1 - y0,
                                 "stroke": STROKE, "weight": 1, "note": COLOR_NOTE})
            elif c.tag == "ellipse":
                elements.append({"type": "ellipse", "name": label, "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0,
                                 "stroke": STROKE, "strokeWeight": 1, "note": COLOR_NOTE})
            elif x1 - x0 > 0 and y1 - y0 > 0:
                elements.append({"type": "rect", "name": label, "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0,
                                 "fill": FILL, "note": "이미지 자리일 수 있음. " + COLOR_NOTE})

    walk(frame, 0, 0, None)
    for e in elements:
        for k in ("x", "y", "w", "h"):
            e[k] = round(e[k], 1)
    return {"name": name, "elements": elements}


def convert(meta: Path, frames: dict, out: Path, refs: Path = None) -> list:
    raw = meta.read_text(encoding="utf-8")
    root = ET.fromstring("<wrap>" + raw + "</wrap>")
    idx = {e.get("id"): e for e in root.iter() if e.get("id")}
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for fid, name in frames.items():
        f = idx[fid]
        slide = frame_to_slide(f, name)
        slide["base"] = f"figma#{fid}"
        if refs and (refs / f"{name}.png").exists():
            shutil.copy(refs / f"{name}.png", out / f"{name}.png")
            slide["reference"] = f"{name}.png"
        spec = {"width": 1920, "height": 1080, "assets": {}, "slides": [slide]}
        (out / f"{name}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        written.append(out / f"{name}.json")
    return written


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("meta", type=Path)
    p.add_argument("--frame", action="append", required=True, help="NODE_ID=name")
    p.add_argument("--refs", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    frames = dict(f.split("=", 1) for f in a.frame)
    for path in convert(a.meta, frames, a.out, a.refs):
        sys.stdout.buffer.write(f"{path}\n".encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
