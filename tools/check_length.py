"""Check cover-letter answers against per-question character limits.

answers JSON:   {"answers": [{"id": "q1", "text": "..."}]}
questions JSON: {"count_rule": {"mode": "with_spaces"|"without_spaces", "newline_chars": 1|2},
                 "questions": [{"id": "q1", "limit": 500}, ...]}

Submission sites differ in how they count line breaks; the rule is configurable.

Usage: python tools/check_length.py answers.json questions.json [--out PATH]
Exit code 0 = all within limits, 1 = over limit or missing answer.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def count(text: str, mode: str = "with_spaces", newline_chars: int = 1) -> int:
    text = text.replace("\r\n", "\n")
    if mode == "without_spaces":
        return len(re.sub(r"\s", "", text))
    return len(text) + (newline_chars - 1) * text.count("\n")


def check(answers_doc: dict, questions_doc: dict) -> dict:
    rule = questions_doc.get("count_rule", {})
    mode, nl = rule.get("mode", "with_spaces"), rule.get("newline_chars", 1)
    answers = {a["id"]: a.get("text", "") for a in answers_doc.get("answers", [])}
    results = []
    for q in questions_doc["questions"]:
        if q["id"] not in answers or not answers[q["id"]].strip():
            results.append({"id": q["id"], "ok": False, "error": "missing answer"})
            continue
        c = count(answers[q["id"]], mode, nl)
        results.append({"id": q["id"], "count": c, "limit": q["limit"],
                        "over_by": max(0, c - q["limit"]), "ok": c <= q["limit"]})
    return {"ok": all(r["ok"] for r in results), "rule": {"mode": mode, "newline_chars": nl}, "results": results}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("answers", type=Path)
    p.add_argument("questions", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    result = check(json.loads(a.answers.read_text(encoding="utf-8")),
                   json.loads(a.questions.read_text(encoding="utf-8")))
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(out, encoding="utf-8")
    sys.stdout.buffer.write((out + "\n").encode("utf-8"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
