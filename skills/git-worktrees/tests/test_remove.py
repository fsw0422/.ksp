"""Tests for `worktree.py remove` with a remote: when it deletes a merged branch's copy, and when it stops.

Run: python3 -m unittest discover -s <this skill's folder>/tests
"""
import unittest

from helpers import RemoteTest, commit, git, pull_request

STOP = 'Stopped before removing anything'
NOT_LOGGED_IN = 'To get started with GitHub CLI, please run:  gh auth login\n'


class RemoveCase(RemoteTest):
    """Helpers for the remove tests. It has no tests of its own, so subclasses don't repeat any."""

    def merge(self, branch):
        """Squash the branch into main and push main, as a finished merge does."""
        self.squash_into_main(branch)
        git(self.repo, 'push', '-q', 'origin', 'main')

    def remove(self, folder, *flags, expected_code=0):
        result = self.script('remove', folder, *flags)
        self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
        return result.stdout

    def assert_nothing_removed(self, folder, branch):
        self.assertTrue(folder.is_dir())
        self.assertIsNotNone(self.local(branch))
        self.assertIsNotNone(self.on_remote(branch))


class RemoveTest(RemoveCase):
    def test_deletes_a_merged_branch_here_and_on_the_remote(self):
        folder = self.publish('feature')
        self.merge('feature')
        output = self.remove(folder)
        self.assertIn('Deleted branch feature: main has all its work', output)
        self.assertIn('origin/feature: deleted from origin', output)
        self.assertIsNone(self.local('feature'))
        self.assertIsNone(self.on_remote('feature'))
        self.assertIn('/feature', git(self.repo, 'for-each-ref', '--format=%(refname)', 'refs/recovery/removed/'))
        self.assertIn('pr list --repo github.com/test/app', self.gh_calls()[0])

    def test_stops_until_the_parent_is_pushed(self):
        folder = self.publish('feature')
        self.squash_into_main('feature')
        output = self.remove(folder, expected_code=1)
        self.assertIn(f"{STOP}: origin/main doesn't have its work yet", output)
        self.assertIn('Push main, then run remove again.', output)
        self.assert_nothing_removed(folder, 'feature')
        self.assertEqual(self.gh_calls(), [])

    def test_deletes_a_branch_merged_on_the_remote_before_its_parent_is_pulled(self):
        folder = self.publish('feature')
        other = self.teammate('main')
        git(other, 'fetch', '-q', 'origin', 'feature')
        git(other, 'merge', '--squash', 'origin/feature')
        git(other, 'commit', '-q', '-m', 'Add feature (#1)')
        git(other, 'push', '-q', 'origin', 'main')
        output = self.remove(folder)
        self.assertIn('Deleted branch feature: origin/main has all its work', output)
        self.assertIsNone(self.on_remote('feature'))

    def test_handles_a_copy_the_remote_already_deleted(self):
        folder = self.publish('feature')
        self.squash_into_main('feature')
        git(self.remote, 'branch', '-D', 'feature')  # as GitHub can do after merging a pull request
        output = self.remove(folder)
        self.assertIn('origin/feature: already gone from origin', output)
        self.assertIsNone(self.local('feature'))
        self.assertEqual(self.gh_calls(), [])

    def test_stops_for_someone_elses_commit_on_the_copy(self):
        folder = self.publish('feature')
        self.merge('feature')
        other = self.teammate('feature')
        commit(other, 'late.txt', 'l\n', 'Late teammate change')
        git(other, 'push', '-q', 'origin', 'feature')
        output = self.remove(folder, expected_code=1)
        self.assertIn(f"{STOP}: origin/feature has 1 commit that feature doesn't", output)
        self.assert_nothing_removed(folder, 'feature')

    def test_keeps_unmerged_work(self):
        folder = self.publish('feature')
        output = self.remove(folder)
        self.assertIn("Kept branch feature: it has work that isn't in main or origin/main", output)
        self.assertFalse(folder.exists())
        self.assertIsNotNone(self.local('feature'))
        self.assertIsNotNone(self.on_remote('feature'))

    def test_keeps_a_branch_that_others_build_on(self):
        parent = self.add('audio', 'main')
        commit(parent, 'audio.txt', 'a\n', 'Audio')
        self.add('audio-codec', 'audio')
        self.squash_into_main('audio')
        output = self.remove(parent)
        self.assertIn('Kept branch audio: other branches build on it (audio-codec)', output)
        self.assertIsNotNone(self.local('audio'))


