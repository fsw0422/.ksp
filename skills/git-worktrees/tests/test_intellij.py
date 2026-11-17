"""Tests for how `worktree.py add` and `remove` keep IntelliJ's multi-project workspace in step.

Run: python3 -m unittest discover -s <this skill's folder>/tests
"""
import shutil
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from helpers import commit, git, run_script, start_script

STOP = 'Stopped before removing anything'
# A workspace as IntelliJ writes it: two-space indents, and no newline at the end.
WORKSPACE = '''<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="WorkspaceSettings">
    <project name="app" path="$PROJECT_DIR$/app">
      <vcs id="Git" remoteUrl="https://github.com/test/app.git" />
    </project>
    <project name="other" path="$PROJECT_DIR$/other" />
    <option name="workspace" value="true" />
  </component>
</project>'''
FEATURE_ENTRY = '''    <project name="app-feature" path="$PROJECT_DIR$/app-feature">
      <vcs id="Git" remoteUrl="https://github.com/test/app.git" />
    </project>
'''
WITH_FEATURE = WORKSPACE.replace('    <option', FEATURE_ENTRY + '    <option')
# What IntelliJ writes once it loads app-feature: its Gradle build, its Maven build, or its modules.
LOADED = {
    'gradle.xml': '<project version="4"><component name="GradleSettings"><option name="linkedExternalProjectsSettings">'
                  '<GradleProjectSettings><option name="externalProjectPath" value="$PROJECT_DIR$/app-feature" />'
                  '</GradleProjectSettings></option></component></project>',
    'misc.xml': '<project version="4"><component name="MavenProjectsManager"><option name="originalFiles"><list>'
                '<option value="$PROJECT_DIR$/app-feature/pom.xml" /></list></option></component></project>',
    'modules.xml': '<project version="4"><component name="ProjectModuleManager"><modules>'
                   '<module fileurl="file://$PROJECT_DIR$/app-feature/.idea/app.iml" '
                   'filepath="$PROJECT_DIR$/app-feature/.idea/app.iml" /></modules></component></project>',
}


class IntellijTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.repo = self.root / 'app'
        (self.repo / '.idea' / 'shelf').mkdir(parents=True)
        git(self.repo, 'init', '-q', '-b', 'main')
        commit(self.repo, '.gitignore', '/.idea/misc.xml\n/.idea/workspace.xml\n/.idea/shelf/\n', 'Start')
        commit(self.repo, '.idea/vcs.xml', 'shared\n', 'Share the VCS settings')
        for name in ('misc.xml', 'modules.xml', 'app.iml', 'workspace.xml', '.name', 'shelf/Draft.xml'):
            (self.repo / '.idea' / name).write_text(f'{name} of the main checkout\n')
        self.idea = self.root / '.idea'
        self.idea.mkdir()
        self.workspace = self.idea / 'jb-workspace.xml'
        self.workspace.write_text(WORKSPACE)
        self.folder = self.root / 'app-feature'

    def add(self):
        result = run_script('add', self.repo, 'feature', '--from', 'main')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_add_copies_intellij_files_git_does_not_track_and_lists_the_worktree(self):
        output = self.add()
        copied = sorted(path.name for path in (self.folder / '.idea').rglob('*') if path.is_file())
        self.assertEqual(copied, ['app.iml', 'misc.xml', 'modules.xml', 'vcs.xml'])
        self.assertEqual((self.folder / '.idea' / 'misc.xml').read_text(), 'misc.xml of the main checkout\n')
        self.assertIn(f'.idea: copied 3 files from {self.repo}', output)
        self.assertEqual(git(self.folder, 'status', '--porcelain'), '')  # nothing copied can be committed
        self.assertEqual(self.workspace.read_text(), WITH_FEATURE)
        self.assertIn(f'{self.root.name} IntelliJ workspace: added. To load it now, right-click it', output)

    def test_remove_takes_the_worktree_out_of_intellij_before_deleting_it(self):
        self.add()
        # Links to other folders, and a mention outside a link, don't count as loading the worktree.
        (self.idea / 'gradle.xml').write_text(LOADED['gradle.xml'].replace('app-feature', 'app'))
        (self.idea / 'misc.xml').write_text('<project version="4"><component name="FrameworkDetectionExcludesConfiguration">'
                                            '<file type="web" url="file://$PROJECT_DIR$/app-feature" />'
                                            '</component></project>')
        (self.idea / 'app.iml').write_text('<module version="4"><component name="NewModuleRootManager">'
                                           '<content url="file://$MODULE_DIR$/app" /></component></module>')
        (self.idea / 'modules.xml').write_text(LOADED['modules.xml'].replace('app-feature/.idea/app.iml', '.idea/app.iml'))
        process = start_script('remove', self.folder, GIT_WORKTREES_UNLIST_PAUSE='1')
        unlisted_while_present = False
        while process.poll() is None:
            unlisted_while_present |= self.folder.exists() and 'app-feature' not in self.workspace.read_text()
            time.sleep(0.02)
        stdout, stderr = process.communicate()
        self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assertTrue(unlisted_while_present, 'the folder was deleted while IntelliJ still listed it')
        self.assertFalse(self.folder.exists())
        self.assertEqual(self.workspace.read_text(), WORKSPACE)

    def test_remove_stops_while_intellij_has_the_worktree_loaded(self):
        self.add()
        for name, text in LOADED.items():
            with self.subTest(name):
                (self.idea / name).write_text(text)
                result = run_script('remove', self.folder)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(f'{STOP}: IntelliJ still has app-feature loaded in the {self.root.name} '
                              f'IntelliJ workspace, in {name}.', result.stdout)
                self.assertIn("choose Remove 'app-feature' from Workspace, then run remove again", result.stdout)
                self.assertTrue(self.folder.is_dir())
                self.assertEqual(self.workspace.read_text(), WITH_FEATURE)
                (self.idea / name).unlink()
        result = run_script('remove', self.folder)  # as after Remove from Workspace in IntelliJ
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.folder.exists())

    def test_remove_stops_for_a_module_kept_in_the_workspace_folder(self):
        # As IntelliJ loads a repository without a build: a module file in the workspace's own .idea.
        self.add()
        (self.idea / 'app-feature.iml').write_text(
            '<module type="GENERAL_MODULE" version="4"><component name="NewModuleRootManager">'
            '<content url="file://$MODULE_DIR$/app-feature" /></component></module>')
        (self.idea / 'modules.xml').write_text(
            '<project version="4"><component name="ProjectModuleManager"><modules>'
            '<module fileurl="file://$PROJECT_DIR$/.idea/app-feature.iml" '
            'filepath="$PROJECT_DIR$/.idea/app-feature.iml" /></modules></component></project>')
        result = run_script('remove', self.folder)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(f'{STOP}: IntelliJ still has app-feature loaded', result.stdout)
        self.assertIn('in modules.xml.', result.stdout)
        self.assertTrue(self.folder.is_dir())

    def test_remove_that_git_refuses_puts_the_intellij_entry_back(self):
        self.add()
        (self.folder / 'draft.txt').write_text('not saved yet\n')
        result = run_script('remove', self.folder)
        self.assertEqual(result.returncode, 1)
        self.assertIn('git:', result.stderr)
        self.assertEqual(self.workspace.read_text(), WITH_FEATURE)
        self.assertIn(f'{self.root.name} IntelliJ workspace: added back, because the worktree stays', result.stdout)

    def test_workspace_laid_out_differently_is_left_for_a_manual_edit(self):
        text = WORKSPACE.replace('  ', '    ')
        self.workspace.write_text(text)
        result = run_script('add', self.repo, 'feature', '--from', 'main')
        self.assertEqual(result.returncode, 1)
        self.assertIn("isn't laid out the way IntelliJ writes it, so update it by hand", result.stdout)
        self.assertEqual(self.workspace.read_text(), text)
        self.assertTrue(self.folder.is_dir())

    def entries(self):
        return {entry.get('path').rsplit('/', 1)[-1]: entry for entry in ET.parse(self.workspace).iter('project') if entry.get('path')}

    def test_a_workspace_lists_every_checkout_in_its_folder(self):
        self.workspace.write_text(WORKSPACE.replace('$PROJECT_DIR$/app"', '$PROJECT_DIR$/elsewhere"'))
        lib = self.root / 'lib'
        lib.mkdir()
        git(lib, 'init', '-q', '-b', 'main')
        git(lib, 'remote', 'add', 'origin', 'https://github.com/test/lib.git')
        output = self.add()
        entries = self.entries()
        self.assertEqual(sorted(entries), ['app', 'app-feature', 'elsewhere', 'lib', 'other'])
        self.assertEqual(entries['lib'].find('vcs').get('remoteUrl'), 'https://github.com/test/lib.git')
        self.assertIsNone(entries['app'].find('vcs'))  # app has no remote
        self.assertIn(f'{self.root.name} IntelliJ workspace: lists app, lib. IntelliJ loads them at its next start', output)

    def test_a_folder_without_idea_gets_a_workspace_with_every_checkout(self):
        shutil.rmtree(self.idea)
        output = self.add()
        self.assertIn(f'{self.root.name} IntelliJ workspace: created', output)
        self.assertEqual(sorted(self.entries()), ['app', 'app-feature'])
        self.assertIn('<option name="workspace" value="true" />', self.workspace.read_text())

    def test_an_ordinary_intellij_project_is_left_alone(self):
        self.workspace.unlink()  # its .idea stays, as an ordinary project's would
        output = self.add()
        self.assertFalse(self.workspace.exists())
        self.assertIn('IntelliJ: no multi-project workspace beside the main checkout lists it', output)


if __name__ == '__main__':
    unittest.main()
