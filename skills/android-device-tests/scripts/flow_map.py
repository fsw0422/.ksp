"""Draw one map of the flows that device tests walked: each screen once, with an arrow to each next one.

  python3 flow_map.py <pictures folder> <map folder> [--title <title>] [--all]

The pictures folder is where a test run left its step pictures, in one folder for each flow. The map
folder keeps every flow the map has seen, so a later run adds to the map, or replaces what it walked again.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so `python3 -I` finds the modules beside this file

from map_folder import load, save, take_in  # noqa: E402
from map_page import counted, draw  # noqa: E402
from run_pictures import read_run  # noqa: E402
from screen_tree import each, join, place  # noqa: E402


def update(pictures, folder, title, every):
    if not pictures.is_dir():
        sys.exit(f'{pictures} is not a folder.')
    run = read_run(pictures)
    if not run:
        sys.exit(f'{pictures} holds no flow, so the map is unchanged. '
                 'A flow is a folder of step pictures named like 01-welcome.png.')
    folder.mkdir(parents=True, exist_ok=True)
    saved = load(folder)
    saved['title'] = title or saved.get('title') or 'Flow Map'
    changed = take_in(folder, saved, run, every)
    save(folder, saved)
    by_title = sorted(saved['flows'].items(), key=lambda named: (named[1]['title'].lower(), named[0]))
    flows = [flow for _, flow in by_title]
    starts = join(flows)
    (folder / 'index.html').write_text(draw(saved['title'], flows, starts, place(starts)), encoding='utf-8')
    screens = list(each(starts))
    shown = sorted({picture for screen in screens for picture in screen.own.values()})
    (folder / 'pictures.json').write_text(json.dumps(shown, indent=2) + '\n', encoding='utf-8')
    report(folder, saved['flows'], len(screens), shown, changed)


def report(folder, flows, screens, shown, changed):
    print(f'Flow map: {counted(len(flows), "flow")} on {counted(screens, "screen")}, in {folder / "index.html"}')
    for word, titles in (('New', changed['new']), ('Walked again', changed['again']), ('Gone', changed['gone'])):
        if titles:
            print(f'{word}: {", ".join(titles)}')
    kept = len(flows) - len(changed['new']) - len(changed['again'])
    if kept:
        print(f'Kept from earlier runs: {counted(kept, "flow")}')
    print(f'The page uses {counted(len(shown), "picture")}, listed in {folder / "pictures.json"}')
    link = folder / 'link.txt'
    if link.is_file():
        print(f'Published at {link.read_text(encoding="utf-8").strip()}: update that page.')


def main():
    parser = argparse.ArgumentParser(description='Draw one map of the flows that device tests walked.')
    parser.add_argument('pictures', help='the folder where the run left its step pictures, one folder for each flow')
    parser.add_argument('map', help='the folder that keeps the map, which outlives the runs')
    parser.add_argument('--title', help="the page's title, such as 'Shop Flow Map'. The map keeps it once it is set.")
    parser.add_argument('--all', action='store_true',
                        help='the run walked every flow, so a flow that it did not walk leaves the map')
    args = parser.parse_args()
    update(Path(args.pictures).resolve(), Path(args.map).resolve(), args.title, args.all)


if __name__ == '__main__':
    main()
