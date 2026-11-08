"""Tests for `worktree.py sync` and `worktree.py parent`, on throwaway repositories.

Run: python3 -m unittest discover -s <this skill's folder>/tests
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import commit, git, run_script


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.repo = self.root / 'app'
        self.repo.mkdir()
        git(self.repo, 'init', '-q', '-b', 'main')
        commit(self.repo, 'README.md', 'one\ntwo\nthree\n', 'Start')

    def add(self, branch, parent):
        result = run_script('add', self.repo, branch, '--from', parent)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.root / f'app-{branch}'

    def sync(self, expected_code=0):
        result = run_script('sync', self.repo)
        self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
        return result.stdout

    def subjects(self, ref):
        return git(self.repo, 'log', '--format=%s', ref).splitlines()

    def add_remote(self):
        remote = self.root / 'origin.git'
        git(self.root, 'init', '-q', '--bare', str(remote))
        git(self.repo, 'remote', 'add', 'origin', str(remote))
        return remote

    def test_child_moves_onto_a_commit_made_directly_on_its_parent(self):
        child = self.add('feature', 'main')
        commit(child, 'feature.txt', 'f\n', 'Add feature')
        commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        output = self.sync()
        self.assertEqual(self.subjects('feature'), ['Add feature', 'Fix main', 'Start'])
        self.assertIn('feature: rebased onto main', output)
        self.assertIn('1 commit of its own, unchanged', output)
        saved = git(self.repo, 'for-each-ref', '--format=%(refname)', 'refs/recovery/sync/')
        self.assertIn('/tip/feature', saved)
        self.assertIn("feature: on its parent's head", self.sync())

    def test_children_follow_a_parent_that_sync_rebased(self):
        parent = self.add('audio', 'main')
        commit(parent, 'audio.txt', 'a\n', 'Audio draft')
        child = self.add('audio-codec', 'audio')
        commit(child, 'codec.txt', 'c\n', 'Codec fix')
        commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        output = self.sync()
        self.assertEqual(self.subjects('audio-codec'), ['Codec fix', 'Audio draft', 'Fix main', 'Start'])
        self.assertLess(output.index('audio: rebased'), output.index('audio-codec: rebased'))

    def test_child_follows_a_parent_rewritten_by_hand_without_replaying_its_old_commits(self):
        parent = self.add('audio', 'main')
        commit(parent, 'README.md', 'one\ntwo\nTHREE\n', 'Audio draft')
        child = self.add('audio-codec', 'audio')
        commit(child, 'codec.txt', 'c\n', 'Codec fix')
        (parent / 'README.md').write_text('one\ntwo\nThree\n')
        git(parent, 'commit', '-q', '--amend', '-a', '-m', 'Audio draft, reworded')
        self.sync()
        self.assertEqual(self.subjects('audio-codec'), ['Codec fix', 'Audio draft, reworded', 'Start'])
        self.assertEqual((child / 'README.md').read_text(), 'one\ntwo\nThree\n')

    def test_child_without_commits_moves_to_the_new_head(self):
        child = self.add('later', 'main')
        head = commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        self.assertIn('it has no commits of its own', self.sync())
        self.assertEqual(git(child, 'rev-parse', 'HEAD'), head)

    def test_child_with_uncommitted_files_is_left_alone(self):
        child = self.add('feature', 'main')
        tip = commit(child, 'feature.txt', 'f\n', 'Add feature')
        (child / 'draft.txt').write_text('half done\n')
        commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        self.assertIn('uncommitted or untracked files', self.sync(expected_code=1))
        self.assertEqual(git(child, 'rev-parse', 'HEAD'), tip)

    def test_conflicting_rebase_is_undone(self):
        child = self.add('feature', 'main')
        tip = commit(child, 'README.md', 'feature\n', 'Feature edits README')
        commit(self.repo, 'README.md', 'main\n', 'Main edits README')
        output = self.sync(expected_code=1)
        self.assertIn('its rebase conflicts in README.md', output)
        self.assertIn('rebase --onto main', output)
        self.assertEqual(git(child, 'rev-parse', 'HEAD'), tip)
        self.assertEqual(git(child, 'status', '--porcelain'), '')

    def test_squash_merged_child_only_waits_for_removal(self):
        child = self.add('feature', 'main')
        tip = commit(child, 'feature.txt', 'f\n', 'Add feature')
        git(self.repo, 'merge', '--squash', 'feature')
        git(self.repo, 'commit', '-q', '-m', 'Feature')
        self.assertIn('already in main', self.sync(expected_code=1))
        self.assertEqual(git(child, 'rev-parse', 'HEAD'), tip)

    def test_branch_without_a_worktree_is_left_alone(self):
        child = self.add('feature', 'main')
        commit(child, 'feature.txt', 'f\n', 'Add feature')
        run_script('remove', child)
        commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        self.assertIn('not checked out in any worktree', self.sync(expected_code=1))

    def test_child_whose_remote_copy_has_someone_elses_commit_is_left_alone(self):
        remote = self.add_remote()
        child = self.add('feature', 'main')
        tip = commit(child, 'feature.txt', 'f\n', 'Add feature')
        git(child, 'push', '-q', '-u', 'origin', 'feature')
        other = self.root / 'other'
        git(self.root, 'clone', '-q', '-b', 'feature', str(remote), str(other))
        commit(other, 'team.txt', 't\n', 'Teammate change')
        git(other, 'push', '-q', 'origin', 'feature')
        git(self.repo, 'fetch', '-q', 'origin')
        commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        self.assertIn('origin/feature has 1 commit it lacks', self.sync(expected_code=1))
        self.assertEqual(git(child, 'rev-parse', 'HEAD'), tip)

    def test_remote_copy_with_only_older_versions_needs_a_force_push(self):
        self.add_remote()
        child = self.add('feature', 'main')
        commit(child, 'feature.txt', 'f\n', 'Add feature')
        git(child, 'push', '-q', '-u', 'origin', 'feature')
        commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        self.assertIn('origin/feature: a force-push updates it', self.sync())

    def test_parent_lets_sync_follow_an_existing_branch(self):
        git(self.repo, 'branch', 'old-work')
        run_script('add', self.repo, 'old-work')
        folder = self.root / 'app-old-work'
        commit(folder, 'old.txt', 'o\n', 'Old work')
        commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        self.assertIn('No branch has a recorded parent', self.sync())
        result = run_script('parent', folder, 'main')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Parent of old-work: main', result.stdout)
        self.sync()
        self.assertEqual(self.subjects('old-work'), ['Old work', 'Fix main', 'Start'])

    def test_parent_refuses_a_loop(self):
        first = self.add('first', 'main')
        self.add('second', 'first')
        result = run_script('parent', first, 'second')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already follows first', result.stderr)


if __name__ == '__main__':
    unittest.main()
