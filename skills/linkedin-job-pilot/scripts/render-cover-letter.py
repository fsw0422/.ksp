#!/usr/bin/env python3
"""Render a drafted cover letter to a one-page PDF with headless Google Chrome.

Usage:
  render-cover-letter.py --letter letter.txt --name "Full Name" --contact "email · phone · city" \
      --out path/to/Cover-Letter.pdf [--title TEXT] [--date TEXT] [--paper a4|letter] [--chrome PATH] \
      [--preview path/to/preview.png] [--verify-only]

The letter file holds the exact drafted text. Blank lines separate paragraphs.
Writes the PDF atomically, then verifies it and prints one line:
  <pdf path> pages=1 sha256=<hex> text_match=yes header_match=yes
Exits 1 if rendering fails, 2 if the PDF is not exactly one page, and 3 if the
PDF text does not match the letter or the header. --verify-only skips rendering
and verifies an existing PDF. --preview writes a PNG of the page (needs pdftoppm).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

CHROME_MAC = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title><style>
@page {{ size: {paper}; margin: 22mm; }}
body {{ font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #111; }}
.name {{ font-size: 18pt; font-weight: 600; margin: 0; }}
.contact {{ color: #444; margin: 2pt 0 18pt; }}
.date {{ margin: 0 0 14pt; }}
p {{ margin: 0 0 10pt; }}
</style></head><body>
<p class="name">{name}</p>
<p class="contact">{contact}</p>
{date}
{body}
</body></html>
"""


def to_paragraphs(text: str) -> str:
    blocks = text.replace("\r\n", "\n").strip().split("\n\n")
    return "\n".join(
        "<p>" + "<br>".join(html.escape(line) for line in block.strip("\n").split("\n")) + "</p>"
        for block in blocks
        if block.strip()
    )


def count_pages(pdf: pathlib.Path) -> int:
    if shutil.which("pdfinfo"):
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        match = re.search(r"^Pages:\s+(\d+)", info, re.M)
        if match:
            return int(match.group(1))
    return len(re.findall(rb"/Type\s*/Page(?!s)", pdf.read_bytes()))


def normalize(text: str) -> str:
    text = text.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", text).strip()


def pdf_text(pdf: pathlib.Path) -> str | None:
    if not shutil.which("pdftotext"):
        return None
    return subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout


def verify(pdf: pathlib.Path, letter: str, name: str, contact: str, preview: str | None) -> int:
    pages = count_pages(pdf)
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    extracted = pdf_text(pdf)
    if extracted is None:
        text_ok = header_ok = "unknown"
    else:
        got, want = normalize(extracted), normalize(letter)
        # Line wrapping can split a hyphenated word ("data-" / "residency"); pdftotext then drops the hyphen.
        text_ok = "yes" if want in got or want.replace("-", "") in got.replace("-", "") else "no"
        header_ok = "yes" if got.startswith(normalize(f"{name} {contact}")) else "no"
    if preview and shutil.which("pdftoppm"):
        target = pathlib.Path(preview).expanduser().resolve()
        subprocess.run(["pdftoppm", "-png", "-r", "60", "-singlefile", str(pdf), str(target.with_suffix(""))], check=False)
    print(f"{pdf} pages={pages} sha256={digest} text_match={text_ok} header_match={header_ok}")
    if pages != 1:
        return 2
    return 3 if "no" in (text_ok, header_ok) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--letter", required=True, help="Text file with the exact drafted letter.")
    parser.add_argument("--name", required=True, help="Applicant name, as it appears on the resume.")
    parser.add_argument("--contact", required=True, help="One contact line taken from the resume.")
    parser.add_argument("--out", required=True, help="Target PDF path.")
    parser.add_argument("--title", default="Cover letter", help="PDF document title.")
    parser.add_argument("--date", default="", help="Optional date line.")
    parser.add_argument("--paper", choices=["a4", "letter"], default="a4")
    parser.add_argument("--chrome", default=os.environ.get("CHROME_PATH") or CHROME_MAC)
    parser.add_argument("--preview", help="Optional PNG preview path.")
    parser.add_argument("--verify-only", action="store_true", help="Verify an existing PDF without rendering.")
    args = parser.parse_args()

    out = pathlib.Path(args.out).expanduser().resolve()
    letter = pathlib.Path(args.letter).expanduser().read_text(encoding="utf-8")
    if args.verify_only:
        return verify(out, letter, args.name, args.contact, args.preview)
    staged = out.with_name(out.name + ".tmp")
    page_html = PAGE.format(
        title=html.escape(args.title),
        paper="A4" if args.paper == "a4" else "letter",
        name=html.escape(args.name),
        contact=html.escape(args.contact),
        date=f'<p class="date">{html.escape(args.date)}</p>' if args.date else "",
        body=to_paragraphs(letter),
    )

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="cover-letter-"))
    try:
        source = tmp / "letter.html"
        source.write_text(page_html, encoding="utf-8")
        command = [
            args.chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--use-mock-keychain",
            "--password-store=basic",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-sync",
            f"--user-data-dir={tmp / 'profile'}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={staged}",
            source.as_uri(),
        ]
        if not render(command, staged, tmp / "chrome.log"):
            log = (tmp / "chrome.log").read_text(errors="replace").strip()[-2000:]
            print(f"Chrome could not render the PDF.\n{log}", file=sys.stderr)
            return 1

        pages = count_pages(staged)
        if pages != 1:
            print(f"The letter renders to {pages} pages; shorten it to fit one page.", file=sys.stderr)
            return 2

        os.replace(staged, out)
        return verify(out, letter, args.name, args.contact, args.preview)
    finally:
        staged.unlink(missing_ok=True)
        shutil.rmtree(tmp, ignore_errors=True)


def pdf_complete(pdf: pathlib.Path) -> bool:
    if not pdf.exists() or pdf.stat().st_size == 0:
        return False
    with pdf.open("rb") as handle:
        handle.seek(max(0, pdf.stat().st_size - 1024))
        return handle.read().rstrip().endswith(b"%%EOF")


def render(command: list[str], staged: pathlib.Path, log: pathlib.Path, limit: float = 60) -> bool:
    """Headless Chrome can keep running after it prints, so wait for a complete PDF instead of exit."""
    with log.open("w") as log_handle:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=log_handle)
        deadline = time.monotonic() + limit
        last_size = -1
        try:
            while time.monotonic() < deadline and process.poll() is None:
                size = staged.stat().st_size if staged.exists() else -1
                if size > 0 and size == last_size and pdf_complete(staged):
                    break
                last_size = size
                time.sleep(0.5)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    return pdf_complete(staged)


if __name__ == "__main__":
    sys.exit(main())
