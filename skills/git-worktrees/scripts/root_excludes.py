"""Hide a workspace's listed folders inside a root that holds them, so VS Code shows each folder once.

A .code-workspace file can list its own folder as a root, with "path": ".", to show the files beside
the checkouts. That root would show every listed checkout a second time. So the root's
.vscode/settings.json hides exactly the checkouts the workspace lists, and VS Code doesn't watch
them twice.
"""
from checkouts import git_succeeds
from workspace import WorkspaceError, listed_folders, read_json, workspace_files, write_json

GLOB_CHARACTERS = set('*?[]{}')
# Each setting, and the key that hides a folder in it.
SETTINGS = (('files.exclude', '{}'), ('files.watcherExclude', '{}/**'))


def hide_listed_folders(main):
    """Update each root that holds listed folders, in each workspace that lists the main checkout.

    Print what changed. Return False if a file couldn't be updated.
    """
    ok = True
    for file in workspace_files(main):
        try:
            for line in _sync(file):
                print(line)
        except WorkspaceError as error:
            print(error)
            ok = False
    return ok


def _sync(file):
    folders = listed_folders(file)
    lines = []
    for outer in folders:
        inner = sorted(folder.relative_to(outer).as_posix() for folder in folders if outer in folder.parents)
        settings = outer / '.vscode' / 'settings.json'
        if not (inner or settings.is_file()) or _is_checkout(outer):
            continue  # never change a repository's own settings
        lines += _update(settings, outer, inner)
    return lines


def _update(settings, outer, inner):
    """Make the settings hide exactly the inner folders among the entries this script looks after."""
    label = f'{outer.name}/.vscode/settings.json'
    try:
        data, indent = read_json(settings) if settings.is_file() else ({}, '\t')
    except WorkspaceError as error:
        raise WorkspaceError(f'{label}: {error}') from None
    hidden, shown = set(), set()
    for setting, key_format in SETTINGS:
        patterns = data.get(setting, {})
        if not isinstance(patterns, dict):
            raise WorkspaceError(f'{label}: its {setting} is not an object, so update it by hand')
        for name in [name for name in _folder_keys(patterns, key_format) if name not in inner]:
            if _looked_after(outer, name):
                del patterns[key_format.format(name)]
                shown.add(name)
        for name in inner:
            if key_format.format(name) not in patterns:
                patterns = _insert_sorted(patterns, key_format.format(name))
                hidden.add(name)
        data[setting] = patterns
    if not hidden and not shown:
        return []
    settings.parent.mkdir(exist_ok=True)
    write_json(settings, data, indent)
    return ([f'{label}: hides {", ".join(sorted(hidden))}'] if hidden else []) + \
           ([f'{label}: no longer hides {", ".join(sorted(shown))}'] if shown else [])


def _folder_keys(patterns, key_format):
    """Return the folder each key names, such as app for app/** in files.watcherExclude."""
    prefix, suffix = key_format.split('{}')
    return [key[len(prefix):len(key) - len(suffix)] for key in patterns
            if key.startswith(prefix) and key.endswith(suffix)]


def _looked_after(outer, name):
    """Return True for a key this script manages: a plain path that names a checkout, or nothing anymore.

    Patterns with glob characters, and folders that aren't checkouts, such as .idea, belong to the user.
    """
    if GLOB_CHARACTERS & set(name) or not name:
        return False
    path = outer / name
    return (path / '.git').exists() or not path.exists()


def _is_checkout(folder):
    return git_succeeds(folder, 'rev-parse', '--is-inside-work-tree')


def _insert_sorted(patterns, key):
    """Return the patterns with the key added, hidden, before the first key that sorts after it."""
    items = list(patterns.items())
    index = next((i for i, (each, _) in enumerate(items) if each > key), len(items))
    items.insert(index, (key, True))
    return dict(items)
