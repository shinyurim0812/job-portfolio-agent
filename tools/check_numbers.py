"""Check that every number in a draft appears in the source material.

A number with a unit ("87%", "120명") must appear with the same unit in the sources.
A bare number must appear as a number in the sources. List markers ("1.", "2)")
and identifiers like "v2"/"q1" are ignored. This catches invented or mis-copied
figures; it cannot tell whether a supported figure is used in the right context.

Usage: python tools/check_numbers.py TARGET --sources SRC [SRC ...] [--out PATH]
TARGET may be .md/.txt, a cover-letter JSON ({"answers": [...]}) or a portfolio spec JSON.
Exit code 0 = all supported, 1 = unsupported numbers found.
"""
import argparse
import json
import re
import sys
from pathlib import Path

UNITS = ["퍼센트", "개월", "시간", "페이지", "가지", "단계", "%", "명", "건", "배", "개", "회", "분", "초",
         "일", "주", "년", "원", "만", "천", "억", "ms", "점", "위", "장", "자", "차", "번", "줄", "x"]
NUM = re.compile(
    r"(?<![\w.,])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s?(" + "|".join(map(re.escape, UNITS)) + r")?"
)
LIST_MARKER = re.compile(r"^\s*(?:#+\s*)?(\d+)[.)]\s")
COMMA_IN_NUMBER = re.compile(r"(?<=\d),(?=\d{3})")


def extract_numbers(text: str) -> list[dict]:
    found = []
    for n, line in enumerate(text.splitlines(), start=1):
        marker = LIST_MARKER.match(line)
        skip_until = marker.end(1) if marker else -1
        for m in NUM.finditer(line):
            if m.start() < skip_until:
                continue
            value = m.group(1).replace(",", "") + (f".{m.group(2)}" if m.group(2) else "")
            unit = m.group(3) or ""
            found.append({"token": m.group(0).replace(" ", ""), "value": value, "unit": unit, "line": n})
    return found


def _norm_source(source: str) -> str:
    return re.sub(r"\s+", "", COMMA_IN_NUMBER.sub("", source))


SPACED_DIGITS = re.compile(r"(?<=[\d.])[ \t]+(?=[\d.])")


def unsupported(draft: str, source: str) -> list[dict]:
    # Figma-exported PDFs extract as "2 0 2 6 . 0 1"; join digits before matching
    source = SPACED_DIGITS.sub("", source)
    src = _norm_source(source)
    bare_numbers = {n["value"] for n in extract_numbers(source)}
    bad = []
    for n in extract_numbers(draft):
        if n["unit"]:
            ok = (n["value"] + n["unit"]) in src
        else:
            ok = n["value"] in bare_numbers
        if not ok:
            bad.append(n)
    return bad


def texts_from_spec(obj) -> list[str]:
    """Collect only values of "text" keys (ignores coordinates, sizes, colors)."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "text" and isinstance(v, str):
                out.append(v)
            else:
                out.extend(texts_from_spec(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(texts_from_spec(v))
    return out


def _all_strings(obj) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in _all_strings(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in _all_strings(v)]
    return []


def load_target(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if path.suffix != ".json":
        return raw
    data = json.loads(raw)
    if isinstance(data, dict) and "answers" in data:
        return "\n".join(a.get("text", "") for a in data["answers"])
    return "\n".join(texts_from_spec(data))


def load_source(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    return "\n".join(_all_strings(json.loads(raw))) if path.suffix == ".json" else raw


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("target", type=Path)
    p.add_argument("--sources", nargs="+", type=Path, required=True)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    source = "\n".join(load_source(s) for s in a.sources)
    bad = unsupported(load_target(a.target), source)
    result = {"ok": not bad, "unsupported": bad}
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(out, encoding="utf-8")
    sys.stdout.buffer.write((out + "\n").encode("utf-8"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
