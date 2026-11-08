"""Each branch's parent and base, kept in git config so sync knows where every branch belongs.

The parent is the branch it follows. The base is the parent commit where the branch's own
commits start, so a rebase replays only those, even after the parent itself was rewritten.
Both live under the branch's own config section, so they follow a renamed branch and go
away with a deleted one.
"""
from checkouts import git, git_succeeds, git_try

PARENT, BASE = 'worktreeParent', 'worktreeBase'


def commit_of(repo, ref):
    return git(repo, 'rev-parse', '--verify', f'{ref}^{{commit}}')


def is_ancestor(repo, older, newer):
    return git_succeeds(repo, 'merge-base', '--is-ancestor', older, newer)


def record_parent(repo, branch, parent):
    """Make sync keep the branch on the parent's head. Return the branch's base.

    A recorded base the branch still contains is kept, so a branch moved to another parent
    still replays only its own commits.
    """
    git(repo, 'config', f'branch.{branch}.{PARENT}', parent)
    base = _recorded_base(repo, branch)
    if not base or not is_ancestor(repo, base, branch):
        base = git(repo, 'merge-base', branch, parent)
    set_base(repo, branch, base)
    return base


def set_base(repo, branch, base):
    if _recorded_base(repo, branch) != base:
        git(repo, 'config', f'branch.{branch}.{BASE}', base)


def base_of(repo, branch, parent):
    """Return where the branch's own commits start: the newer of its recorded base and its fork point.

    The fork point alone is wrong after the parent was rewritten, because the parent's old commits
    would then count as the branch's own. The recorded base alone goes stale when the branch is
    rebased by hand.
    """
    fork = git(repo, 'merge-base', branch, parent)
    recorded = _recorded_base(repo, branch)
    if recorded and is_ancestor(repo, recorded, branch) and is_ancestor(repo, fork, recorded):
        return recorded
    return fork


def parent_links(repo):
    """Return {branch: parent} for every branch with a recorded parent."""
    output = git_try(repo, 'config', '--get-regexp', rf'^branch\..*\.{PARENT.lower()}$') or ''
    links = {}
    for line in output.splitlines():
        key, _, parent = line.partition(' ')
        links[key[len('branch.'):-len(f'.{PARENT}')]] = parent
    return links


def makes_loop(links, branch, parent):
    """True if following parents up from parent leads back to branch."""
    seen = set()
    while parent and parent not in seen:
        if parent == branch:
            return True
        seen.add(parent)
        parent = links.get(parent)
    return False


def walk(links):
    """Yield (branch, parent, depth) depth-first, each parent before its children. Roots have no parent."""
    children = {}
    for branch, parent in sorted(links.items()):
        children.setdefault(parent, []).append(branch)

    def visit(parent, depth):
        for child in children.get(parent, []):
            yield child, parent, depth
            yield from visit(child, depth + 1)

    for root in sorted(parent for parent in children if parent not in links):
        yield root, None, 0
        yield from visit(root, 1)


def _recorded_base(repo, branch):
    return git_try(repo, 'config', '--get', f'branch.{branch}.{BASE}')
