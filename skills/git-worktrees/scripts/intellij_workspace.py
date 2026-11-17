"""Keep IntelliJ's multi-project workspace in step with the worktrees.

A workspace is a folder whose .idea/jb-workspace.xml lists its subprojects. IntelliJ watches that
file, so an entry added here shows up in its Project view at once. IntelliJ loads the subproject's
modules and build at its next start, or at once with Load Project.
"""
import copy
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from checkouts import git_try
from workspace import WorkspaceError

HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n'
# Where IntelliJ links a loaded subproject's build: (file, elements, attribute) whose value is in its folder.
# Its modules, listed in modules.xml, are checked by _loads_modules.
BUILD_LINKS = (
    ('gradle.xml', ".//option[@name='externalProjectPath']", 'value'),  # its Gradle build
    ('misc.xml', ".//component[@name='MavenProjectsManager']//option", 'value'),  # its Maven build
)


def intellij_workspaces(main):
    """Return the IntelliJ workspace file beside the main checkout, in a list, if it's a workspace or lists it."""
    file = workspace_file(main.parent)
    if not file.is_file():
        return []
    try:
        root, _ = _load(file)
    except WorkspaceError:
        # Report a file this script can't update when it may list the checkout.
        return [file] if main.name in file.read_text(encoding='utf-8') else []
    is_workspace = _settings(root).find("option[@name='workspace']")
    return [file] if _entries(root, file, main) or (is_workspace is not None and is_workspace.get('value') == 'true') else []


def workspace_file(folder):
    return folder / '.idea' / 'jb-workspace.xml'


def create_workspace(folder):
    """Make the folder an IntelliJ multi-project workspace with no subprojects yet. Return its file."""
    root = ET.Element('project', version='4')
    settings = ET.SubElement(root, 'component', name='WorkspaceSettings')
    ET.SubElement(settings, 'option', name='workspace', value='true')
    file = workspace_file(folder)
    file.parent.mkdir()
    file.write_text(_serialize(root), encoding='utf-8')
    return file


def listed_subprojects(file):
    """Return the folders the workspace lists, as paths."""
    root, _ = _load(file)
    return [_resolve(file, entry.get('path')) for entry in _settings(root).findall('project') if entry.get('path')]


def workspace_name(file):
    """Name the workspace by its folder, such as `projects IntelliJ workspace`."""
    return f'{file.parent.parent.name} IntelliJ workspace'


def add_subproject(file, folder, main=None):
    """List the folder as a subproject, with its Git remote. Return what happened.

    The remote comes from the main checkout's entry when there is one, or else from the folder's origin.
    """
    root, newline = _load(file)
    if _entries(root, file, folder):
        return 'already listed'
    settings = _settings(root)
    entry = ET.Element('project', name=folder.name, path=_stored(file, folder))
    main_entry = next(iter(_entries(root, file, main)), None) if main else None
    if main_entry is not None:
        entry.extend(copy.deepcopy(child) for child in main_entry)
    elif remote := git_try(folder, 'remote', 'get-url', 'origin'):
        ET.SubElement(entry, 'vcs', id='Git', remoteUrl=remote)
    projects = settings.findall('project')
    settings.insert(list(settings).index(projects[-1]) + 1 if projects else 0, entry)
    _save(file, root, newline)
    return 'added'


def remove_subproject(file, folder):
    """Take every entry for the folder out of the workspace. Return what happened."""
    root, newline = _load(file)
    entries = _entries(root, file, folder)
    if not entries:
        return 'not listed'
    settings = _settings(root)
    for entry in entries:
        settings.remove(entry)
    _save(file, root, newline)
    return 'removed'


def listed_name(file, folder):
    """Return the name IntelliJ shows for the folder: its entry's name, or else the folder's."""
    try:
        entries = _entries(_load(file)[0], file, folder)
    except WorkspaceError:
        entries = []
    return entries[0].get('name') if entries else folder.name


def loaded_links(file, folder):
    """Return the files where IntelliJ still links the folder's build or modules, such as gradle.xml."""
    found = []
    for name, elements, attribute in BUILD_LINKS:
        values = _values(file.parent / name, elements, attribute)
        if values is None or any(value and _inside(_resolve(file, value), folder) for value in values):
            found.append(name)  # an unreadable file counts, to be safe
    if _loads_modules(file, folder):
        found.append('modules.xml')
    return found


def _loads_modules(file, folder):
    """Return True if modules.xml lists a module of the folder: its module file or a content root is in it.

    A module file can sit in the folder, such as app/.idea/app.iml, or in the workspace's own
    .idea, such as .idea/docs.iml, whose content root is then the folder.
    """
    filepaths = _values(file.parent / 'modules.xml', './/module', 'filepath')
    if filepaths is None:
        return True  # unreadable, so assume it does
    for module in (_resolve(file, value) for value in filepaths if value):
        if _inside(module, folder) or any(_inside(root, folder) for root in _content_roots(file, module)):
            return True
    return False


def _content_roots(file, module):
    """Return the module's content roots. $MODULE_DIR$ is the module file's folder, or the workspace's for one in .idea."""
    urls = _values(module, './/content', 'url') or []
    return [_resolve(file, url.replace('$MODULE_DIR$', str(base)))
            for url in urls if url for base in (module.parent, file.parent.parent)]


def _values(path, elements, attribute):
    """Return the attribute of each matching element in the XML file: [] with no file, None if it's unreadable."""
    if not path.is_file():
        return []
    try:
        return [element.get(attribute) for element in ET.parse(path).iterfind(elements)]
    except ET.ParseError:
        return None


def _load(file):
    """Read the file. Refuse one that writing back would change, so only the entry ever changes."""
    text = file.read_text(encoding='utf-8')
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise WorkspaceError("isn't valid XML, so update it by hand") from None
    if _serialize(root) != text.rstrip('\n'):
        raise WorkspaceError("isn't laid out the way IntelliJ writes it, so update it by hand")
    _settings(root)
    return root, text.endswith('\n')


def _save(file, root, newline):
    """Replace the file in one step, because IntelliJ reloads it as soon as it changes."""
    fd, temporary = tempfile.mkstemp(dir=file.parent, prefix=f'.{file.name}.')
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        out.write(_serialize(root) + ('\n' if newline else ''))
    os.chmod(temporary, file.stat().st_mode & 0o777)
    os.replace(temporary, file)


def _serialize(root):
    ET.indent(root, space='  ')
    return HEADER + ET.tostring(root, encoding='unicode')


def _settings(root):
    settings = root.find("component[@name='WorkspaceSettings']")
    if settings is None:
        raise WorkspaceError('has no list of subprojects, so update it by hand')
    return settings


def _entries(root, file, folder):
    return [entry for entry in _settings(root).findall('project')
            if entry.get('path') and _resolve(file, entry.get('path')) == folder]


def _stored(file, folder):
    """Return the folder as IntelliJ stores it, such as $PROJECT_DIR$/app-feature."""
    return '$PROJECT_DIR$/' + Path(os.path.relpath(folder, file.parent.parent)).as_posix()


def _resolve(file, stored):
    """Return the path a stored value names, such as file://$PROJECT_DIR$/app/.idea/app.iml."""
    path = stored.removeprefix('file://').replace('$PROJECT_DIR$', str(file.parent.parent))
    return Path(os.path.normpath(path.replace('$USER_HOME$', str(Path.home()))))


def _inside(path, folder):
    return path == folder or folder in path.parents
