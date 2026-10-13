#!/usr/bin/env python3
"""Purge dead Claude Code / Codex sessions and the data tied to them.

  purge.py jobs                          list ~/.claude/jobs rows (job id, session id, name)
  purge.py plan  --live ID [--live ID..] [--manifest F] [--no-playwright] [--playwright-profile]
  purge.py apply --manifest F

`plan` never deletes. `apply` only touches what the manifest lists, and every
path is re-checked against the allowed roots first.
"""
import argparse, glob, json, os, re, shutil, sqlite3, sys, tempfile, time

HOME = os.path.realpath(os.path.expanduser('~'))
CLAUDE = HOME + '/.claude'
CODEX = HOME + '/.codex'
PW = HOME + '/.playwright-chromium-browser'
DESKTOP = HOME + '/Library/Application Support/Claude'
ROOTS = (CLAUDE, CODEX, PW)
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
THREAD_COLS = ('thread_id', 'parent_thread_id', 'child_thread_id', 'session_id')


def size(p):
    if os.path.isfile(p) or os.path.islink(p):
        return os.lstat(p).st_size
    return sum(os.lstat(os.path.join(d, f)).st_size
               for d, _, fs in os.walk(p) for f in fs if os.path.lexists(os.path.join(d, f)))


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except Exception:
        return True


def uuid_of(name):
    m = UUID.match(name)
    return m.group(0) if m else None


def read_jsonl(p):
    try:
        with open(p) as f:
            for line in f:
                try:
                    yield line, json.loads(line)
                except ValueError:
                    yield line, None
    except FileNotFoundError:
        return


# ---------- jobs ----------
def job_rows():
    rows = []
    for sp in sorted(glob.glob(CLAUDE + '/jobs/*/state.json')):
        try:
            s = json.load(open(sp))
        except Exception:
            continue
        rows.append((os.path.basename(os.path.dirname(sp)), s.get('sessionId'), s.get('name'), s.get('state')))
    return rows


def cmd_jobs(_):
    for r in job_rows():
        print('\t'.join(str(x) for x in r))


