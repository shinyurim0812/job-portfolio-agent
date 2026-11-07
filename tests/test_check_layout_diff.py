"""check_layout_diff: 수정 페이지가 원본 spec에서 선언한 요소만 바꿨는지."""
import copy

from check_layout_diff import diff_slide, check

BASE = {"name": "p10", "elements": [
    {"type": "rect", "name": "Shape/01", "x": 0, "y": 0, "w": 109, "h": 106, "fill": "#142B57"},
    {"type": "text", "name": "Text/02", "text": "old title", "x": 96, "y": 116, "w": 1349, "h": 78, "size": 56,
     "lh": 78, "color": "#20242C"},
    {"type": "text", "name": "Text/03", "text": "label", "x": 96, "y": 251, "w": 92, "h": 34, "size": 24,
     "lh": 34, "color": "#000000"},
]}


def edited(**changes):
    s = copy.deepcopy(BASE)
    for name, fields in changes.items():
        el = next(e for e in s["elements"] if e["name"] == name)
        el.update(fields)
    return s


def test_unchanged_page_has_no_diff():
    assert diff_slide(BASE, copy.deepcopy(BASE)) == {"changed": [], "added": [], "removed": []}


def test_declared_text_change_passes():
    out = edited(**{"Text/02": {"text": "new title"}})
    out["changes"] = ["Text/02"]
    r = check(out, BASE)
    assert r["ok"], r


def test_undeclared_change_fails_and_is_named():
    out = edited(**{"Text/02": {"text": "new title"}, "Text/03": {"y": 300}})
    out["changes"] = ["Text/02"]
    r = check(out, BASE)
    assert not r["ok"]
    assert r["undeclared"] == ["Text/03"]


def test_added_and_removed_elements_count_as_changes():
    out = copy.deepcopy(BASE)
    out["elements"] = out["elements"][:2] + [{"type": "rect", "name": "Shape/new", "x": 1, "y": 1, "w": 2, "h": 2}]
    d = diff_slide(BASE, out)
    assert d["added"] == ["Shape/new"] and d["removed"] == ["Text/03"]
    out["changes"] = ["Shape/new"]
    assert check(out, BASE)["undeclared"] == ["Text/03"]


def test_slide_without_mode_fails(tmp_path):
    """mode를 안 적으면 원본 비교를 건너뛴 것이므로 실패로 본다."""
    from check_layout_diff import check_spec
    assert not check_spec({"slides": [copy.deepcopy(BASE)]}, tmp_path)["ok"]


def test_note_field_is_ignored():
    out = edited(**{"Text/03": {"note": "checked bold"}})
    assert diff_slide(BASE, out)["changed"] == []
