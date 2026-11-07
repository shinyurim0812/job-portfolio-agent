"""Check that excluded experiences did not leak into an output.

Exclusions file (kept private in data/): {"page_ids": [...], "keywords": [...]}
- page_ids: Notion page IDs, matched with or without dashes
- keywords: case-insensitive substrings

Keyword matching misses paraphrases; it is a safety net, not proof.

Usage: python tools/check_exclusions.py FILE [FILE ...] --exclusions data/exclusions.json [--out PATH]
Exit code 0 = no hits, 1 = hits.
"""
import argparse
import json
import sys
from pathlib import Path


def scan(text: str, exclusions: dict) -> list[dict]:
    ids = [i.replace("-", "").lower() for i in exclusions.get("page_ids", []) if i]
    kws = [k for k in exclusions.get("keywords", []) if k]
    hits = []
    for n, line in enumerate(text.splitlines(), start=1):
        low = line.lower()
        flat = low.replace("-", "")
        for pid in ids:
            if pid in flat:
                hits.append({"line": n, "kind": "page_id", "match": pid})
        for kw in kws:
            pos = low.find(kw.lower())
            if pos >= 0:
                hits.append({"line": n, "kind": "keyword", "match": line[pos:pos + len(kw)]})
    return hits


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--exclusions", type=Path, default=Path("data/exclusions.json"))
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    excl = json.loads(a.exclusions.read_text(encoding="utf-8"))
    report = {}
    for f in a.files:
        hits = scan(f.read_text(encoding="utf-8"), excl)
        if hits:
            report[str(f)] = hits
    result = {"ok": not report, "hits": report}
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(out, encoding="utf-8")
    sys.stdout.buffer.write((out + "\n").encode("utf-8"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
