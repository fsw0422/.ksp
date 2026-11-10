"""Tests for wipe.py. They run on a throwaway home folder, never the real one."""
import contextlib, io, json, os, sys, tempfile, unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
import wipe

CLAUDE_GONE = (
    '.claude/projects/-Users-me-app/1111.jsonl',
    '.claude/projects/-Users-me-app/1111.jsonl.bak',
    '.claude/projects/-Users-me-app/1111/subagents/agent.jsonl',
    '.claude/projects/-Users-me-app/1111/tool-results/out.txt',
    '.claude/projects/-Users-me-old/2222.jsonl',
    '.claude/history.jsonl',
    '.claude/daemon.log',
    '.claude/plans/plan.md',
    '.claude/todos/todo.json',
    '.claude/file-history/1111/a.txt',
    '.claude/feedback/drafts/draft.txt',
    'Library/Application Support/Claude/claude-code-sessions/s.json',
    'Library/Application Support/Claude/local-agent-mode-sessions/x/y.json',
)
CLAUDE_KEPT = (
    '.claude/projects/-Users-me-app/memory/MEMORY.md',
    '.claude/projects/-Users-me-app/notes.txt',
    '.claude/settings.json',
    '.claude/skills/demo/SKILL.md',
    '.claude/feedback/sent.txt',
    'Library/Application Support/Claude/config.json',
)
CODEX_GONE = (
    'Documents/Codex/chat-a/out.txt',
    'Documents/Codex/.hidden',
    '.codex/sessions/2026/11/rollout.jsonl',
    '.codex/archived_sessions/old.jsonl',
    '.codex/.tmp/scratch',
    '.codex/history.jsonl',
    '.codex/session_index.jsonl',
    '.codex/state_5.sqlite',
    '.codex/state_5.sqlite-wal',
    '.codex/logs_2.sqlite',
    '.codex/.codex-global-state.json.bak1',
    'Library/Caches/Codex/cache.bin',
    'Library/Caches/com.openai.codex/cache.bin',
    'Library/Logs/com.openai.codex/app.log',
)
CODEX_KEPT = (
    'Documents/Other/keep.txt',
    '.codex/auth.json',
    '.codex/memories_1.sqlite',
    '.codex/.codex-global-state.json',
    'Library/Caches/Other/keep.bin',
)
CLAUDE_CODE = 'Claude Code (a session, claude agents, or its background daemon)'
CODEX = 'Codex (the ChatGPT app or the codex CLI)'
CLAUDE_JSON = {'userID': 'u', 'projects': {'/Users/me/app': {
    'allowedTools': [], 'lastSessionId': '1111', 'lastCost': 1.5, 'activeWorktreeSession': 'w'}}}
CODEX_TOML = '''model = "gpt"

[projects."{home}/Documents/Codex/chat-a"]
trust_level = "trusted"

[projects."{home}/projects"]
trust_level = "trusted"

[mcp_servers.demo]
command = "demo"
'''


class WipeTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = os.path.realpath(tmp.name)
        self.home = root + '/home'
        for rel in CLAUDE_GONE + CLAUDE_KEPT + CODEX_GONE + CODEX_KEPT:
            self.write(rel, 'x' * 8192)  # big enough to take disk blocks, so every row shows
        self.write('.claude.json', json.dumps(CLAUDE_JSON))
        self.write('.codex/config.toml', CODEX_TOML.format(home=self.home))
        # Config backups go to the temp folder: keep them inside the throwaway one.
        os.mkdir(root + '/tmp')
        self.addCleanup(setattr, tempfile, 'tempdir', tempfile.tempdir)
        tempfile.tempdir = root + '/tmp'

    def path(self, rel):
        return os.path.join(self.home, rel)

    def write(self, rel, text):
        os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
        with open(self.path(rel), 'w') as f:
            f.write(text)

    def read(self, rel):
        with open(self.path(rel)) as f:
            return f.read()

    def snapshot(self):
        """Every file under the home folder, with its content."""
        files = {}
        for folder, _, names in os.walk(self.home):
            for name in names:
                with open(os.path.join(folder, name)) as f:
                    files[os.path.join(folder, name)] = f.read()
        return files

    def wipe_home(self, *args, running=()):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = wipe.main(list(args), home=self.home,
                             running_apps=lambda claude, codex: list(running))
        return code, out.getvalue(), err.getvalue()

    def assert_gone(self, rels):
        self.assertEqual([r for r in rels if os.path.lexists(self.path(r))], [])

    def assert_kept(self, rels):
        self.assertEqual([r for r in rels if not os.path.lexists(self.path(r))], [])

    def test_dry_run_deletes_nothing(self):
        before = self.snapshot()
        code, out, _ = self.wipe_home(running=['Claude desktop app'])
        self.assertEqual(code, 0)
        self.assertEqual(self.snapshot(), before)
        self.assertIn('Would delete', out)
        self.assertIn('Still running (quit before deleting):\n  - Claude desktop app', out)
        self.assertIn('Dry run: nothing deleted.', out)

    def test_yes_deletes_session_data_and_keeps_the_setup(self):
        code, out, _ = self.wipe_home('--yes')
        self.assertEqual(code, 0)
        self.assert_gone(CLAUDE_GONE + CODEX_GONE)
        self.assert_kept(CLAUDE_KEPT + CODEX_KEPT)
        self.assertIn('Done: freed about', out)

    def test_yes_removes_only_project_folders_left_empty(self):
        self.wipe_home('--yes')
        self.assertFalse(os.path.exists(self.path('.claude/projects/-Users-me-old')))
        self.assertTrue(os.path.isdir(self.path('.claude/projects/-Users-me-app/memory')))

    def test_yes_refuses_while_a_tool_is_running(self):
        before = self.snapshot()
        code, _, err = self.wipe_home('--yes', running=['Claude desktop app'])
        self.assertEqual(code, 1)
        self.assertEqual(self.snapshot(), before)
        self.assertIn('quit these first, then rerun:\n  - Claude desktop app', err)

    def test_claude_only_leaves_codex_alone(self):
        toml = self.read('.codex/config.toml')
        self.wipe_home('--yes', '--claude-only')
        self.assert_gone(CLAUDE_GONE)
        self.assert_kept(CLAUDE_KEPT + CODEX_GONE + CODEX_KEPT)
        self.assertEqual(self.read('.codex/config.toml'), toml)

    def test_codex_only_leaves_claude_alone(self):
        claude_json = self.read('.claude.json')
        self.wipe_home('--yes', '--codex-only')
        self.assert_gone(CODEX_GONE)
        self.assert_kept(CODEX_KEPT + CLAUDE_GONE + CLAUDE_KEPT)
        self.assertEqual(self.read('.claude.json'), claude_json)

    def test_both_only_flags_are_rejected(self):
        with self.assertRaises(SystemExit) as stop, contextlib.redirect_stderr(io.StringIO()):
            wipe.main(['--claude-only', '--codex-only'], home=self.home)
        self.assertEqual(stop.exception.code, 2)

    def test_yes_scrubs_session_details_from_the_configs(self):
        self.wipe_home('--yes')
        self.assertEqual(json.loads(self.read('.claude.json')),
                         {'userID': 'u', 'projects': {'/Users/me/app': {'allowedTools': []}}})
        toml = self.read('.codex/config.toml')
        self.assertNotIn('Documents/Codex/chat-a', toml)
        self.assertIn(f'[projects."{self.home}/projects"]', toml)
        self.assertIn('[mcp_servers.demo]', toml)
        self.assertIn('model = "gpt"', toml)

    def test_yes_backs_up_the_configs_before_changing_them(self):
        _, out, _ = self.wipe_home('--yes')
        backup = [line for line in out.splitlines() if line.startswith('Config backups')][0]
        backup = backup.split(': ', 1)[1]
        with open(backup + '/.claude.json') as f:
            self.assertEqual(json.load(f), CLAUDE_JSON)
        with open(backup + '/config.toml') as f:
            self.assertIn('Documents/Codex/chat-a', f.read())

    def test_report_sums_paths_that_share_a_label(self):
        _, out, _ = self.wipe_home()
        self.assertIn('~/.claude/projects/*/ (transcripts, subagents, tool outputs)  [4 items]', out)
        self.assertIn('~/.codex/state_5.sqlite*  [2 items]', out)
        self.assertIn('~/.claude.json: 3 last-session keys', out)
        self.assertIn('~/.codex/config.toml: 1 [projects] entries', out)

    def test_refuses_a_linked_folder_that_leads_outside(self):
        os.makedirs(self.path('Documents/Other/sub'))
        os.symlink(self.path('Documents/Other'), self.path('.claude/projects/linked'))
        before = self.snapshot()
        with self.assertRaises(SystemExit) as stop:
            self.wipe_home('--yes')
        self.assertIn('refusing unsafe path', str(stop.exception))
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(os.path.isdir(self.path('Documents/Other/sub')))

    def running_with(self, commands, claude=True, codex=True):
        """What running() reports when these command lines are the only processes."""
        names = [os.path.basename(c.split(' --')[0]) for c in commands]
        with mock.patch.object(wipe, 'processes', return_value=(names, commands)):
            return wipe.running(claude, codex)

    def test_running_finds_each_tool(self):
        self.assertEqual(self.running_with(['/Applications/Claude.app/Contents/MacOS/Claude']),
                         ['Claude desktop app'])
        self.assertEqual(self.running_with(['/Users/me/.local/bin/claude --resume']),
                         [CLAUDE_CODE])
        self.assertEqual(self.running_with(['/Applications/ChatGPT.app/Contents/MacOS/ChatGPT']),
                         [CODEX])
        self.assertEqual(self.running_with(['/usr/local/bin/codex']), [CODEX])
        app_server = (['node'], ['node /opt/x/codex --foo app-server'])
        with mock.patch.object(wipe, 'processes', return_value=app_server):
            self.assertEqual(wipe.running(True, True), [CODEX])

    def test_running_finds_the_desktop_apps_claude_code_despite_the_space_in_its_path(self):
        bundled = '/Users/me/Library/Application Support/Claude/claude-code/2.1/claude.app/Contents/MacOS/claude'
        self.assertEqual(self.running_with([bundled + ' --output-format stream-json']), [CLAUDE_CODE])

    def test_running_finds_a_cli_that_only_renamed_its_process(self):
        with mock.patch.object(wipe, 'processes', return_value=(['node'], ['claude --resume'])):
            self.assertEqual(wipe.running(True, True), [CLAUDE_CODE])

    def test_running_ignores_lookalikes(self):
        self.assertEqual(self.running_with([
            '/bin/zsh -l', 'vim /Users/me/notes/claude codex.md',
            'python3 -I /Users/me/.claude/skills/purge-all-sessions/scripts/wipe.py --yes',
            '/Applications/Claude.app/Contents/Frameworks/Claude Helper.app/Contents/MacOS/Claude Helper',
        ]), [])

    def test_running_checks_only_the_selected_tools(self):
        everything = ['/Applications/Claude.app/Contents/MacOS/Claude', '/usr/local/bin/claude',
                      '/usr/local/bin/codex']
        self.assertEqual(self.running_with(everything), [CLAUDE_CODE, 'Claude desktop app', CODEX])
        self.assertEqual(self.running_with(everything, codex=False), [CLAUDE_CODE, 'Claude desktop app'])
        self.assertEqual(self.running_with(everything, claude=False), [CODEX])

    def test_processes_lists_names_and_command_lines(self):
        names, commands = wipe.processes()
        self.assertIn('ps', names)
        self.assertTrue(any(c.startswith('ps -axww') for c in commands))


if __name__ == '__main__':
    unittest.main()
