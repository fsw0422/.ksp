"""Show each Git checkout in a VS Code workspace once: as its own folder, never inside the workspace's root.

A .code-workspace file can list its own folder as a root, with "path": ".", to show the files beside
the checkouts. That root would show every checkout in it as well. So every checkout in that folder is
listed as its own folder, and the root's .vscode/settings.json hides the listed folders, so VS Code
neither shows nor watches them twice. The root then shows only the loose files and other folders.
A folder with no .code-workspace file gets one set up that way.
"""
import tempfile
from pathlib import Path

from checkouts import git_succeeds
from workspace import WorkspaceError, add_folder, listed_folders, read_json, workspace_files, write_json

GLOB_CHARACTERS = set('*?[]{}')
# Each setting, and the key that hides a folder in it.
SETTINGS = (('files.exclude', '{}'), ('files.watcherExclude', '{}/**'))


def show_checkouts_once(main, ahead=None):
    """Tidy each workspace beside the main checkout: list its folder's checkouts, then hide them in its roots.

    ahead is a folder about to be created. It's hidden already, so it never shows in a root.
    Print what changed. Return False if a file couldn't be updated.
    """
    ok = True
    for line in _create_workspace(main.parent):
        print(line)
    for file in _workspaces(main):
        try:
            for line in _list_checkouts(file) + _hide_listed(file, ahead):
                print(line)
        except WorkspaceError as error:
            print(error)
            ok = False
    return ok


def _create_workspace(folder):
    """Create <folder>.code-workspace with the folder as its root, when the folder has no workspace file.

    Never in the home folder, a temporary folder or the file system's root, whose roots would show far
    too much, nor inside a checkout, where the file would become an untracked file of that repository.
    """
    never = {Path.home().resolve(), Path(tempfile.gettempdir()).resolve(), Path('/tmp').resolve(), Path('/')}
    if folder in never or any(folder.glob('*.code-workspace')) or git_succeeds(folder, 'rev-parse', '--is-inside-work-tree'):
        return []
    file = folder / f'{folder.name}.code-workspace'
    write_json(file, {'folders': [{'name': f'{folder.name} (root)', 'path': '.'}], 'settings': {}}, '\t')
    return [f'{file.name}: created, with {folder.name} as its root']


def _workspaces(main):
    """Return the workspace files beside the main checkout that list it, or list their own folder as a root."""
    found = set(workspace_files(main))
    for file in main.parent.glob('*.code-workspace'):
        try:
            if file.parent.resolve() in listed_folders(file):
                found.add(file)
        except WorkspaceError:
            pass  # reported when the file lists the main checkout
    return sorted(found)


def _listed(file):
    try:
        return listed_folders(file)
    except WorkspaceError as error:
        raise WorkspaceError(f'{file.name}: {error}') from None


def _list_checkouts(file):
    """In a workspace that lists its own folder as a root, list every checkout in that folder."""
    folders = _listed(file)
    home = file.parent.resolve()
    if home not in folders:
        return []
    found = sorted(child.resolve() for child in home.iterdir()
                   if child.is_dir() and (child / '.git').exists() and child.resolve() not in folders)
    for child in found:
        add_folder(file, child)
    return [f'{file.name}: lists {", ".join(child.name for child in found)}'] if found else []


def _hide_listed(file, ahead):
    folders = _listed(file)
    lines = []
    for outer in _outer_roots(folders):
        inner = {folder.relative_to(outer).as_posix() for folder in folders if outer in folder.parents}
        if ahead and outer in ahead.parents:
            inner.add(ahead.relative_to(outer).as_posix())
        lines += _update(outer / '.vscode' / 'settings.json', outer, sorted(inner))
    return lines


def _outer_roots(folders):
    """Return the roots that hold other listed folders, or keep settings for them, and aren't checkouts.

    A root that's a checkout is left alone, so a repository's own settings never change.
    """
    return [outer for outer in folders
            if (any(outer in folder.parents for folder in folders) or (outer / '.vscode' / 'settings.json').is_file())
            and not git_succeeds(outer, 'rev-parse', '--is-inside-work-tree')]


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


def _insert_sorted(patterns, key):
    """Return the patterns with the key added, hidden, before the first key that sorts after it."""
    items = list(patterns.items())
    index = next((i for i, (each, _) in enumerate(items) if each > key), len(items))
    items.insert(index, (key, True))
    return dict(items)
