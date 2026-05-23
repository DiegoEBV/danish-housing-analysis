#!/usr/bin/env python3
"""
Convert a PDF guide (slide deck) to Markdown.

Uses PyMuPDF (fitz) for text extraction. Groups character-level spans into
lines using y-position proximity, then classifies heading levels by font size.

Usage:
    python scripts/convert_guide_to_md.py examen/guia/semana-07-seleccion-y-calculos.pdf
    python scripts/convert_guide_to_md.py examen/guia/semana-07-seleccion-y-calculos.pdf --out docs/refs/
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF — must be system python (not uv venv)
except ModuleNotFoundError:
    sys.exit("PyMuPDF (fitz) not found. Run with: python scripts/convert_guide_to_md.py ...")


# ── helpers ─────────────────────────────────────────────────────────────────

def _page_title_size(page: "fitz.Page") -> tuple[float, float]:
    """
    Return (title_size, body_size) for a page by analysing span font sizes.
    title_size = max font size found; body_size = median font size.
    Uses get_text('dict') for font metadata only — not for text content.
    """
    sizes: list[float] = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if span["text"].strip():
                    sizes.append(round(span["size"], 1))
    if not sizes:
        return 24.0, 12.0
    sizes_s = sorted(sizes)
    return max(sizes_s), sizes_s[len(sizes_s) // 2]


def _text_lines(page: "fitz.Page") -> list[str]:
    """
    Extract readable text lines from a page using get_text('text').
    Preserves word spacing (PyMuPDF reconstructs it from glyph positions).
    Returns list of stripped non-empty lines.
    """
    return [l.strip() for l in page.get_text("text").split("\n") if l.strip()]


def _classify_line(text: str, is_first: bool, title_size: float,
                   body_size: float, page_dict_blocks: list[dict]) -> str:
    """Return markdown-prefixed line. is_first = first non-empty line on the slide."""
    if re.match(r"^\d{1,3}$", text):  # bare page number
        return ""

    # First line of a slide is treated as its title
    if is_first:
        # Section divider pattern
        if re.match(r"^Parte\s+\d+", text, re.IGNORECASE):
            return f"## {text}"
        return f"### {text}"

    # Sub-heading: check if this line's dominant font size is larger than body
    # We approximate by checking if the line appears in a "large" span in the dict
    line_size = _approx_line_size(text, page_dict_blocks)
    if line_size >= title_size * 0.75 and line_size > body_size * 1.2:
        return f"#### {text}"

    # Bullet heuristic
    if re.match(r"^[•·▪▸►◦○●]\s*", text):
        body = re.sub(r"^[•·▪▸►◦○●]\s*", "", text)
        return f"- {body}"

    # Numbered list — keep as-is
    if re.match(r"^\d+\.\s", text):
        return text

    return text


def _approx_line_size(text: str, blocks: list[dict]) -> float:
    """
    Find the font size of the first span whose text contains a substring of `text`.
    Fallback: 0.0 (body).
    """
    sample = text[:20].strip()
    if not sample:
        return 0.0
    # Search across concatenated span texts in each line
    for block in blocks:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            line_text = "".join(s["text"] for s in line["spans"])
            # Match cleaned-up version
            if sample.replace(" ", "") in line_text.replace(" ", ""):
                sizes = [s["size"] for s in line["spans"] if s["text"].strip()]
                return max(sizes) if sizes else 0.0
    return 0.0


def convert_pdf(pdf_path: Path) -> str:
    """Convert a PDF presentation to a Markdown string."""
    doc = fitz.open(str(pdf_path))
    sections: list[str] = []

    # Document-level heading from page 1
    cover_lines = [l.strip() for l in doc[0].get_text("text").split("\n") if l.strip()]
    doc_title = " — ".join(cover_lines[:3])[:120]
    sections.append(f"# {doc_title}\n")

    for page_num, page in enumerate(doc):
        text_lines = _text_lines(page)
        if not text_lines:
            continue

        title_size, body_size = _page_title_size(page)
        dict_blocks = page.get_text("dict")["blocks"]

        md_lines: list[str] = [f"\n---\n\n<!-- slide {page_num + 1} -->"]
        for i, line in enumerate(text_lines):
            md = _classify_line(line, i == 0, title_size, body_size, dict_blocks)
            if md:
                md_lines.append(md)

        if len(md_lines) > 2:
            sections.append("\n".join(md_lines))

    return "\n".join(sections) + "\n"


def main(argv: list[str] = sys.argv[1:]) -> int:
    if not argv:
        print("Usage: python scripts/convert_guide_to_md.py <pdf> [--out <dir>]")
        return 1

    pdf_path = Path(argv[0])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        return 1

    out_dir = pdf_path.parent  # default: same folder as PDF
    if "--out" in argv:
        idx = argv.index("--out")
        out_dir = Path(argv[idx + 1])
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / (pdf_path.stem + ".md")

    print(f"Converting {pdf_path.name} ({pdf_path.stat().st_size // 1024} KB) …")
    md = convert_pdf(pdf_path)

    out_path.write_text(md, encoding="utf-8")
    lines = md.count("\n")
    print(f"Written {out_path}  ({lines} lines, {len(md)//1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
