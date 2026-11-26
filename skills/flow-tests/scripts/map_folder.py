"""The map folder: every flow the map has seen, in flows.json, each with a copy of its pictures."""
import json
import shutil

SCREENS = 'screens'


def load(folder):
    file = folder / 'flows.json'
    return json.loads(file.read_text(encoding='utf-8')) if file.is_file() else {'flows': {}}


def save(folder, saved):
    (folder / 'flows.json').write_text(json.dumps(saved, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def take_in(folder, saved, run, every):
    """Put the run's flows among the saved ones, with their pictures. Return the titles of what changed.

    With `every`, the run walked every flow there is, so a saved flow that it didn't walk is gone.
    """
    known = set(saved['flows'])
    gone = []
    for name in sorted(known - set(run)) if every else []:
        gone.append(saved['flows'].pop(name)['title'])
        shutil.rmtree(pictures_of(folder, name), ignore_errors=True)
    for name, flow in run.items():
        saved['flows'][name] = {**flow, 'steps': keep_pictures(folder, name, flow['steps'])}
    titles = {name: flow['title'] for name, flow in run.items()}
    return {'new': [titles[name] for name in sorted(set(run) - known)],
            'again': [titles[name] for name in sorted(set(run) & known)], 'gone': gone}


def keep_pictures(folder, name, steps):
    """Copy the flow's pictures into the map folder, in place of the ones from its earlier run."""
    screens = pictures_of(folder, name)
    shutil.rmtree(screens, ignore_errors=True)
    screens.mkdir(parents=True)
    kept = []
    for step in steps:
        shutil.copy2(step['picture'], screens / step['picture'].name)
        kept.append({'name': step['name'], 'picture': f'{SCREENS}/{name}/{step["picture"].name}'})
    return kept


def pictures_of(folder, name):
    """The flow's own folder of pictures. A name that would leave the map folder is refused."""
    if name in ('', '.', '..') or '/' in name or '\\' in name:
        raise ValueError(f'{name!r} is not a flow name.')
    return folder / SCREENS / name