class PullRequestTest(RemoveCase):
    def setUp(self):
        super().setUp()
        self.folder = self.publish('feature')
        self.merge('feature')

    def test_stops_for_an_open_pull_request_from_the_branch(self):
        self.pull_requests('head', pull_request(7, 'Add feature'))
        output = self.remove(self.folder, expected_code=1)
        self.assertIn(f'{STOP}: deleting origin/feature would close the pull requests from it', output)
        self.assertIn('  #7 Add feature (from it): https://github.com/test/app/pull/7', output)
        self.assertIn('Merge or close them first, or run remove again with --close-prs.', output)
        self.assert_nothing_removed(self.folder, 'feature')

    def test_stops_for_an_open_pull_request_into_the_branch(self):
        self.pull_requests('base', pull_request(9, 'Codec fix'))
        output = self.remove(self.folder, expected_code=1)
        self.assertIn('  #9 Codec fix (into it): https://github.com/test/app/pull/9', output)
        self.assert_nothing_removed(self.folder, 'feature')

    def test_ignores_a_pull_request_from_a_fork_branch_with_the_same_name(self):
        self.pull_requests('head', pull_request(4, 'Their feature', head='someone/app'))
        self.assertIn('origin/feature: deleted from origin', self.remove(self.folder))

    def test_stops_when_gh_cant_check(self):
        self.gh_fails(NOT_LOGGED_IN)
        output = self.remove(self.folder, expected_code=1)
        self.assertIn(f"{STOP}: couldn't check the pull requests that use origin/feature: "
                      'To get started with GitHub CLI, please run: gh auth login.', output)
        self.assert_nothing_removed(self.folder, 'feature')

    def test_stops_when_the_remote_isnt_on_github(self):
        git(self.repo, 'remote', 'set-url', 'origin', str(self.remote))
        output = self.remove(self.folder, expected_code=1)
        self.assertIn("origin's address isn't a GitHub repository", output)
        self.assertEqual(self.gh_calls(), [])

    def test_close_prs_deletes_without_checking(self):
        self.gh_fails(NOT_LOGGED_IN)
        output = self.remove(self.folder, '--close-prs')
        self.assertIn('origin/feature: deleted from origin', output)
        self.assertEqual(self.gh_calls(), [])

    def test_close_prs_still_needs_the_parent_pushed(self):
        folder = self.publish('second')
        self.squash_into_main('second')
        output = self.remove(folder, '--close-prs', expected_code=1)
        self.assertIn(f"{STOP}: origin/main doesn't have its work yet", output)


class ForkTest(RemoveCase):
    """The branch's copy is on a fork, origin, and its parent's copy is on upstream."""

    def test_checks_the_parents_repository_for_the_forks_pull_requests(self):
        upstream = self.add_remote('upstream', 'git@github.com:team/app.git')
        git(self.repo, 'branch', '-q', '--set-upstream-to=upstream/main', 'main')
        folder = self.publish('feature')
        self.squash_into_main('feature')
        git(self.repo, 'push', '-q', 'upstream', 'main')
        self.pull_requests('head', pull_request(3, 'Add feature', head='test/app', listed_in='team/app'))
        output = self.remove(folder, expected_code=1)
        self.assertIn('  #3 Add feature (from it): https://github.com/team/app/pull/3', output)
        self.assertTrue(any('--repo github.com/team/app' in call for call in self.gh_calls()))
        self.assertIsNotNone(self.on_remote('main', upstream))


if __name__ == '__main__':
    unittest.main()
