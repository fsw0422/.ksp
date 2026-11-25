"""Draw the map as one page: each screen at its place, with an arrow to each screen that follows it."""
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

from screen_tree import each

ASSETS = Path(__file__).resolve().parent.parent / 'assets'
WIDTH, HEIGHT = 170, 378    # a picture on the map: a phone screen, 9 wide and 20 tall
CAPTION, ENDS = 76, 58      # the room above a picture for its name, and below it for the flows that end there
COLUMN = WIDTH + 84         # from one step to the next, with room for the arrow
ROW = CAPTION + HEIGHT + ENDS + 20
RULES = re.compile(r'^((?:[A-Z][A-Z0-9]*-\d+)(?:, ?[A-Z][A-Z0-9]*-\d+)*): (.+)$', re.S)
MARKS = {'passed': '✓ ', 'failed': '✗ '}
# Claude wraps a page it publishes in a document of its own, so this page has no doctype, html, head or
# body tags. A browser opens it as it is.
PAGE = '''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<title>{title}</title>
<style>
{style}</style>
<header class="bar">
<h1>{title}</h1>
<p class="count">{count}</p>
<div class="tools">
<div class="pick">
<label for="flow">Show</label>
<select id="flow" autocomplete="off">
<option value="">All flows</option>
{options}
</select>
</div>
<div class="zoom" role="group" aria-label="Zoom">
<button id="zoom-out" type="button" aria-label="Zoom out">−</button>
<button id="zoom-in" type="button" aria-label="Zoom in">+</button>
<button id="zoom-fit" type="button">Fit</button>
<button id="zoom-full" type="button">100%</button>
</div>
</div>
</header>
<main class="board" id="board" tabindex="0" aria-label="The map. It scrolls both ways.">
<p class="hint">Flows that start with the same steps share those screens, and an arrow leaves the screen where they part. A flow's name stands under its last screen. A screen that flows share plays the clip of the flow walked last, which runs on to that flow's next screen. Pick a flow in the list to see its own clips, with what it did on each screen. Click a picture to see it larger.</p>
<div class="map" id="map" data-width="{width}" data-height="{height}" style="width:{width}px;height:{height}px">
<svg class="arrows" width="{width}" height="{height}" viewBox="0 0 {width} {height}" aria-hidden="true">
<defs>
<marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="head" d="M0 0 10 5 0 10z"/></marker>
<marker id="head-picked" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path class="head-picked" d="M0 0 10 5 0 10z"/></marker>
</defs>
{arrows}
</svg>
{screens}
</div>
</main>
<dialog id="closer" aria-labelledby="closer-name">
<div class="sheet">
<h2 id="closer-name"></h2>
<img alt="">
<p>Flows that walk through this screen:</p>
<ul></ul>
<button type="button">Close</button>
</div>
</dialog>
<script>
{script}</script>
'''


def draw(title, flows, starts, rows):
    screens = list(each(starts))
    width = (max(screen.depth for screen in screens) + 1) * COLUMN - (COLUMN - WIDTH)
    height = round(rows * ROW) - 20
    return PAGE.format(
        title=html.escape(title), count=html.escape(count_line(flows, screens)),
        style=(ASSETS / 'flow-map.css').read_text(encoding='utf-8'),
        script=(ASSETS / 'flow-map.js').read_text(encoding='utf-8'),
        options='\n'.join(option(number, flow) for number, flow in enumerate(flows)),
        width=width, height=height,
        arrows='\n'.join(arrow(screen, follower) for screen in screens for follower in screen.next.values()),
        screens='\n'.join(figure(screen, flows) for screen in screens))


def count_line(flows, screens):
    newest = max(flow['walked'] for flow in flows)
    return f'{counted(len(flows), "flow")} · {counted(len(screens), "screen")} · last walked {newest}'


def counted(number, word):
    return f'{number} {word}{"" if number == 1 else "s"}'


def label(flow):
    return html.escape(MARKS.get(flow['outcome'], '') + flow['title'])


def option(number, flow):
    return f'<option value="{number}" data-title="{html.escape(flow["title"])}">{label(flow)}</option>'


def figure(screen, flows):
    stopped = any(flows[number]['outcome'] == 'failed' for number in screen.ends)
    ends = ''.join(f'<li class="{html.escape(flows[number]["outcome"] or "")}" title="{label(flows[number])}">'
                   f'{label(flows[number])}</li>' for number in screen.ends)
    name = html.escape(screen.name)
    return (f'<figure class="screen{" stopped" if stopped else ""}" data-flows="{numbers(screen.flows)}" '
            f'data-name="{name}"{own_pictures(screen)} style="left:{left(screen)}px;top:{top(screen)}px">'
            f'<figcaption>{caption(screen.name)}</figcaption>'
            f'<button class="picture" type="button" aria-label="Show it larger: {name}">'
            f'<img src="{quote(screen.picture)}" alt="" loading="lazy" width="{WIDTH}" height="{HEIGHT}"></button>'
            f'<ul class="ends">{ends}</ul></figure>')


def own_pictures(screen):
    """For a screen that flows share: each flow's own picture of it, which the page shows once that flow is picked.

    A step's clip shows what its flow did on the screen, and two flows can do different things there.
    """
    if len(screen.own) < 2:
        return ''
    own = json.dumps({str(number): quote(picture) for number, picture in screen.own.items()})
    return f' data-own="{html.escape(own)}"'


def caption(name):
    """The step's name, with its rule's ID on a line of its own."""
    rules = RULES.match(name)
    if not rules:
        return f'<span class="name">{html.escape(name)}</span>'
    return f'<span class="rule">{html.escape(rules[1])}</span><span class="name">{html.escape(rules[2])}</span>'


def arrow(screen, follower):
    """A curve from the middle of the screen's right edge to the middle of its follower's left edge."""
    start_x, start_y = left(screen) + WIDTH, middle(screen)
    end_x, end_y = left(follower), middle(follower)
    bend = (start_x + end_x) // 2
    return (f'<path data-flows="{numbers(follower.flows)}" '
            f'd="M{start_x} {start_y}C{bend} {start_y} {bend} {end_y} {end_x} {end_y}"/>')


def numbers(flows):
    """The flows' numbers with a space around each, so a script can look for ` 12 `."""
    return ' ' + ' '.join(str(number) for number in flows) + ' '


def left(screen):
    return screen.depth * COLUMN


def top(screen):
    return round(screen.row * ROW)


def middle(screen):
    return top(screen) + CAPTION + HEIGHT // 2
