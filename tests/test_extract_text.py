"""extract_text: PDF는 페이지별, docx는 문단별 텍스트. 한글·공백 경로 포함."""
import zipfile

from extract_text import extract


def make_pdf(path, pages):
    """Minimal valid PDF with one Helvetica text line per page (ASCII only)."""
    objs = []
    n = len(pages)
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n))
    objs.append("<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>")
    font_id = 3 + 2 * n
    for i, text in enumerate(pages):
        content_id = 4 + 2 * i
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>")
        stream = f"BT /F1 12 Tf 20 150 Td ({text}) Tj ET"
        objs.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(out)


def make_docx(path, paragraphs):
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"<w:body>{body}</w:body></w:document>")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", xml)


def test_pdf_pages(tmp_path):
    d = tmp_path / "바탕 화면"
    d.mkdir()
    p = d / "포트폴리오 샘플.pdf"
    make_pdf(p, ["Page one RAG chatbot", "Page two deploy"])
    r = extract(p)
    assert r["kind"] == "pdf"
    assert len(r["pages"]) == 2
    assert "RAG chatbot" in r["pages"][0]
    assert "deploy" in r["pages"][1]


def test_docx_paragraphs_korean(tmp_path):
    p = tmp_path / "자기소개서 샘플.docx"
    make_docx(p, ["첫 문단입니다.", "둘째 문단: 사용자 120명"])
    r = extract(p)
    assert r["kind"] == "docx"
    assert r["paragraphs"] == ["첫 문단입니다.", "둘째 문단: 사용자 120명"]


def test_unsupported_extension(tmp_path):
    p = tmp_path / "a.hwp"
    p.write_bytes(b"x")
    try:
        extract(p)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
