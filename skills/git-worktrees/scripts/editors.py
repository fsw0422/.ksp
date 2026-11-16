"""List a worktree in the VS Code and IntelliJ workspaces beside its main checkout, and take it out again."""
import os
import time

from cleanup import STOP
from intellij_workspace import (add_subproject, intellij_workspaces, listed_name, loaded_links,
                                remove_subproject, workspace_name)
from workspace import WorkspaceError, add_folder, remove_folder, workspace_files

LOAD_HINT = (". To load it now, right-click it in IntelliJ's Project view and choose Load Project. "
             'Otherwise IntelliJ loads it at its next start.')


def list_folder(main, folder):
    """Add the folder to each workspace that lists the main checkout. Return False if a file failed."""
    def to_intellij(file):
        outcome = add_subproject(file, folder, main)
        return outcome + LOAD_HINT if outcome == 'added' else outcome

    in_vscode = _update_vscode(main, lambda file: add_folder(file, folder))
    in_intellij = _update_intellij(main, to_intellij)
    return in_vscode and in_intellij


def intellij_stops(main, folder):
    """Return why remove must wait, or []: IntelliJ still links the folder's build or modules.

    Only IntelliJ can unlink those safely. Left behind, they point at a folder that's gone.
    """
    stops = []
    for file in intellij_workspaces(main):
        links = loaded_links(file, folder)
        if links:
            name = listed_name(file, folder)
            stops.append(f'{STOP}: IntelliJ still has {name} loaded in the {workspace_name(file)}, '
                         f'in {", ".join(links)}. Right-click it in IntelliJ\'s Project view, choose '
                         f"Remove '{name}' from Workspace, then run remove again.")
    return stops


def unlist(main, folder):
    """Take the folder out of the workspaces, then give the editors a moment to drop it.

    An editor or language server that sees the files of a folder it still lists vanish can keep
    that folder's modules in its cache, and fail on its next start. So the folder leaves them
    while its files still exist. Return False if a file failed, and a way to put back each entry.
    """
    removed = []  # (name, add the entry back)

    def from_vscode(file):
        outcome = remove_folder(file, folder)
        if outcome == 'removed':
            removed.append((file.name, lambda: add_folder(file, folder)))
        return outcome

    def from_intellij(file):
        outcome = remove_subproject(file, folder)
        if outcome == 'removed':
            removed.append((workspace_name(file), lambda: add_subproject(file, folder, main)))
        return outcome

    in_vscode = _update_vscode(main, from_vscode)
    in_intellij = _update_intellij(main, from_intellij)
    if removed:
        time.sleep(float(os.environ.get('GIT_WORKTREES_UNLIST_PAUSE', '3')))
    return in_vscode and in_intellij, removed


def _update_vscode(main, change):
    return _update(workspace_files(main), change, lambda file: file.name,
                   'VS Code: no .code-workspace file beside the main checkout lists it')


def _update_intellij(main, change):
    return _update(intellij_workspaces(main), change, workspace_name,
                   'IntelliJ: no multi-project workspace beside the main checkout lists it')


def _update(files, change, name, none_found):
    """Apply the change to each file and print what happened. Return False if one failed."""
    if not files:
        print(none_found)
    ok = True
    for file in files:
        try:
            print(f'{name(file)}: {change(file)}')
        except WorkspaceError as error:
            print(f'{name(file)}: {error}')
            ok = False
    return ok
