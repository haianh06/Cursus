"""Normalize data/clean documents into citation-ready JSONL chunks.

Usage: python backend/scripts/ingest_clean_corpus.py --source data/clean --output data/cursus_corpus.jsonl
Legacy .ppt files are converted through LibreOffice headless before extraction.
"""
from __future__ import annotations

import argparse, json, shutil, subprocess, tempfile
from hashlib import sha256
from pathlib import Path

from docx import Document
from pypdf import PdfReader
from pptx import Presentation

SUPPORTED = {".docx", ".pdf", ".pptx", ".ppt"}

def subject_code(path: Path) -> str:
    for part in path.parts:
        if "." in part and part.split(".", 1)[-1].upper().isalnum():
            return part.split(".", 1)[-1]
    return path.parent.name

def extract(path: Path) -> list[tuple[str, str]]:
    if path.suffix == ".docx":
        doc = Document(path); return [("document", "\n".join(p.text for p in doc.paragraphs if p.text.strip()))]
    if path.suffix == ".pdf":
        return [(f"page {i}", page.extract_text() or "") for i, page in enumerate(PdfReader(path).pages, 1)]
    if path.suffix == ".ppt":
        if not shutil.which("soffice"):
            raise RuntimeError("LibreOffice (soffice) is required for legacy .ppt")
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run(["soffice", "--headless", "--convert-to", "pptx", "--outdir", temp, str(path)], check=True, capture_output=True)
            converted = Path(temp) / f"{path.stem}.pptx"
            return extract(converted)
    deck = Presentation(path)
    return [(f"slide {i}", "\n".join(shape.text for shape in slide.shapes if hasattr(shape, "text") and shape.text.strip())) for i, slide in enumerate(deck.slides, 1)]

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--source", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True); report = {"files": 0, "chunks": 0, "errors": []}
    with args.output.open("w", encoding="utf-8") as writer:
        for file in sorted(p for p in args.source.rglob("*") if p.suffix.lower() in SUPPORTED):
            report["files"] += 1
            try:
                for index, (location, text) in enumerate(extract(file), 1):
                    text = text.strip()
                    if not text: continue
                    record = {"id": sha256(f"{file}:{index}".encode()).hexdigest()[:24], "subject_code": subject_code(file), "title": file.stem, "source_path": str(file.relative_to(args.source)), "location": location, "text": text, "checksum": sha256(file.read_bytes()).hexdigest()}
                    writer.write(json.dumps(record, ensure_ascii=False) + "\n"); report["chunks"] += 1
            except Exception as exc: report["errors"].append({"path": str(file), "error": str(exc)})
    args.output.with_suffix(".report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__": main()
