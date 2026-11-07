"""start_spec: 원본 페이지·템플릿 spec을 묶어 디자이너의 시작 spec을 만든다."""
import json
from pathlib import Path

from start_spec import start


def write(path: Path, slide: dict, assets=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"width": 1920, "height": 1080, "assets": assets or {}, "slides": [slide]}), encoding="utf-8")


def test_edit_and_new_pages_keep_order_and_record_base(tmp_path):
    lay = tmp_path / "layouts" / "row"
    (lay / "assets").mkdir(parents=True)
    (lay / "assets" / "p10-img1.png").write_bytes(b"x")
    write(lay / "p10.json", {"name": "p10", "elements": [{"type": "image", "name": "Image/01", "key": "p10_img1"}]},
          {"p10_img1": {"path": "assets/p10-img1.png"}})
    write(tmp_path / "templates" / "ex-bg.json", {"name": "ex-bg", "elements": [], "reference": "ex-bg.png"})
    out = tmp_path / "jobs" / "job-001" / "portfolio-spec.json"
    start([("new", tmp_path / "templates" / "ex-bg.json", "p03"), ("edit", lay / "p10.json", "p10")], out, tmp_path)
    spec = json.loads(out.read_text(encoding="utf-8"))
    s3, s10 = spec["slides"]
    assert (s3["name"], s3["mode"], s3["base_spec"]) == ("p03", "new", "templates/ex-bg.json")
    assert (s10["mode"], s10["base_spec"], s10["changes"]) == ("edit", "layouts/row/p10.json", [])
    # 이미지 경로는 출력 spec 위치 기준으로 다시 쓴다
    assert (out.parent / spec["assets"]["p10_img1"]["path"]).resolve() == (lay / "assets" / "p10-img1.png").resolve()
