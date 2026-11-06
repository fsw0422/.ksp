"""Render a Mermaid diagram to a PNG image, offline.

Usage: python3 -I render.py diagram.mmd diagram.png

The bundled Mermaid copy in ../assets draws the diagram in a windowless,
throwaway copy of the browser MCP's Chrome for Testing. It uses an empty profile
and blocks network access, so it never touches the shared browser, and the
diagram never leaves this machine. Set MERMAID_IMAGE_BROWSER to use another Chromium.
"""
import html
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MERMAID_JS = Path(__file__).resolve().parent.parent / 'assets' / 'mermaid.min.js'
BROWSER_SH = Path(__file__).resolve().parents[2] / 'playwright-chromium-browser' / 'browser.sh'
PAD = 16   # white margin around the diagram, in CSS pixels
SCALE = 2  # image pixels per CSS pixel, so text stays sharp when zoomed
# Chrome for Testing lays a page out at least 500 pixels wide and leaves a window under
# about 150 pixels tall blank, so screenshot at least this big, then crop around the diagram.
MIN_WINDOW = 500

DRAW_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<script src="{mermaid_js}"></script></head><body>
<pre id="source">{source}</pre><div id="out"></div>
<script>
mermaid.initialize({{startOnLoad: false, theme: 'default', suppressErrorRendering: true,
  htmlLabels: false, flowchart: {{htmlLabels: false, useMaxWidth: false}},
  sequence: {{useMaxWidth: false}}, state: {{useMaxWidth: false}}}});
mermaid.render('diagram', document.getElementById('source').textContent)
  .then(({{svg}}) => {{ document.getElementById('out').innerHTML = svg; }})
  .catch((e) => {{ document.getElementById('out').dataset.error = String(e.message || e); }});
</script></body></html>"""

SHOT_PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html, body {{ margin: 0; background: #fff; }}
body {{ display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
svg {{ display: block; margin: {pad}px; }}
</style></head><body>{svg}</body></html>"""


def find_browser():
    """Return the browser program the browser MCP uses, as its browser.sh finds it."""
    if os.environ.get('MERMAID_IMAGE_BROWSER'):
        return os.environ['MERMAID_IMAGE_BROWSER']
    found = subprocess.run(['bash', str(BROWSER_SH), 'path'], capture_output=True, text=True)
    if found.returncode != 0:
        sys.exit(found.stderr.strip() or f'{BROWSER_SH} found no browser.')
    return found.stdout.strip()


def run_browser(browser, work, *args):
    command = [browser, '--headless', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
               '--use-mock-keychain', '--no-first-run',  # no keychain prompt or first-run setup
               '--host-resolver-rules=MAP * ~NOTFOUND',  # no network access
               f'--user-data-dir={work}/profile', *args]
    return subprocess.run(command, capture_output=True, text=True, timeout=90)


def draw_svg(browser, work, source):
    """Let Mermaid draw the diagram, and return its SVG."""
    page = Path(work, 'draw.html')
    page.write_text(DRAW_PAGE.format(mermaid_js=MERMAID_JS.as_uri(), source=html.escape(source)))
    dom = run_browser(browser, work, '--virtual-time-budget=15000', '--dump-dom', page.as_uri()).stdout
    error = re.search(r'data-error="([^"]*)"', dom)
    if error:
        sys.exit('Mermaid found a syntax error:\n' + html.unescape(error.group(1)))
    svg = re.search(r'<div id="out">(<svg[\s\S]*</svg>)</div>', dom)
    if not svg:
        sys.exit('No diagram was drawn: the browser stopped before Mermaid finished.')
    return svg.group(1)


def svg_size(svg):
    """Return the diagram's width and height in CSS pixels, from its viewBox."""
    box = re.search(r'viewBox="([^"]+)"', svg).group(1)
    _, _, width, height = (float(n) for n in box.replace(',', ' ').split())
    return math.ceil(width), math.ceil(height)


def save_png(browser, work, svg, png):
    """Screenshot the SVG, centered on a white page, then crop the image around it."""
    width, height = (n + 2 * PAD for n in svg_size(svg))
    page = Path(work, 'shot.html')
    page.write_text(SHOT_PAGE.format(pad=PAD, svg=svg))
    window = f'{max(width, MIN_WINDOW)},{max(height, MIN_WINDOW)}'
    run_browser(browser, work, f'--force-device-scale-factor={SCALE}', f'--window-size={window}',
                f'--screenshot={png}', page.as_uri())
    if not png.exists():
        sys.exit('The browser did not save the image.')
    sips('--cropToHeightWidth', height * SCALE, width * SCALE, png, '--out', png)  # crops the center
    if is_blank(png, work):
        png.unlink()
        sys.exit('The image came out blank.')
    return f'{width}x{height}'


def sips(*args):
    """Run macOS's built-in image tool."""
    subprocess.run(['sips', *map(str, args)], capture_output=True, check=True)


def is_blank(png, work):
    """True when no pixel is dark. A drawn diagram always has dark text or lines."""
    bmp = Path(work, 'check.bmp')
    sips('-s', 'format', 'bmp', png, '--out', bmp)
    data = bmp.read_bytes()
    start = int.from_bytes(data[10:14], 'little')
    width = int.from_bytes(data[18:22], 'little', signed=True)
    height = abs(int.from_bytes(data[22:26], 'little', signed=True))
    pixel_bytes = width * int.from_bytes(data[28:30], 'little') // 8
    row = (pixel_bytes + 3) // 4 * 4  # BMP pads each row to a multiple of 4 bytes
    return all(min(data[i:i + pixel_bytes]) > 200 for i in range(start, start + row * height, row))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    source = Path(sys.argv[1]).read_text()
    png = Path(sys.argv[2]).resolve()
    png.unlink(missing_ok=True)
    browser = find_browser()
    with tempfile.TemporaryDirectory() as work:
        size = save_png(browser, work, draw_svg(browser, work, source), png)
    print(f'{png}: {size} CSS pixels, saved at {SCALE}x')


if __name__ == '__main__':
    main()
