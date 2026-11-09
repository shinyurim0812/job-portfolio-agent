"""Block a commit whose message contains a private term (company or real name).

Runs as the git commit-msg hook, so the bad message never becomes a commit.
Install once: python tools/check_commit_msg.py --install
Usage (by git): python tools/check_commit_msg.py MSG_FILE [--terms data/private_terms.json]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_terms(text, terms, allow=()):
    low = text.lower()
    for word in allow:
        low = low.replace(word.lower(), " ")
    return [t for t in terms if t.lower() in low]


def install():
    hook = ROOT / ".git" / "hooks" / "commit-msg"
    hook.write_text('#!/bin/sh\npython tools/check_commit_msg.py "$1"\n', encoding="utf-8", newline="\n")
    print(f"installed {hook}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("msg_file", nargs="?")
    ap.add_argument("--terms", default=str(ROOT / "data" / "private_terms.json"))
    ap.add_argument("--install", action="store_true")
    a = ap.parse_args()
    if a.install:
        return install()
    terms_file = Path(a.terms)
    if not terms_file.exists():
        return 0
    data = json.loads(terms_file.read_text(encoding="utf-8"))
    hits = find_terms(Path(a.msg_file).read_text(encoding="utf-8"), data["terms"], data.get("allow", []))
    if hits:
        sys.stderr.buffer.write(f"commit blocked: private term in message: {hits}\n".encode("utf-8"))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
