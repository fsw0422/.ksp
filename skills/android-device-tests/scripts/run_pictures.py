"""Read the flows a test run left behind: one folder of numbered step pictures for each flow."""
import json
import re
from datetime import datetime

STEP_PICTURE = re.compile(r'^(\d+)-(.+)\.png$')
RULE_IN_FILE_NAME = re.compile(r'^([a-z][a-z0-9]*)-(\d{3,})-(.+)$')


def read_run(pictures):
    """The run's flows, by folder name. A folder with no step pictures isn't a flow."""
    flows = {folder.name: read_flow(folder) for folder in sorted(pictures.iterdir()) if folder.is_dir()}
    return {name: flow for name, flow in flows.items() if flow}


def read_flow(folder):
    told = told_by(folder)
    steps = steps_told(folder, told) or steps_by_file_name(folder)
    if not steps:
        return None
    newest = max(step['picture'].stat().st_mtime for step in steps)
    return {'title': told.get('title') or title_from(folder.name), 'outcome': told.get('outcome'),
            'walked': datetime.fromtimestamp(newest).strftime('%Y-%m-%d %H:%M'), 'steps': steps}


def told_by(folder):
    """What the flow's own flow.json says: its title, its outcome, and its steps' exact names."""
    file = folder / 'flow.json'
    return json.loads(file.read_text(encoding='utf-8')) if file.is_file() else {}


def steps_told(folder, told):
    """The steps that flow.json names, as far as their pictures are there."""
    return [{'name': step['name'], 'picture': shown(folder / step['picture'])}
            for step in told.get('steps', []) if (folder / step['picture']).is_file()]


def steps_by_file_name(folder):
    """The steps in the order of their numbers, each named after its file."""
    found = []
    for file in folder.iterdir():
        match = STEP_PICTURE.match(file.name)
        if match:
            found.append((int(match[1]), file.name, file, match[2]))
    return [{'name': name_from(words), 'picture': shown(file)} for _, _, file, words in sorted(found)]


def shown(picture):
    """The step's clip when it has one, because the map shows what moves. Its still picture otherwise."""
    clip = picture.with_suffix('.gif')
    return clip if clip.is_file() else picture


def name_from(words):
    """`ident-002-the-email-screen` becomes `IDENT-002: the email screen`, and `welcome` becomes `Welcome`."""
    rule = RULE_IN_FILE_NAME.match(words)
    if rule:
        return f'{rule[1].upper()}-{rule[2]}: {rule[3].replace("-", " ")}'
    return capitalized(words.replace('-', ' '))


def title_from(folder_name):
    """`test-sign-up` becomes `Sign up`."""
    words = folder_name[5:] if folder_name.startswith('test-') else folder_name
    return capitalized(words.replace('-', ' '))


def capitalized(text):
    return text[:1].upper() + text[1:]
