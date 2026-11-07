"""Keep VS Code's .code-workspace files in step with the worktrees."""
import json
import os


class WorkspaceError(Exception):
    """A workspace file this script can't update safely."""


def workspace_files(main):
    """Return the .code-workspace files beside the main checkout that list it."""
    return [file for file in sorted(main.parent.glob('*.code-workspace')) if _lists(file, main)]


def add_folder(file, folder):
    """Add the folder to the file's folders, in sorted place. Return what happened."""
    data, indent = _load(file)
    folders = data.setdefault('folders', [])
    if _index_of(folders, file, folder) is not None:
        return 'already listed'
    path = os.path.relpath(folder, file.parent)
    folders.insert(_sorted_index(folders, path), {'path': path})
    _save(file, data, indent)
    return 'added'


def remove_folder(file, folder):
    """Remove the folder from the file's folders. Return what happened."""
    data, indent = _load(file)
    folders = data.get('folders', [])
    index = _index_of(folders, file, folder)
    if index is None:
        return 'not listed'
    del folders[index]
    _save(file, data, indent)
    return 'removed'


def _lists(file, main):
    try:
        data, _ = _load(file)
    except WorkspaceError:
        # Report a file this script can't read when it may list the checkout.
        return main.name in file.read_text()
    return _index_of(data.get('folders', []), file, main) is not None


def _load(file):
    text = file.read_text()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise WorkspaceError('has comments or trailing commas, so update it by hand') from None
    if not isinstance(data, dict) or not isinstance(data.get('folders', []), list):
        raise WorkspaceError('has no folders list, so update it by hand')
    return data, _indent(text)


def _save(file, data, indent):
    file.write_text(json.dumps(data, indent=indent, ensure_ascii=False) + '\n')


def _indent(text):
    """Return the file's indentation: a tab, or its number of spaces. VS Code uses a tab."""
    for line in text.splitlines():
        content = line.lstrip(' \t')
        if content and content != line:
            return '\t' if line.startswith('\t') else len(line) - len(content)
    return '\t'


def _path_of(entry):
    path = entry.get('path') if isinstance(entry, dict) else None
    return path if isinstance(path, str) else None


def _index_of(folders, file, folder):
    for index, entry in enumerate(folders):
        path = _path_of(entry)
        if path is not None and (file.parent / path).resolve() == folder:
            return index
    return None


def _sorted_index(folders, path):
    """Return where the path goes so the entries with a path stay sorted."""
    return next((i for i, entry in enumerate(folders) if (_path_of(entry) or '') > path), len(folders))
