"""Assemble the designer's starting spec from original page specs and templates.

  --edit PATH:NAME  an existing page to modify (mode "edit"; only plan-declared elements may change)
  --new  PATH:NAME  a new page started from a template or another page (mode "new")
Pages keep the given order. Asset paths are rewritten relative to the output spec, and each
slide records "base_spec" (relative to --root) for check_layout_diff.py.

Usage: python tools/start_spec.py --new data/design/templates/ex-background.json:p03 \
         --edit data/design/layouts/service_fullstack/p10.json:p10 --out JOB_DIR/portfolio-spec.json
"""
import argparse
import json
import os
import sys
from pathlib import Path


def start(pages, out: Path, root: Path = Path(".")) -> dict:
    spec = {"width": 1920, "height": 1080, "assets": {}, "slides": []}
    out.parent.mkdir(parents=True, exist_ok=True)
    for mode, path, name in pages:
        src = json.loads(Path(path).read_text(encoding="utf-8"))
        for key, asset in src.get("assets", {}).items():
            target = (Path(path).parent / asset["path"]).resolve()
            spec["assets"][key] = {"path": os.path.relpath(target, out.parent.resolve()).replace("\\", "/")}
        slide = src["slides"][0]
        slide["name"] = name
        slide["mode"] = mode
        slide["base_spec"] = os.path.relpath(Path(path).resolve(), Path(root).resolve()).replace("\\", "/")
        if mode == "edit":
            slide["changes"] = []
        spec["slides"].append(slide)
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    return spec


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--edit", action="append", default=[])
    p.add_argument("--new", action="append", default=[])
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path("."))
    a = p.parse_args(argv)
    # keep command-line order across --edit/--new
    order, args = [], sys.argv[1:] if argv is None else argv
    for i, tok in enumerate(args):
        if tok in ("--edit", "--new"):
            path, name = args[i + 1].rsplit(":", 1)
            order.append((tok[2:], Path(path), name))
    start(order, a.out, a.root)
    sys.stdout.buffer.write(f"{a.out}\n".encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