# ---------- Claude ----------
def desktop_ids(candidates):
    """Session ids that Claude Desktop's UI storage still mentions (sidebar)."""
    hits = set()
    pat = re.compile(rb'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
    for sub in ('Local Storage', 'IndexedDB', 'Session Storage', 'claude-code-sessions'):
        for d, _, fs in os.walk(os.path.join(DESKTOP, sub)):
            for f in fs:
                try:
                    data = open(os.path.join(d, f), 'rb').read()
                except Exception:
                    continue
                for m in pat.findall(data):
                    u = m.decode()
                    if u in candidates:
                        hits.add(u)
    return hits


def plan_claude(live_args, min_age):
    cand = set()
    for pat in ('projects/*/*', 'file-history/*', 'session-env/*', 'tasks/*', 'debug/*'):
        for p in glob.glob(f'{CLAUDE}/{pat}'):
            u = uuid_of(os.path.basename(p))
            if u:
                cand.add(u)
    for _, s, _, _ in job_rows():
        if s:
            cand.add(s)
    for _, d in read_jsonl(CLAUDE + '/history.jsonl'):
        if d and d.get('sessionId'):
            cand.add(d['sessionId'])

    live, why = set(), {}

    def protect(u, reason):
        live.add(u)
        why.setdefault(u, reason)

    for a in live_args:
        for u in cand:
            if u.startswith(a):
                protect(u, 'on dashboard (--live)')
    cur = os.environ.get('CLAUDE_JOB_DIR')
    if cur:
        for jid, s, _, _ in job_rows():
            if jid == os.path.basename(cur.rstrip('/')) and s:
                protect(s, 'this session')
    for sp in glob.glob(CLAUDE + '/sessions/*.json'):
        try:
            d = json.load(open(sp))
        except Exception:
            continue
        if d.get('sessionId') and pid_alive(d.get('pid', 0)):
            protect(d['sessionId'], 'process running')
    for u in desktop_ids(cand):
        protect(u, 'in Claude Desktop UI storage')
    now = time.time()
    for p in glob.glob(CLAUDE + '/projects/*/*.jsonl'):
        u = uuid_of(os.path.basename(p))
        if u and now - os.path.getmtime(p) < min_age * 60:
            protect(u, f'active in last {min_age} min')

    purge = cand - live
    rm = []
    for u in sorted(purge):
        for pat in (f'projects/*/{u}*', f'file-history/{u}', f'session-env/{u}',
                    f'tasks/{u}', f'debug/{u}*'):
            rm += glob.glob(f'{CLAUDE}/{pat}')
    for jid, s, _, _ in job_rows():
        if s in purge:
            rm.append(f'{CLAUDE}/jobs/{jid}')
    for sp in glob.glob(CLAUDE + '/sessions/*.json'):
        try:
            d = json.load(open(sp))
        except Exception:
            continue
        if d.get('sessionId') in purge and not pid_alive(d.get('pid', 0)):
            rm.append(sp)
    filt = [{'path': CLAUDE + '/history.jsonl', 'key': 'sessionId', 'ids': sorted(purge)}]
    return purge, live, why, rm, filt


# ---------- Codex ----------
def plan_codex():
    db = CODEX + '/state_5.sqlite'
    purge, alive = set(), set()
    rm, rollout = [], []
    if os.path.exists(db):
        c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
        for i, path, arch in c.execute('select id, rollout_path, archived from threads'):
            if arch:
                purge.add(i)
                rollout.append(path)
            else:
                alive.add(i)
        c.close()
    for p in glob.glob(CODEX + '/archived_sessions/*.jsonl'):
        m = UUID.findall(os.path.basename(p))
        if m and m[-1] not in alive:
            purge.add(m[-1])
    for u in purge:
        for pat in ('sessions/**/*%s*', 'archived_sessions/*%s*', 'shell_snapshots/*%s*',
                    'generated_images/%s*', 'attachments/%s*', 'thread-writer-locks/*%s*'):
            rm += glob.glob(f'{CODEX}/{pat % u}', recursive=True)
    rm += [p for p in rollout if os.path.exists(p)]
    filt = [{'path': CODEX + '/session_index.jsonl', 'key': 'id', 'ids': sorted(purge)},
            {'path': CODEX + '/history.jsonl', 'key': 'session_id', 'ids': sorted(purge)}]
    sql = []
    for dbp in sorted(glob.glob(CODEX + '/*.sqlite') + glob.glob(CODEX + '/sqlite/*.db')):
        try:
            c = sqlite3.connect(f'file:{dbp}?mode=ro', uri=True)
            for (t,) in c.execute("select name from sqlite_master where type='table'"):
                cols = [r[1] for r in c.execute(f'pragma table_info("{t}")')]
                use = [x for x in cols if x in THREAD_COLS] or (['id'] if t == 'threads' else [])
                for col in use:
                    sql.append({'db': dbp, 'table': t, 'col': col})
            c.close()
        except Exception as e:
            print(f'  skip {dbp}: {e}', file=sys.stderr)
    return purge, sorted(set(rm)), filt, sql


# ---------- Playwright ----------
def plan_playwright(include_profile):
    if not os.path.isdir(PW):
        return []
    if os.system(f"pgrep -f '{PW}/profile' >/dev/null 2>&1") == 0:
        print('  playwright browser is running - skipping', file=sys.stderr)
        return []
    rm = glob.glob(PW + '/output/*')
    if include_profile:
        rm += glob.glob(PW + '/profile/*')
    return rm


# ---------- safety + apply ----------
def safe(p):
    r = os.path.realpath(p)
    for root in ROOTS:
        if r.startswith(root + '/') and r.count('/') >= root.count('/') + 2:
            return r
    raise SystemExit(f'refusing unsafe path: {p}')


def cmd_plan(a):
    purge_c, live_c, why, rm_c, filt_c = plan_claude(a.live, a.min_age)
    purge_x, rm_x, filt_x, sql = plan_codex()
    rm_p = [] if a.no_playwright else plan_playwright(a.playwright_profile)
    rm = sorted({safe(p) for p in rm_c + rm_x + rm_p})
    man = {'created': time.time(), 'rm': rm, 'filter': filt_c + filt_x, 'sql': sql,
           'codex_ids': sorted(purge_x)}
    job_tmp = os.environ.get('CLAUDE_JOB_DIR')
    path = a.manifest or os.path.join(job_tmp + '/tmp' if job_tmp else tempfile.gettempdir(), 'purge-manifest.json')
    json.dump(man, open(path, 'w'))
    print(f'Claude: purge {len(purge_c)} sessions, keep {len(live_c)} live')
    for u in sorted(live_c):
        print(f'  keep {u}  ({why[u]})')
    print(f'Codex: purge {len(purge_x)} archived threads')
    print(f'Playwright: {len(rm_p)} items')
    print(f'Files/dirs to delete: {len(rm)}  ({sum(size(p) for p in rm if os.path.lexists(p)) / 1e6:.1f} MB)')
    print(f'DB cleanups: {len(sql)} table/column pairs; JSONL filters: {len(man["filter"])}')
    print('manifest:', path)


def cmd_apply(a):
    man = json.load(open(a.manifest))
    if time.time() - man['created'] > 3600:
        raise SystemExit('manifest older than 1h - run plan again')
    n = 0
    for p in man['rm']:
        r = safe(p)
        if not os.path.lexists(r):
            continue
        shutil.rmtree(r) if os.path.isdir(r) and not os.path.islink(r) else os.remove(r)
        n += 1
    print('deleted', n, 'items')
    for f in man['filter']:
        p = safe(f['path'])
        ids = set(f['ids'])
        if not os.path.exists(p) or not ids:
            continue
        keep, dropped = [], 0
        for line, d in read_jsonl(p):
            if d is not None and d.get(f['key']) in ids:
                dropped += 1
            else:
                keep.append(line)
        tmp = p + '.purge.tmp'
        open(tmp, 'w').writelines(keep)
        os.chmod(tmp, os.stat(p).st_mode & 0o777)
        os.replace(tmp, p)
        print(f'{os.path.basename(p)}: dropped {dropped} lines')
    ids = man['codex_ids']
    by_db = {}
    for s in man['sql']:
        by_db.setdefault(s['db'], []).append(s)
    for dbp, items in by_db.items():
        safe(dbp)
        try:
            c = sqlite3.connect(dbp, timeout=30)
            c.execute('pragma foreign_keys=on')
            total = 0
            for s in items:
                for i in range(0, len(ids), 500):
                    chunk = ids[i:i + 500]
                    q = ','.join('?' * len(chunk))
                    total += c.execute(f'delete from "{s["table"]}" where "{s["col"]}" in ({q})', chunk).rowcount
            c.commit()
            c.close()
            print(f'{os.path.basename(dbp)}: deleted {total} rows')
        except Exception as e:
            print(f'{os.path.basename(dbp)}: FAILED ({e}) - is the Codex app running?', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('jobs').set_defaults(f=cmd_jobs)
    p = sub.add_parser('plan')
    p.add_argument('--live', action='append', default=[], help='session id or prefix on the dashboard')
    p.add_argument('--manifest')
    p.add_argument('--min-age', type=int, default=10, help='protect transcripts touched in the last N minutes')
    p.add_argument('--no-playwright', action='store_true')
    p.add_argument('--playwright-profile', action='store_true', help='also wipe browser profile (logs you out)')
    p.set_defaults(f=cmd_plan)
    q = sub.add_parser('apply')
    q.add_argument('--manifest', required=True)
    q.set_defaults(f=cmd_apply)
    a = ap.parse_args()
    if a.cmd == 'plan' and not a.live:
        raise SystemExit('plan needs at least one --live id (the dashboard rows). Refusing to guess.')
    a.f(a)


main()
