"""Check that an edited page changed only the elements its plan declared.

Each slide in the designer's spec carries:
  "mode": "edit" | "new"
  "base_spec": path to the original page spec (data/design/layouts/<row>/pNN.json) — for "edit"
  "changes": ["Text/02", ...]  element names the approved plan allows to change
Elements are matched by name; "note" is ignored. "new" pages are reported but not diffed
(the reviewer compares them with their template visually).

Usage: python tools/check_layout_diff.py SPEC.json [--out PATH]
Exit code 0 = every edited page changed only declared elements.
"""
import argparse
import json
import sys
from pathlib import Path

IGNORE = {"note"}


def _strip(e):
    return {k: v for k, v in e.items() if k not in IGNORE}


def diff_slide(base: dict, out: dict) -> dict:
    b = {e["name"]: _strip(e) for e in base["elements"]}
    o = {e["name"]: _strip(e) for e in out["elements"]}
    return {"changed": [n for n in o if n in b and o[n] != b[n]],
            "added": [n for n in o if n not in b],
            "removed": [n for n in b if n not in o]}


def check(out: dict, base: dict) -> dict:
    d = diff_slide(base, out)
    declared = set(out.get("changes", []))
    undeclared = [n for n in d["changed"] + d["added"] + d["removed"] if n not in declared]
    return {**d, "declared": sorted(declared), "undeclared": undeclared, "ok": not undeclared}


def check_spec(spec: dict, root: Path) -> dict:
    pages = []
    for s in spec["slides"]:
        if s.get("mode") != "edit":
            pages.append({"page": s["name"], "mode": s.get("mode", "missing"), "ok": s.get("mode") == "new"})
            continue
        base = json.loads((root / s["base_spec"]).read_text(encoding="utf-8"))["slides"][0]
        pages.append({"page": s["name"], "mode": "edit", "base_spec": s["base_spec"], **check(s, base)})
    return {"ok": all(p["ok"] for p in pages), "pages": pages}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("spec", type=Path)
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    result = check_spec(json.loads(a.spec.read_text(encoding="utf-8")), a.root)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text, encoding="utf-8")
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
