"""Tests for how sync treats each branch's copy on the remote, on throwaway repositories.

Run: python3 -m unittest discover -s <this skill's folder>/tests
"""
import unittest

from helpers import RemoteTest, commit, git


class SyncCopyTest(RemoteTest):
    def test_sync_pushes_a_rebased_branch_over_its_copy(self):
        self.publish('feature')
        commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        self.assertIn('origin/feature: pushed', self.sync())
        self.assertEqual(self.on_remote('feature'), self.local('feature'))

    def test_sync_never_publishes_a_branch_without_a_copy(self):
        child = self.add('local-only', 'main')
        commit(child, 'local.txt', 'l\n', 'Local work')
        commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        self.sync()
        self.assertIsNone(self.on_remote('local-only'))

    def test_sync_leaves_new_local_commits_for_you_to_push(self):
        folder = self.publish('feature')
        commit(folder, 'more.txt', 'm\n', 'More work')
        before = self.on_remote('feature')
        self.assertNotIn('Copies on the remote', self.sync())
        self.assertEqual(self.on_remote('feature'), before)

    def test_sync_pushes_a_copy_left_behind_by_an_earlier_rebase(self):
        folder = self.publish('feature')
        commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        git(folder, 'rebase', '-q', 'main')
        self.assertIn('origin/feature: pushed', self.sync())
        self.assertEqual(self.on_remote('feature'), self.local('feature'))

    def test_sync_fetches_first_and_leaves_a_branch_with_someone_elses_commit(self):
        folder = self.publish('feature')
        tip = git(folder, 'rev-parse', 'HEAD')
        other = self.teammate('feature')
        theirs = commit(other, 'team.txt', 't\n', 'Teammate change')
        git(other, 'push', '-q', 'origin', 'feature')
        commit(self.repo, 'fix.txt', 'x\n', 'Fix main')
        self.assertIn('origin/feature has 1 commit it lacks', self.sync(expected_code=1))
        self.assertEqual(git(folder, 'rev-parse', 'HEAD'), tip)
        self.assertEqual(self.on_remote('feature'), theirs)


if __name__ == '__main__':
    unittest.main()
