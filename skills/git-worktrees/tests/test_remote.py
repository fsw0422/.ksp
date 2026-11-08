"""Tests for how sync and remove treat each branch's copy on the remote, on throwaway repositories.

Run: python3 -m unittest discover -s <this skill's folder>/tests
"""
import unittest

from helpers import RepoTest, commit, git, git_maybe, run_script


class RemoteCopyTest(RepoTest):
    def setUp(self):
        super().setUp()
        self.add_remote()

    def publish(self, branch, parent='main'):
        """Create the branch with one commit, and push it, so it has a copy on the remote."""
        folder = self.add(branch, parent)
        commit(folder, f'{branch}.txt', f'{branch}\n', f'Add {branch}')
        git(folder, 'push', '-q', '-u', 'origin', branch)
        return folder

    def local(self, branch):
        return git_maybe(self.repo, 'rev-parse', '--verify', '--quiet', f'refs/heads/{branch}')

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

    def test_remove_deletes_a_merged_branch_here_and_on_the_remote(self):
        folder = self.publish('feature')
        self.squash_into_main('feature')
        result = run_script('remove', folder)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Deleted branch feature: main has all its work', result.stdout)
        self.assertIn('origin/feature: deleted from origin', result.stdout)
        self.assertIsNone(self.local('feature'))
        self.assertIsNone(self.on_remote('feature'))
        self.assertIn('/feature', git(self.repo, 'for-each-ref', '--format=%(refname)', 'refs/recovery/removed/'))

    def test_remove_deletes_a_branch_merged_on_the_remote_before_its_parent_is_pulled(self):
        folder = self.publish('feature')
        other = self.teammate('main')
        git(other, 'fetch', '-q', 'origin', 'feature')
        git(other, 'merge', '--squash', 'origin/feature')
        git(other, 'commit', '-q', '-m', 'Add feature (#1)')
        git(other, 'push', '-q', 'origin', 'main')
        result = run_script('remove', folder)
        self.assertIn('Deleted branch feature: origin/main has all its work', result.stdout)
        self.assertIsNone(self.on_remote('feature'))

    def test_remove_handles_a_copy_the_remote_already_deleted(self):
        folder = self.publish('feature')
        self.squash_into_main('feature')
        git(self.remote, 'branch', '-D', 'feature')  # as GitHub can do after merging a pull request
        result = run_script('remove', folder)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('origin/feature: already gone from origin', result.stdout)
        self.assertIsNone(self.local('feature'))

    def test_remove_keeps_a_copy_with_someone_elses_commit(self):
        folder = self.publish('feature')
        self.squash_into_main('feature')
        other = self.teammate('feature')
        commit(other, 'late.txt', 'l\n', 'Late teammate change')
        git(other, 'push', '-q', 'origin', 'feature')
        result = run_script('remove', folder)
        self.assertIn("origin/feature: kept, because it has commits that feature doesn't", result.stdout)
        self.assertIsNotNone(self.on_remote('feature'))

    def test_remove_keeps_unmerged_work(self):
        folder = self.publish('feature')
        result = run_script('remove', folder)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Kept branch feature: it has work that isn't in main or origin/main", result.stdout)
        self.assertIsNotNone(self.local('feature'))
        self.assertIsNotNone(self.on_remote('feature'))

    def test_remove_keeps_a_branch_that_others_build_on(self):
        parent = self.add('audio', 'main')
        commit(parent, 'audio.txt', 'a\n', 'Audio')
        self.add('audio-codec', 'audio')
        self.squash_into_main('audio')
        result = run_script('remove', parent)
        self.assertIn('Kept branch audio: other branches build on it (audio-codec)', result.stdout)
        self.assertIsNotNone(self.local('audio'))


if __name__ == '__main__':
    unittest.main()
