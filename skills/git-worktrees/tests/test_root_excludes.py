"""Tests for how `worktree.py add` and `remove` keep a root that holds the listed folders from showing them twice.

Run: python3 -m unittest discover -s <this skill's folder>/tests
"""
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from helpers import commit, git, run_script, start_script


class RootExcludesTest(unittest.TestCase):
    """A workspace that lists its own folder, ".", beside the checkouts app and zeta, and an unlisted checkout, other."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.repo = self.root / 'app'
        for name in ('app', 'zeta', 'other'):
            (self.root / name).mkdir()
            git(self.root / name, 'init', '-q', '-b', 'main')
        commit(self.repo, 'README.md', 'app\n', 'Start')
        self.workspace = self.root / 'demo.code-workspace'
        self.write_workspace(['.', 'app', 'zeta'])
        self.settings = self.root / '.vscode' / 'settings.json'
        self.folder = self.root / 'app-feature'

    def write_workspace(self, paths):
        self.workspace.write_text(json.dumps({'folders': [{'path': path} for path in paths]}, indent='\t') + '\n')

    def write_settings(self, data):
        self.settings.parent.mkdir(exist_ok=True)
        self.settings.write_text(json.dumps(data, indent=2) + '\n')

    def read_settings(self):
        return json.loads(self.settings.read_text())

    def workspace_paths(self):
        return [entry['path'] for entry in json.loads(self.workspace.read_text())['folders']]

    def add(self):
        result = run_script('add', self.repo, 'feature', '--from', 'main')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_add_lists_every_checkout_in_the_root_and_hides_them_there(self):
        (self.root / 'notes').mkdir()  # not a checkout, so the root keeps showing it
        output = self.add()
        self.assertEqual(self.workspace_paths(), ['.', 'app', 'app-feature', 'other', 'zeta'])
        settings = self.read_settings()
        self.assertEqual(list(settings['files.exclude']), ['app', 'app-feature', 'other', 'zeta'])
        self.assertEqual(list(settings['files.watcherExclude']), ['app-feature/**', 'app/**', 'other/**', 'zeta/**'])
        self.assertIn('demo.code-workspace: lists other', output)
        self.assertIn(f'{self.root.name}/.vscode/settings.json: hides app, app-feature, other, zeta', output)

    def test_add_never_shows_the_new_worktree_in_the_root(self):
        self.add()  # creates the settings file, so the next add only adds to it
        process = start_script('add', self.repo, 'second', '--from', 'main')
        second = self.root / 'app-second'
        hidden_whenever_present = True
        while process.poll() is None:
            try:
                hidden_whenever_present &= not second.exists() or 'app-second' in self.read_settings()['files.exclude']
            except json.JSONDecodeError:
                pass  # read while the script was writing the file
            time.sleep(0.005)
        stdout, stderr = process.communicate()
        self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assertTrue(hidden_whenever_present, 'the root showed the new worktree')
        self.assertLess(stdout.index('settings.json: hides app-second'), stdout.index('Created'))

    def test_sync_lists_and_hides_a_worktree_made_elsewhere(self):
        git(self.repo, 'worktree', 'add', '-q', '-b', 'by-hand', str(self.root / 'app-by-hand'))
        result = run_script('sync', self.repo)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('app-by-hand', self.workspace_paths())
        self.assertIn('app-by-hand', self.read_settings()['files.exclude'])

    def test_a_root_workspace_lists_a_repository_it_did_not_list_yet(self):
        self.write_workspace(['.', 'zeta'])
        self.add()
        self.assertEqual(self.workspace_paths(), ['.', 'app', 'app-feature', 'other', 'zeta'])
        self.assertEqual(list(self.read_settings()['files.exclude']), ['app', 'app-feature', 'other', 'zeta'])

    def test_a_checkout_taken_out_of_the_workspace_comes_back(self):
        self.add()
        self.write_workspace(['.', 'app', 'app-feature', 'zeta'])  # as when other is removed in VS Code
        result = run_script('remove', self.folder)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.workspace_paths(), ['.', 'app', 'other', 'zeta'])
        self.assertEqual(list(self.read_settings()['files.exclude']), ['app', 'other', 'zeta'])

    def test_add_keeps_the_users_own_patterns(self):
        (self.root / '.idea').mkdir()
        self.write_settings({'files.exclude': {'**/node_modules': True, '.idea': True, 'app': True},
                             'editor.tabSize': 2})
        self.add()
        settings = self.read_settings()
        self.assertEqual(list(settings['files.exclude']),
                         ['**/node_modules', '.idea', 'app', 'app-feature', 'other', 'zeta'])
        self.assertEqual(settings['editor.tabSize'], 2)
        self.assertIn('\n  "files.exclude"', self.settings.read_text())  # keeps the file's indentation

    def test_remove_shows_nothing_until_the_folder_is_gone(self):
        self.add()
        process = start_script('remove', self.folder, GIT_WORKTREES_UNLIST_PAUSE='1')
        hidden_while_present = True
        while process.poll() is None:
            try:
                hidden_while_present &= not self.folder.exists() or 'app-feature' in self.read_settings()['files.exclude']
            except json.JSONDecodeError:
                pass  # read while the script was writing the file
            time.sleep(0.02)
        stdout, stderr = process.communicate()
        self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assertTrue(hidden_while_present, 'the root showed the folder while it still existed')
        self.assertFalse(self.folder.exists())
        settings = self.read_settings()
        self.assertEqual(list(settings['files.exclude']), ['app', 'other', 'zeta'])
        self.assertEqual(list(settings['files.watcherExclude']), ['app/**', 'other/**', 'zeta/**'])
        self.assertIn('no longer hides app-feature', stdout)

    def test_workspace_without_an_outer_root_gets_no_settings(self):
        self.write_workspace(['app', 'zeta'])
        self.add()
        self.assertFalse(self.settings.exists())
        self.assertEqual(self.workspace_paths(), ['app', 'app-feature', 'zeta'])

    def test_never_changes_the_settings_of_a_checkout(self):
        (self.repo / 'lib').mkdir()
        self.write_workspace(['app', 'app/lib'])
        self.add()
        self.assertFalse((self.repo / '.vscode').exists())

    def test_settings_with_comments_are_left_for_a_manual_edit(self):
        self.settings.parent.mkdir()
        text = '{\n  // mine\n  "files.exclude": {"app": true}\n}\n'
        self.settings.write_text(text)
        result = run_script('add', self.repo, 'feature', '--from', 'main')
        self.assertEqual(result.returncode, 1)
        self.assertIn('settings.json: has comments or trailing commas, so update it by hand', result.stdout)
        self.assertEqual(self.settings.read_text(), text)
        self.assertTrue(self.folder.is_dir())


if __name__ == '__main__':
    unittest.main()
