"""log: 스크립트가 찍은 시각으로 병렬 실행(구간 겹침)을 판정."""
import pytest

from log import append_event, read_events, overlapping


def ev(ts, event, agent):
    return {"ts": ts, "event": event, "agent": agent}


def test_append_and_read(tmp_path):
    p = tmp_path / "run.jsonl"
    append_event("start", "a", p)
    append_event("end", "a", p)
    events = read_events(p)
    assert [e["event"] for e in events] == ["start", "end"]


def test_overlap_true():
    es = [ev("T10", "start", "a"), ev("T11", "start", "b"), ev("T12", "end", "a"), ev("T13", "end", "b")]
    assert overlapping(es, "a", "b")


def test_overlap_false_when_sequential():
    es = [ev("T10", "start", "a"), ev("T11", "end", "a"), ev("T12", "start", "b"), ev("T13", "end", "b")]
    assert not overlapping(es, "a", "b")


def test_missing_end_raises():
    with pytest.raises(ValueError):
        overlapping([ev("T1", "start", "a"), ev("T2", "start", "b"), ev("T3", "end", "b")], "a", "b")


def test_bad_event_rejected(tmp_path):
    with pytest.raises(ValueError):
        append_event("middle", "a", tmp_path / "x.jsonl")
