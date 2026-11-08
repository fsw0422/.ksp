"""A branch's copy on its remote: fetch it, check it holds nothing new, and update or delete it.

Only a remote branch with the same name counts as a copy. A branch that tracks origin/main follows
that branch; it isn't a copy of it. Every push carries a lease pinned to the commit the checks saw,
so it can never overwrite a commit nobody here has seen.
"""
from collections import namedtuple

from checkouts import GitError, git, git_try
from lineage import is_ancestor

Copy = namedtuple('Copy', 'remote ref')  # such as ('origin', 'refs/remotes/origin/fix')


def remote_copy(repo, branch):
    """Return the branch's copy on its remote, or None."""
    fields = git(repo, 'for-each-ref', '--format=%(upstream) %(upstream:remotename) %(upstream:remoteref)',
                 f'refs/heads/{branch}').split(' ')
    ref, remote, name = (fields + ['', '', ''])[:3]
    if ref.startswith('refs/remotes/') and remote not in ('', '.') and name == f'refs/heads/{branch}':
        return Copy(remote, ref)
    return None


def short_name(copy):
    return copy.ref[len('refs/remotes/'):]


def tip_of(repo, copy):
    """Return the commit the copy had at the last fetch, or None if the remote doesn't have it."""
    return git_try(repo, 'rev-parse', '--verify', '--quiet', copy.ref)


def fetch(repo, remotes):
    """Fetch each remote, dropping copies it no longer has. Return a line for each fetch that failed."""
    failed = []
    for remote in sorted(remotes):
        try:
            git(repo, 'fetch', '--quiet', '--prune', remote)
        except GitError as error:
            failed.append(f"Couldn't fetch {remote}, so its copies are as of the last fetch: {reason(error)}")
    return failed


def foreign_commits(repo, branch, copy):
    """Count the copy's commits that the branch lacks, apart from older versions of its own.

    A rebase keeps each commit's author, date and subject, so a commit on the copy with the same
    three as a local one is an older version of it. Comparing diffs wouldn't work: rebases change them.
    """
    if not tip_of(repo, copy):
        return 0
    ours = set(_identities(repo, f'{copy.ref}..{branch}'))
    return sum(identity not in ours for identity in _identities(repo, f'{branch}..{copy.ref}'))


def update(repo, branch, copy, rebased):
    """Push a rebased branch over its copy. Return (pushed, what happened), or None if there's nothing to do.

    A branch rebased just now is always pushed. Another branch is pushed only when its copy holds
    nothing but older versions of its commits, left by an earlier rebase. A copy that's only behind
    has new local commits that nothing rewrote, so pushing them is left to the user.
    """
    seen, tip = tip_of(repo, copy), git(repo, 'rev-parse', branch)
    if not seen or seen == tip:
        return None
    foreign = foreign_commits(repo, branch, copy)
    if foreign:
        return False, (f'{short_name(copy)}: not pushed, because it has {foreign} '
                       f"commit{'s' if foreign > 1 else ''} that {branch} doesn't; pull them in first")
    if not rebased and is_ancestor(repo, seen, tip):
        return None
    try:
        git(repo, 'push', '--quiet', f'--force-with-lease=refs/heads/{branch}:{seen}',
            copy.remote, f'refs/heads/{branch}:refs/heads/{branch}')
    except GitError as error:
        return False, f'{short_name(copy)}: not updated, because the push failed: {reason(error)}'
    return True, f'{short_name(copy)}: pushed {seen[:7]} → {tip[:7]}'


def delete(repo, branch, copy):
    """Delete the copy from its remote. Return what happened.

    Remove checks first that the copy holds nothing new, and the lease makes sure nothing arrived since.
    """
    seen = tip_of(repo, copy)
    if not seen:
        return f'{short_name(copy)}: already gone from {copy.remote}'
    try:
        git(repo, 'push', '--quiet', f'--force-with-lease=refs/heads/{branch}:{seen}',
            copy.remote, f':refs/heads/{branch}')
    except GitError as error:
        return (f'{short_name(copy)}: not deleted, because the push failed: {reason(error)}. '
                f'To delete it later: git push {copy.remote} --delete {branch}')
    return f'{short_name(copy)}: deleted from {copy.remote}'


def reason(error):
    """Pick the line of a git error that says what went wrong."""
    lines = [line.strip() for line in str(error).splitlines() if line.strip()]
    return next((line for line in lines if line.startswith(('!', 'fatal:'))), lines[-1] if lines else 'unknown error')


def _identities(repo, revisions):
    return git(repo, 'log', '--format=%ae%x1f%ad%x1f%s', '--date=raw', revisions).splitlines()
