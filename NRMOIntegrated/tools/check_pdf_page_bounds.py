#!/usr/bin/env python3
"""
[V7.3 PDF PAGE-BOUNDS GUARD]

Scans a built PDF for text content that extends past each page's
MediaBox (i.e. genuine right/bottom-edge clipping), not merely LaTeX's
internal "Overfull \\hbox" warnings (most of which never reach the
physical page edge and are visually harmless).

Generic by design: this does not hardcode any page numbers. It re-scans
the full document every run, so it catches regressions introduced by
future edits anywhere in the source, not just the specific pages fixed
in the 2026-09-23 layout-repair pass.

Usage:
    python3 tools/check_pdf_page_bounds.py [path/to/file.pdf]

Exit code 0 = no unexpected overflow found. Exit code 1 = overflow
found (or PyMuPDF unavailable / PDF missing) -> CI should fail.
"""
import sys
import os

DEFAULT_PDF = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "NRMO_Integrated_System_v7_3.pdf",
)

# Points of tolerance before a span counts as "overflowing." Font
# ascent/descent metrics routinely extend a fraction of a point past
# the nominal box even on a correctly laid-out page; anything above
# this is a real, visually-checkable layout defect.
TOLERANCE_PT = 0.5

# Pages explicitly reviewed and accepted as intentional exceptions
# (e.g. deliberate printer's marks or bleed). Empty by design -- add
# an entry here only after a human visually confirms the page is fine,
# never to silence an unreviewed finding.
ALLOWLIST_PAGES = set()


def main():
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("[V7.3 PDF PAGE-BOUNDS GUARD]")
        print("FAIL: PyMuPDF (pymupdf) not installed; cannot scan PDF.")
        print("      pip install pymupdf")
        return 1

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    print("[V7.3 PDF PAGE-BOUNDS GUARD]")

    if not os.path.isfile(pdf_path):
        print(f"FAIL: PDF not found at {pdf_path}")
        return 1

    doc = fitz.open(pdf_path)
    findings = []

    for pno in range(len(doc)):
        page_num = pno + 1
        if page_num in ALLOWLIST_PAGES:
            continue
        page = doc[pno]
        mb = page.mediabox
        left, top, right, bottom = mb.x0, mb.y0, mb.x1, mb.y1

        d = page.get_text("dict")
        for block in d.get("blocks", []):
            if block.get("type") != 0:  # text blocks only; skip images
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    x0, y0, x1, y1 = span["bbox"]
                    over_left = left - x0
                    over_top = top - y0
                    over_right = x1 - right
                    over_bottom = y1 - bottom
                    max_over = max(over_left, over_top, over_right, over_bottom)
                    if max_over > TOLERANCE_PT:
                        edge = (
                            "right" if over_right == max_over else
                            "bottom" if over_bottom == max_over else
                            "left" if over_left == max_over else
                            "top"
                        )
                        findings.append({
                            "page": page_num,
                            "edge": edge,
                            "overflow_pt": round(max_over, 2),
                            "text": text[:60],
                        })

    total_pages = len(doc)
    doc.close()

    if not findings:
        print(f"OK: {total_pages} pages scanned; no page-boundary overflow found "
              f"(tolerance {TOLERANCE_PT}pt).")
        return 0

    pages = sorted(set(f["page"] for f in findings))
    print(f"FAIL: page-boundary overflow found on {len(pages)} page(s): {pages}")
    for f in findings[:40]:
        print(f"  page {f['page']}: {f['edge']} overflow {f['overflow_pt']}pt "
              f"-- {f['text']!r}")
    if len(findings) > 40:
        print(f"  ... and {len(findings) - 40} more findings")
    return 1


if __name__ == "__main__":
    sys.exit(main())
