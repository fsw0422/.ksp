"""List every Git checkout in an IntelliJ workspace's folder as a subproject, as VS Code's root lists them.

A folder with no .idea at all gets an IntelliJ multi-project workspace set up. IntelliJ watches
jb-workspace.xml, so new entries show up at once. It loads them at its next start, or at once with
Load Project.
"""
from intellij_workspace import add_subproject, create_workspace, intellij_workspaces, listed_subprojects, workspace_name
from root_excludes import may_set_up
from workspace import WorkspaceError

LOAD_HINT = ". IntelliJ loads them at its next start, or right away with Load Project on each in its Project view."


def list_every_checkout(main):
    """Create the workspace beside the main checkout when the folder has none, then list its checkouts.

    Print what changed. Return False if the workspace couldn't be updated.
    """
    folder = main.parent
    if not (folder / '.idea').exists() and may_set_up(folder):
        print(f'{workspace_name(create_workspace(folder))}: created')
    ok = True
    for file in intellij_workspaces(main):
        try:
            listed = listed_subprojects(file)
            found = sorted(child.resolve() for child in folder.iterdir()
                           if child.is_dir() and (child / '.git').exists() and child.resolve() not in listed)
            for child in found:
                add_subproject(file, child)
            if found:
                print(f'{workspace_name(file)}: lists {", ".join(child.name for child in found)}{LOAD_HINT}')
        except WorkspaceError as error:
            print(f'{workspace_name(file)}: {error}')
            ok = False
    return ok
