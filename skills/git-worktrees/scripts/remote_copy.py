"""A branch's copy on its remote: whether a rebase could lose any of it, and how to update it."""
from checkouts import git, git_succeeds


def remote_copy(repo, branch):
    """Return the branch's copy on its remote, such as refs/remotes/origin/fix, or None.

    Only a remote branch with the same name counts. A branch that tracks origin/main follows
    that branch; it isn't a copy of it.
    """
    fields = git(repo, 'for-each-ref', '--format=%(upstream) %(upstream:remoteref)', f'refs/heads/{branch}')
    copy, _, name = fields.partition(' ')
    if copy.startswith('refs/remotes/') and name == f'refs/heads/{branch}' \
            and git_succeeds(repo, 'rev-parse', '--verify', '--quiet', copy):
        return copy
    return None


def short_name(copy):
    return copy[len('refs/remotes/'):]


def foreign_commits(repo, branch, copy):
    """Count the copy's commits that the branch lacks, apart from older versions of its own.

    A rebase keeps each commit's author, date and subject, so a commit on the copy with the same
    three as a local one is an older version of it. Comparing diffs wouldn't work: rebases change them.
    """
    ours = set(_identities(repo, f'{copy}..{branch}'))
    return sum(identity not in ours for identity in _identities(repo, f'{branch}..{copy}'))


def update_hint(repo, branch, copy):
    """Say how to bring the copy up to date with the branch, or None if it is. Sync never pushes."""
    if git(repo, 'rev-parse', copy) == git(repo, 'rev-parse', branch):
        return None
    if git_succeeds(repo, 'merge-base', '--is-ancestor', copy, branch):
        return f'{short_name(copy)}: a push updates it'
    return f'{short_name(copy)}: a force-push updates it; it only has older versions of your commits'


def _identities(repo, revisions):
    return git(repo, 'log', '--format=%ae%x1f%ad%x1f%s', '--date=raw', revisions).splitlines()
