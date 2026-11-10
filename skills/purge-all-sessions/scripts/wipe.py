#!/usr/bin/env python3
"""Wipe all Claude Code and Codex session data, and keep the setup.

  wipe.py [--yes] [--claude-only | --codex-only]

Deletes transcripts, tool outputs, logs, caches, prompt history, and the
session details kept in ~/.claude.json and ~/.codex/config.toml. Keeps
settings, logins, skills, plugins, and memory. Dry run by default; --yes
deletes for good (no Trash). Deleting refuses to start while a selected tool
is running: open sessions would corrupt their SQLite databases or simply write
the files back.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time

# Names inside ~/.claude, the desktop app's folder, and ~/.codex.
CLAUDE = ('file-history', 'plans', 'debug', 'paste-cache', 'image-cache', 'uploads', 'session-env',
          'sessions', 'named-sessions', 'jobs', 'tasks', 'todos', 'shell-snapshots', 'backups',
          'feedback-bundles', 'usage-data', 'statsig', 'logs', 'feedback/drafts', 'history.jsonl',
          'daemon.log')
DESKTOP = ('claude-code-sessions', 'local-agent-mode-sessions')
CODEX = ('sessions', 'archived_sessions', 'sqlite', 'shell_snapshots', 'generated_images',
         'visualizations', 'attachments', 'dictation-history', 'process_manager',
         'thread-writer-locks', '.tmp', 'tmp', 'session_index.jsonl', 'history.jsonl',
         'transcription-history.jsonl')
# Versioned databases (state_5, logs_2, ...) with their -wal/-shm files.
# memories_*.sqlite is deliberately not listed.
CODEX_DB = re.compile(r'(thread_history|state|logs|queue|goals)_\d+\.sqlite')
CODEX_STATE_BACKUP = re.compile(r'\.codex-global-state\.json\.(bak|backup)')
CODEX_LIBRARY = ('Library/Caches/Codex', 'Library/Caches/com.openai.codex',
                 'Library/Logs/com.openai.codex')
# Every target must really sit inside one of these, relative to the home folder.
ROOTS = ('.claude', '.codex', 'Documents/Codex', 'Library/Application Support/Claude',
         'Library/Caches', 'Library/Logs')


# ---------- what to delete ----------
def names(folder, hidden=False):
    """Sorted names in a folder; none if it is missing."""
    try:
        return sorted(n for n in os.listdir(folder) if hidden or not n.startswith('.'))
    except OSError:
        return []


def is_real_dir(path):
    return os.path.isdir(path) and not os.path.islink(path)


def existing(targets):
    return [(label, path) for label, path in targets if os.path.lexists(path)]


def claude_targets(home):
    """(label, path) pairs. Paths sharing a label are summed into one report row.

    Per project: the transcripts plus each session's subagents/ and
    tool-results/ folders. memory/ is the only per-project folder that survives."""
    claude, app = home + '/.claude', home + '/Library/Application Support/Claude'
    label = '~/.claude/projects/*/ (transcripts, subagents, tool outputs)'
    out = []
    for project in names(claude + '/projects'):
        for name in names(f'{claude}/projects/{project}'):
            path = f'{claude}/projects/{project}/{name}'
            if '.jsonl' in name or (name != 'memory' and is_real_dir(path)):
                out.append((label, path))
    out += [(f'~/.claude/{n}', f'{claude}/{n}') for n in CLAUDE]
    out += [(f'~/Library/Application Support/Claude/{n}', f'{app}/{n}') for n in DESKTOP]
    return existing(out)


def codex_targets(home):
    """(label, path) pairs, with one row per database for its -wal/-shm files."""
    codex, docs = home + '/.codex', home + '/Documents/Codex'
    out = [('~/Documents/Codex/* (thread output folders)', f'{docs}/{n}')
           for n in names(docs, hidden=True)]
    out += [(f'~/.codex/{n}', f'{codex}/{n}') for n in CODEX]
    files = names(codex, hidden=True)
    out += [(f'~/.codex/{n}', f'{codex}/{n}') for n in files if CODEX_STATE_BACKUP.match(n)]
    out += [(f'~/.codex/{CODEX_DB.match(n).group(0)}*', f'{codex}/{n}')
            for n in files if CODEX_DB.match(n)]
    out += [(f'~/{n}', f'{home}/{n}') for n in CODEX_LIBRARY]
    return existing(out)


def check_inside_roots(path, home):
    """Stop unless the entry really sits inside a folder this script owns. A link
    planted in ~/.claude/projects could otherwise aim a recursive delete elsewhere."""
    parent = os.path.realpath(os.path.dirname(path))
    for root in ROOTS:
        real_root = os.path.realpath(os.path.join(home, root))
        if parent == real_root or parent.startswith(real_root + '/'):
            return
    raise SystemExit(f'wipe.py: refusing unsafe path: {path}')


# ---------- what blocks deleting ----------
def processes():
    """Every process, as two lists: program names and full command lines.

    Read from `ps`, not `pgrep`: on macOS pgrep leaves out its own ancestors,
    so it misses the Claude app when this runs in a terminal inside that app."""
    def column(name):
        ps = subprocess.run(['ps', '-axww', '-o', name + '='], capture_output=True, text=True,
                            check=True)
        return [line.strip() for line in ps.stdout.splitlines()]
    return [os.path.basename(path) for path in column('comm')], column('command')


def running(claude, codex):
    """One line per running app that blocks deletion."""
    names, commands = processes()
    # `claude` as the program, or as the title a CLI install gives its process.
    # The name check also covers the desktop app's own copy, whose path has a space.
    claude_code = 'claude' in names or any(re.match(r'([^ ]*/)?claude( |$)', c) for c in commands)
    codex_app = ('ChatGPT' in names or 'codex' in names
                 or any(re.search(r'/codex( .*)? app-server', c) for c in commands))
    out = []
    if claude and claude_code:
        out.append('Claude Code (a session, claude agents, or its background daemon)')
    if claude and 'Claude' in names:
        out.append('Claude desktop app')
    if codex and codex_app:
        out.append('Codex (the ChatGPT app or the codex CLI)')
    return out


# ---------- session details in config files ----------
def write_private(path, text):
    """Replace the file in one step. It holds account details, so owner-only."""
    tmp = path + '.purge-tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def scrub_claude_json(home, apply):
    """Drop per-project last-session details (lastSessionId, lastSessionFirstPrompt,
    lastCost, ...) from ~/.claude.json. Returns the key count; only apply writes."""
    path = home + '/.claude.json'
    if not os.path.exists(path):
        return 0
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    dropped = 0
    for project in data.get('projects', {}).values():
        for key in [k for k in project if k.startswith('last') or k == 'activeWorktreeSession']:
            del project[key]
            dropped += 1
    if apply and dropped:
        write_private(path, json.dumps(data, indent=2, ensure_ascii=False))
    return dropped


def scrub_codex_toml(home, apply):
    """Drop [projects."~/Documents/Codex/..."] sections (trust entries for thread
    folders, named after the chats) from ~/.codex/config.toml. Returns the
    section count; only apply writes."""
    # If the config is a link, write its target so the link survives.
    path = os.path.realpath(home + '/.codex/config.toml')
    if not os.path.exists(path):
        return 0
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    header = re.compile(r'^\s*\[')
    project = re.compile(r'^\s*\[projects\."([^"]+)"(\]|\.)')
    kept, skip, dropped = [], False, 0
    for line in lines:
        if header.match(line):
            m = project.match(line)
            skip = bool(m and m.group(1).startswith(home + '/Documents/Codex/'))
            if skip and m.group(2) == ']':
                dropped += 1
        if not skip:
            kept.append(line)
    if apply and dropped:
        write_private(path, ''.join(kept))
    return dropped


def scrub_configs(home, claude_keys, codex_sections):
    """Back up, then rewrite, the config files that hold session details."""
    backup = os.path.join(tempfile.gettempdir(), time.strftime('purge-wipe-%Y%m%d-%H%M%S'))
    os.makedirs(backup, mode=0o700, exist_ok=True)
    if claude_keys:
        shutil.copy2(home + '/.claude.json', backup)
        scrub_claude_json(home, apply=True)
    if codex_sections:
        shutil.copy2(home + '/.codex/config.toml', backup)
        scrub_codex_toml(home, apply=True)
    print(f'Config backups (cleared on reboot): {backup}')


# ---------- report and delete ----------
def blocks(path):
    try:
        return os.lstat(path).st_blocks
    except OSError:
        return 0


def kb(path):
    """Disk usage in KB, like `du -sk`, without following links."""
    total = blocks(path)
    if is_real_dir(path):
        for folder, dirs, files in os.walk(path):
            total += sum(blocks(os.path.join(folder, n)) for n in dirs + files)
    return total // 2


def human(kilobytes):
    if kilobytes >= 1048576:
        return f'{kilobytes / 1048576:.1f}G'
    if kilobytes >= 1024:
        return f'{kilobytes / 1024:.0f}M'
    return f'{kilobytes}K'


def bullets(lines):
    return '\n'.join('  - ' + line for line in lines)


def report(targets, claude_keys, codex_sections, deleting):
    """Print one row per label, and return the total in KB."""
    size, count = {}, {}
    for label, path in targets:
        size[label] = size.get(label, 0) + kb(path)
        count[label] = count.get(label, 0) + 1
    total = sum(size.values())
    print(f"{'Deleting' if deleting else 'Would delete'} ({human(total)}):")
    for label, kilobytes in size.items():
        if kilobytes:  # empty folders are still deleted, just not worth a row
            items = f'  [{count[label]} items]' if count[label] > 1 else ''
            print(f'  {human(kilobytes)}\t{label}{items}')
    if claude_keys:
        print(f'  ~/.claude.json: {claude_keys} last-session keys')
    if codex_sections:
        print(f'  ~/.codex/config.toml: {codex_sections} [projects] entries for '
              '~/Documents/Codex folders')
    return total


def delete(targets):
    """Remove every target. Returns one line per target that could not go."""
    failed = []
    for _, path in targets:
        try:
            shutil.rmtree(path) if is_real_dir(path) else os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as e:
            failed.append(f'{path}: {e}')
    return failed


def remove_empty_projects(home):
    """Project folders left empty once their sessions are gone (no memory/)."""
    projects = home + '/.claude/projects'
    for project in names(projects):
        try:
            os.rmdir(f'{projects}/{project}')
        except OSError:
            pass  # not empty, or not a folder


def parse(argv):
    ap = argparse.ArgumentParser(
        description='Wipe all Claude Code and Codex session data. Dry run unless --yes. '
                    'Quit Claude Code, claude agents, the Claude app, and Codex first.')
    ap.add_argument('--yes', action='store_true', help='delete for good (no Trash)')
    only = ap.add_mutually_exclusive_group()
    only.add_argument('--claude-only', action='store_true', help='leave Codex data alone')
    only.add_argument('--codex-only', action='store_true', help='leave Claude data alone')
    return ap.parse_args(argv)


def main(argv=None, home=None, running_apps=running):
    a = parse(argv)
    home = home or os.path.expanduser('~')
    claude, codex = not a.codex_only, not a.claude_only

    still_running = running_apps(claude, codex)
    if a.yes and still_running:
        print('wipe.py: quit these first, then rerun:\n' + bullets(still_running), file=sys.stderr)
        return 1

    targets = (claude_targets(home) if claude else []) + (codex_targets(home) if codex else [])
    for _, path in targets:
        check_inside_roots(path, home)
    claude_keys = scrub_claude_json(home, apply=False) if claude else 0
    codex_sections = scrub_codex_toml(home, apply=False) if codex else 0
    total = report(targets, claude_keys, codex_sections, deleting=a.yes)

    if not a.yes:
        if still_running:
            print('Still running (quit before deleting):\n' + bullets(still_running))
        print('Dry run: nothing deleted. Rerun with --yes to delete.')
        return 0

    if claude_keys or codex_sections:
        scrub_configs(home, claude_keys, codex_sections)
    failed = delete(targets)
    if claude:
        remove_empty_projects(home)
    if failed:
        print('wipe.py: could not delete:\n' + bullets(failed), file=sys.stderr)
    print(f'Done: freed about {human(total)}.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
