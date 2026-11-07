"""Git commands that find a repository's checkouts and add or remove worktrees."""
import subprocess
from pathlib import Path


class GitError(Exception):
    """A git command failed. The message is git's own error text."""


def git(cwd, *args):
    """Run git in cwd and return its output, or raise GitError."""
    result = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f'git {args[0]} failed')
    return result.stdout.strip()


def git_succeeds(cwd, *args):
    return subprocess.run(['git', '-C', str(cwd), *args], capture_output=True).returncode == 0


def checkouts(repo):
    """List (path, branch) for every checkout of the repository, the main checkout first."""
    found = []
    for line in git(repo, 'worktree', 'list', '--porcelain').splitlines():
        if line.startswith('worktree '):
            found.append([Path(line[len('worktree '):]).resolve(), None])
        elif line.startswith('branch refs/heads/'):
            found[-1][1] = line[len('branch refs/heads/'):]
    return [tuple(entry) for entry in found]


def main_checkout(repo):
    return checkouts(repo)[0][0]


def checkout_of(repo, branch):
    """Return the checkout that has the branch checked out, or None."""
    return next((path for path, name in checkouts(repo) if name == branch), None)


def branch_exists(repo, branch):
    return git_succeeds(repo, 'show-ref', '--verify', '--quiet', f'refs/heads/{branch}')


def sibling_folder(main, branch):
    """Return <repo folder>-<branch> beside the main checkout, with / in the branch as -."""
    return main.parent / f'{main.name}-{branch.replace("/", "-")}'


def add_worktree(repo, branch, start, folder):
    """Check out the branch in folder, creating the branch when needed. Return how."""
    if branch_exists(repo, branch):
        git(repo, 'worktree', 'add', str(folder), branch)
        return f'existing branch {branch}'
    remote = None if start else _remote_branch(repo, branch)
    if remote:
        git(repo, 'worktree', 'add', '--track', '-b', branch, str(folder), remote)
        return f'new branch {branch}, tracking {remote}'
    git(repo, 'worktree', 'add', '-b', branch, str(folder), start or 'HEAD')
    return f'new branch {branch} from {start or f"the current commit of {repo}"}'


def remove_worktree(main, folder):
    """Remove the worktree. Git refuses one with changes, untracked files, or a lock."""
    git(main, 'worktree', 'remove', str(folder))


def _remote_branch(repo, branch):
    """Return the one remote branch with this name, such as origin/fix-login, or None."""
    names = git(repo, 'for-each-ref', '--format=%(refname:short)', f'refs/remotes/*/{branch}').splitlines()
    return names[0] if len(names) == 1 else None
