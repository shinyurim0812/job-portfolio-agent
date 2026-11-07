"""Append an agent start/end event with a timestamp to a JSONL run log.

Usage: python tools/log.py <start|end> <agent-name> [--log PATH]

The timestamp is taken by this script, not written by the agent itself,
so overlapping start/end times are evidence that agents ran in parallel.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_LOG = Path("data/run-log.jsonl")


def append_event(event: str, agent: str, log_path: Path) -> dict:
    if event not in ("start", "end"):
        raise ValueError("event must be 'start' or 'end'")
    record = {"ts": datetime.now().isoformat(timespec="milliseconds"), "event": event, "agent": agent}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_events(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def overlapping(events: list[dict], a: str, b: str) -> bool:
    """True if the [start, end] intervals of agents a and b overlap."""
    def span(name):
        starts = [e["ts"] for e in events if e["agent"] == name and e["event"] == "start"]
        ends = [e["ts"] for e in events if e["agent"] == name and e["event"] == "end"]
        if not starts or not ends:
            raise ValueError(f"missing start/end for {name}")
        return starts[-1], ends[-1]

    (sa, ea), (sb, eb) = span(a), span(b)
    return sa < eb and sb < ea


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("event", choices=["start", "end"])
    p.add_argument("agent")
    p.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = p.parse_args(argv)
    rec = append_event(args.event, args.agent, args.log)
    print(json.dumps(rec, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
