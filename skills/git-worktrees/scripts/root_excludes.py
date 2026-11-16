"""Show each checkout in a VS Code workspace once: as its own folder, never inside an outer root.

A .code-workspace file can list its own folder as a root, with "path": ".", to show the files beside
the checkouts. That root would show every checkout in it as well. So every checkout directly in the
root is listed as its own folder, and the root's .vscode/settings.json hides exactly the checkouts
the workspace lists, so VS Code doesn't show or watch them twice.
"""
from checkouts import git_succeeds
from workspace import WorkspaceError, add_folder, listed_folders, read_json, workspace_files, write_json

GLOB_CHARACTERS = set('*?[]{}')
# Each setting, and the key that hides a folder in it.
SETTINGS = (('files.exclude', '{}'), ('files.watcherExclude', '{}/**'))


def hide_listed_folders(main):
    """Tidy each outer root, in each workspace that lists the main checkout: list its checkouts, then hide them.

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
    lines = _list_checkouts(file)
    folders = listed_folders(file)
    for outer in _outer_roots(folders):
        inner = sorted(folder.relative_to(outer).as_posix() for folder in folders if outer in folder.parents)
        lines += _update(outer / '.vscode' / 'settings.json', outer, inner)
    return lines


def _outer_roots(folders):
    """Return the roots that hold other listed folders, or keep settings for them, and aren't checkouts.

    A root that's a checkout is left alone, so a repository's own settings never change.
    """
    return [outer for outer in folders
            if (any(outer in folder.parents for folder in folders) or (outer / '.vscode' / 'settings.json').is_file())
            and not _is_checkout(outer)]


def _list_checkouts(file):
    """List each checkout directly in an outer root that holds listed folders, so it gets its own folder."""
    folders = listed_folders(file)
    holders = [outer for outer in _outer_roots(folders) if any(outer in folder.parents for folder in folders)]
    found = sorted({child for outer in holders for child in outer.iterdir()
                    if child.is_dir() and (child / '.git').exists() and child not in folders})
    for child in found:
        add_folder(file, child)
    return [f'{file.name}: lists {", ".join(child.name for child in found)}'] if found else []


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
