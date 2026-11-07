"""Check a job-posting analysis (analysis.json) against the posting text (jd.txt).

Catches what an LLM is likely to get wrong silently:
- a "verbatim quote" that is paraphrased or invented
- the wrong number of core tasks, duplicate quotes, missing sections
- competency names that are not words from the posting

It does NOT judge whether the analysis is good.

Usage: python tools/check_analysis.py analysis.json jd.txt [--out checks/analysis.json]
Exit code 0 = pass, 1 = fail.
"""
import argparse
import json
import sys
from pathlib import Path

from textnorm import normalize

SECTIONS = ["title_dept", "core_tasks", "requirements", "background", "core_competencies", "cover_letter_tips"]
MIN_QUOTE_CHARS = 10


def check(analysis: dict, jd_text: str) -> dict:
    errors = []
    jd = normalize(jd_text)

    for s in SECTIONS:
        if s not in analysis:
            errors.append(f"missing section: {s}")

    tasks = analysis.get("core_tasks", [])
    if len(tasks) != 3:
        errors.append(f"core_tasks must have exactly 3 items (got {len(tasks)})")
    seen = set()
    for i, t in enumerate(tasks):
        q = normalize(t.get("quote", ""))
        if len(q) < MIN_QUOTE_CHARS:
            errors.append(f"core_tasks[{i}].quote too short (<{MIN_QUOTE_CHARS} chars)")
        elif q not in jd:
            errors.append(f"core_tasks[{i}].quote not found in posting: {t.get('quote')!r}")
        if q in seen:
            errors.append(f"core_tasks[{i}].quote duplicates another quote")
        seen.add(q)

    comps = analysis.get("core_competencies", [])
    if len(comps) != 3:
        errors.append(f"core_competencies must have exactly 3 items (got {len(comps)})")
    for i, c in enumerate(comps):
        name = normalize(c.get("name", ""))
        if not name or name not in jd:
            errors.append(f"core_competencies[{i}].name not taken from posting: {c.get('name')!r}")

    return {"ok": not errors, "errors": errors}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("analysis", type=Path)
    p.add_argument("jd", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    result = check(json.loads(a.analysis.read_text(encoding="utf-8")), a.jd.read_text(encoding="utf-8"))
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(out, encoding="utf-8")
    sys.stdout.buffer.write((out + "\n").encode("utf-8"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
