"""Extract text from PDF (per page, pypdf) and DOCX (per paragraph, stdlib zipfile).

Agents read these text files instead of the original documents, which keeps
their context small. Layout is not preserved; agents look at the PDF page itself
only when layout matters.

Usage: python tools/extract_text.py FILE [FILE ...] --out DIR
Writes DIR/<stem>.txt (PDF pages separated by "=== page N ===").
"""
import argparse
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract(path: Path) -> dict:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return {"kind": "pdf", "pages": [(p.extract_text() or "") for p in reader.pages]}
    if suffix == ".docx":
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("word/document.xml"))
        paras = []
        for p in root.iter(f"{W}p"):
            text = "".join(t.text or "" for t in p.iter(f"{W}t")).strip()
            if text:
                paras.append(text)
        return {"kind": "docx", "paragraphs": paras}
    raise ValueError(f"unsupported file type: {path.suffix}")


def to_text(result: dict) -> str:
    if result["kind"] == "pdf":
        return "\n".join(f"=== page {i} ===\n{t}" for i, t in enumerate(result["pages"], start=1))
    return "\n".join(result["paragraphs"])


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    for f in a.files:
        r = extract(f)
        dest = a.out / f"{f.stem}.txt"
        dest.write_text(to_text(r), encoding="utf-8")
        n = len(r.get("pages", r.get("paragraphs", [])))
        sys.stdout.buffer.write(f"{dest} ({r['kind']}, {n} {'pages' if r['kind'] == 'pdf' else 'paragraphs'})\n".encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
