"""Add company names from a job posting to the private-terms list (data/private_terms.json).

The list feeds tests/test_no_private_terms.py and tools/check_commit_msg.py, so a new
posting's company name is blocked from commits without the user editing the list.
Usage: python tools/add_private_term.py NAME [NAME ...] [--terms data/private_terms.json]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def norm(s):
    return "".join(s.split()).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("--terms", default=str(ROOT / "data" / "private_terms.json"))
    a = ap.parse_args()
    path = Path(a.terms)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"terms": [], "allow": []}
    data.setdefault("allow", [])
    seen = {norm(t) for t in data["terms"]}
    added = []
    for name in a.names:
        name = name.strip()
        if name and norm(name) not in seen:
            data["terms"].append(name)
            seen.add(norm(name))
            added.append(name)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"added {len(added)}")


if __name__ == "__main__":
    main()
