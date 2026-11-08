"""Find the open pull requests that use a branch's copy on GitHub, by asking the gh CLI.

Deleting a branch on GitHub closes the pull requests from it, and closes or retargets the ones into it.
"""
import json
import os
import re
import subprocess
from urllib.parse import urlparse

from checkouts import git_try

FIELDS = 'number,title,url,headRepository,headRepositoryOwner'


class UnknownPullRequests(Exception):
    """gh couldn't say which pull requests are open. The message says why."""


def open_pull_requests(repo, branch, copy, parent_copy):
    """Return a line for each open pull request from or into the branch's copy on its remote."""
    own = github_repo(repo, copy.remote)
    places = [own]
    if parent_copy and parent_copy.remote != copy.remote:
        places.append(github_repo(repo, parent_copy.remote))  # a fork's pull requests live in its parent's repository
    found = [_line(pr, 'from it') for place in dict.fromkeys(places)
             for pr in _list(place, '--head', branch) if _head_of(pr) == own.split('/', 1)[1].lower()]
    return found + [_line(pr, 'into it') for pr in _list(own, '--base', branch)]


def github_repo(repo, remote):
    """Return the remote's repository as host/owner/name, such as github.com/fsw0422/.ksp."""
    # The configured address comes first: `insteadOf` rewrites can hide the host.
    for url in (git_try(repo, 'config', '--get', f'remote.{remote}.url'), git_try(repo, 'remote', 'get-url', remote)):
        name = _parse(url or '')
        if name:
            return name
    raise UnknownPullRequests(f"{remote}'s address isn't a GitHub repository")


def _parse(url):
    """Return host/owner/name from a remote address, such as git@github.com:owner/name.git, or None."""
    scp = re.fullmatch(r'(?:[^@/]+@)?([^/:]+):([^/].*)', url)  # host:owner/name, the short form ssh uses
    host, path = scp.groups() if scp else (urlparse(url).hostname or '', urlparse(url).path)
    parts = path.strip('/').removesuffix('.git').split('/')
    return f'{host.lower()}/{parts[0]}/{parts[1]}' if host and len(parts) == 2 and all(parts) else None


def _list(place, *filters):
    """Return gh's list of open pull requests in the repository, narrowed by the filters."""
    command = ['gh', 'pr', 'list', '--repo', place, '--state', 'open', '--limit', '100', '--json', FIELDS, *filters]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60,
                                env={**os.environ, 'GH_PROMPT_DISABLED': '1'})
    except FileNotFoundError:
        raise UnknownPullRequests("gh isn't installed") from None
    except subprocess.TimeoutExpired:
        raise UnknownPullRequests("gh didn't answer within a minute") from None
    if result.returncode != 0:
        raise UnknownPullRequests(_first_line(result.stderr) or f'gh exited with code {result.returncode}')
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise UnknownPullRequests("gh's answer wasn't the JSON this script expects") from None


def _head_of(pr):
    """Return the owner/name of the repository a pull request comes from, in lower case."""
    owner = (pr.get('headRepositoryOwner') or {}).get('login', '')
    name = (pr.get('headRepository') or {}).get('name', '')
    return f'{owner}/{name}'.lower()


def _line(pr, direction):
    return f"#{pr['number']} {pr['title']} ({direction}): {pr['url']}"


def _first_line(text):
    return next((' '.join(line.split()) for line in text.splitlines() if line.strip()), '')
