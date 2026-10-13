#!/usr/bin/env python3
"""Find Claude Code conversations missing from `claude agents` and bring them back as rows.

Usage:
  restore-session.py find [WORDS ...] [--cwd PATH] [--limit N] [--include-listed]
  restore-session.py restore SESSION_ID [--name NAME] [--permission-mode MODE] [--allow-copy] [--dry-run]

find prints one JSON object whose `results` are conversations ranked by how well
they match WORDS (title, prompts, summary, and conversation text), or newest
first when no words are given. Each result has a `status`:
  hidden            not in the dashboard; `restore` brings it back
  swapped           open inside row X because /resume switched X to it
  replaced          row X is saved as this conversation but shows another one
  switched_away     row X started as this conversation, then /resume moved it
  open_in_terminal  open in a terminal session
  listed            already a row (only shown with --include-listed)
A result whose title is already another row's name has `name_in_use_by`.

restore checks the status again and, for `hidden`, runs
  claude --bg --resume <id> --permission-mode <mode> --name <name>
from the conversation's original folder, then waits for the row to appear.
<name> is --name, or else the conversation's title. Another row must not
already use it, since /resume leaves old row names on conversations.
It prints one JSON object. Exit codes: 0 restored (or dry run), 1 error,
2 not found or ambiguous, 3 already listed, 4 blocked by another row or
terminal, or the name is already used by another row.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
PROJECTS_DIR = CONFIG_DIR / "projects"
JOBS_DIR = CONFIG_DIR / "jobs"

# Later entries win, so a /rename beats the row name, which beats the auto title.
TITLE_ENTRIES = (
    ("summary", "summary"),
    ("ai-title", "aiTitle"),
    ("agent-name", "agentName"),
    ("custom-title", "customTitle"),
)
MODES = ("acceptEdits", "auto", "default", "dontAsk", "plan")
STOPWORDS = {
    "about", "and", "agent", "back", "bring", "chat", "conversation", "for", "from",
    "hidden", "lost", "one", "related", "restore", "row", "session", "that", "the",
    "this", "unhide", "was", "where", "with",
}
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
TITLE_TAG = re.compile(r"\[[^\]]*\]")
NEW_ROW = re.compile(r"backgrounded\s*\S\s*([0-9a-f]{8})")
SESSION_ID = re.compile(r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    find = commands.add_parser("find", help="list conversations that match some words")
    find.add_argument("words", nargs="*", help="keywords; leave empty for newest first")
    find.add_argument("--cwd", help="only conversations started in this folder or below it")
    find.add_argument("--limit", type=int, default=8)
    find.add_argument("--include-listed", action="store_true", help="also show rows already in the dashboard")

    restore = commands.add_parser("restore", help="bring one conversation back as a row")
    restore.add_argument("session_id", help="full session id, or a unique prefix of at least 8 characters")
    restore.add_argument("--name", help="name for the restored row instead of the conversation's title")
    restore.add_argument("--permission-mode", choices=MODES, default="auto")
    restore.add_argument("--allow-copy", action="store_true", help="allow a copy with a new id for switched_away")
    restore.add_argument("--dry-run", action="store_true", help="show the checks and command without launching")

    args = parser.parse_args()
    if args.command == "find":
        return run_find(args)
    return run_restore(args)


def run_find(args):
    words = keywords(args.words)
    scope = expand(args.cwd) if args.cwd else None
    rows, warning = load_rows()
    current = os.environ.get("CLAUDE_CODE_SESSION_ID")
    results, listed = [], 0
    for path in transcript_paths():
        if path.stem == current:
            continue
        info = read_transcript(path, words)
        if info is None or not in_scope(info["cwd"], scope):
            continue
        status, row = status_of(info["id"], rows)
        if status == "listed" and not args.include_listed:
            listed += 1
            continue
        score, matched = rank(info, words)
        if words and score == 0:
            continue
        result = describe(info, status, row, score, matched)
        owner = name_owner(result["title"], rows) if status in ("hidden", "switched_away") else None
        if owner:
            result["name_in_use_by"] = owner["row"]
        results.append(result)
    results.sort(key=lambda r: (r["score"], r["last_active"]), reverse=True)
    output = {
        "query": words,
        "scope": scope or "all folders",
        "results": results[: max(args.limit, 1)],
        "more": max(len(results) - args.limit, 0),
        "skipped_listed": listed,
    }
    if warning:
        output["warning"] = warning
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def run_restore(args):
    path = find_transcript(args.session_id)
    if isinstance(path, str):
        return report(2, ok=False, status="not_found", message=path)
    info = read_transcript(path, [])
    if info is None:
        return report(2, ok=False, status="not_found", message=f"{path} has no conversation to restore")
    rows, warning = load_rows()
    if warning:
        return report(1, ok=False, status="error", message=f"cannot check the dashboard safely: {warning}")

    status, row = status_of(info["id"], rows)
    blocked = blocked_message(status, row, info, args.allow_copy)
    if blocked:
        code, fields = blocked
        return report(code, ok=False, session_id=info["id"], title=title_of(info), status=status, **fields)

    name = args.name or (title_of(info) if info["titles"] else None)
    owner = name_owner(name, rows) if name else None
    if owner:
        return report(4, ok=False, session_id=info["id"], title=title_of(info), status="name_in_use",
                      name=name, row=owner["row"], row_name=owner.get("name"),
                      fix='restore again with --name "<a different name>"',
                      message=f'row {owner["row"]} is already named "{owner.get("name")}"; '
                              f"pick a different name so the two rows can be told apart")

    cwd = info["cwd"]
    if not cwd or not Path(cwd).is_dir():
        return report(1, ok=False, session_id=info["id"], status="error",
                      message=f"the conversation's folder {cwd or '(unknown)'} no longer exists")
    claude = shutil.which("claude")
    if not claude:
        return report(1, ok=False, status="error", message="`claude` is not on PATH")

    command = [claude, "--bg", "--resume", info["id"], "--permission-mode", args.permission_mode]
    if info["agent"]:
        command += ["--agent", info["agent"]]
    if name:
        command += ["--name", name]
    shown = ["claude"] + command[1:]
    if args.dry_run:
        return report(0, ok=True, dry_run=True, session_id=info["id"], title=title_of(info),
                      name=name, status=status, cwd=cwd, command=shown)

    try:
        launched = subprocess.run(command, cwd=cwd, stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as error:
        return report(1, ok=False, status="error", command=shown, message=f"launch failed: {error}")
    output = ANSI.sub("", launched.stdout + launched.stderr).strip()
    match = NEW_ROW.search(output)
    if launched.returncode != 0 or not match:
        return report(1, ok=False, status="error", command=shown, message=output or f"exit code {launched.returncode}")

    new_row = match.group(1)
    copy = "started a copy" in output
    visible = wait_for_row(new_row)
    return report(0, ok=True, row=new_row, session_id=info["id"], title=title_of(info), name=name, cwd=cwd,
                  permission_mode=args.permission_mode, copy=copy, visible=visible,
                  command=shown, attach=f"claude attach {new_row}", output=output)


def blocked_message(status, row, info, allow_copy):
    name = row and (row.get("name") or row["row"])
    if status == "listed":
        return 3, {"row": row["row"], "row_name": name,
                   "message": f"already in the dashboard as row {row['row']} ({name})"}
    if status == "open_in_terminal":
        return 4, {"pid": row.get("pid"),
                   "message": f"open in a terminal session (pid {row.get('pid')}); exit it there, then retry"}
    if status == "swapped":
        return 4, {"row": row["row"], "row_name": name, "fix": f"claude respawn {row['row']}",
                   "then": "run restore again",
                   "message": f"open inside row {row['row']} because /resume switched that row to it; "
                              f"restarting the row returns it to its own conversation and frees this one"}
    if status == "replaced":
        return 4, {"row": row["row"], "row_name": name, "fix": f"claude respawn {row['row']}",
                   "then": "nothing; the row shows this conversation again",
                   "message": f"row {row['row']} is saved as this conversation but /resume switched it to another"}
    if status == "switched_away" and not allow_copy:
        return 4, {"row": row["row"], "row_name": name, "fix": "restore again with --allow-copy",
                   "message": f"row {row['row']} started as this conversation and was later moved to another; "
                              f"it can only come back as a copy with a new id"}
    return None


def load_rows():
    """Merge saved job state with the dashboard's live view. Returns (rows, warning)."""
    rows = {}
    for state_file in JOBS_DIR.glob("*/state.json"):
        try:
            state = json.loads(state_file.read_text())
        except (OSError, ValueError):
            continue
        job = state_file.parent.name
        rows[job] = {
            "row": job,
            "name": state.get("name"),
            "original": state.get("sessionId"),
            "saved": state.get("resumeSessionId") or state.get("sessionId"),
            "live": None,
            "kind": "background",
        }
    try:
        listing = subprocess.run(["claude", "agents", "--json", "--all"], stdin=subprocess.DEVNULL,
                                 capture_output=True, text=True, timeout=60)
        live_rows = json.loads(listing.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        return list(rows.values()), f"`claude agents --json --all` failed: {error}"
    for live in live_rows:
        key = live.get("id") or f"pid-{live.get('pid')}"
        row = rows.setdefault(key, {"row": key, "name": None, "original": None, "saved": None})
        row["live"] = live.get("sessionId")
        row["name"] = live.get("name") or row["name"]
        row["kind"] = live.get("kind") or row.get("kind")
        row["pid"] = live.get("pid")
    return list(rows.values()), None


def name_owner(name, rows):
    """The row whose name matches, ignoring case and extra spaces."""
    wanted = " ".join(name.split()).casefold()
    for row in rows:
        if row.get("name") and " ".join(row["name"].split()).casefold() == wanted:
            return row
    return None


def shown_session(row):
    """The conversation a row is showing right now.

    A running row's live session is the truth. Its saved state does not change
    when /resume switches the row, so it can point at a conversation the row no
    longer shows, including the row's original one.
    """
    return row["live"] or row["saved"]


def status_of(session_id, rows):
    for row in rows:
        if row["live"] == session_id and row["kind"] != "background":
            return "open_in_terminal", row
    for row in rows:
        shown = shown_session(row)
        if shown == session_id:
            return ("swapped" if row["saved"] and shown != row["saved"] else "listed"), row
    for row in rows:
        if row["saved"] == session_id:
            return "replaced", row
    for row in rows:
        if row["original"] == session_id:
            return "switched_away", row
    return "hidden", None


def transcript_paths():
    if not PROJECTS_DIR.is_dir():
        return []
    return [p for p in PROJECTS_DIR.glob("*/*.jsonl") if SESSION_ID.match(p.stem)]


def find_transcript(session_id):
    wanted = session_id.strip().lower()
    if len(wanted) < 8:
        return "give at least the first 8 characters of the session id"
    matches = [p for p in transcript_paths() if p.stem.startswith(wanted)]
    if not matches:
        return f"no conversation with id {wanted} under {PROJECTS_DIR}"
    if len(matches) > 1:
        return f"{wanted} matches {len(matches)} conversations; give more of the id"
    return matches[0]


def read_transcript(path, words):
    """Summarize one transcript. Returns None when it has no real user prompt."""
    info = {
        "id": path.stem, "cwd": None, "titles": {}, "agent": None, "first_prompt": None,
        "last_prompt": None, "summary": None, "last_active": None, "turns": 0,
        "hits": dict.fromkeys(words, 0),
    }
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return None
    with handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict):
                read_entry(entry, info, words)
    if info["turns"] == 0:
        return None
    if info["last_active"] is None:
        info["last_active"] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    return info


def read_entry(entry, info, words):
    kind = entry.get("type")
    for entry_type, key in TITLE_ENTRIES:
        if kind == entry_type and entry.get(key):
            info["titles"][entry_type] = entry[key]
    if kind == "last-prompt" and entry.get("lastPrompt"):
        info["last_prompt"] = entry["lastPrompt"]
    elif kind == "agent-setting" and entry.get("agentSetting"):
        info["agent"] = entry["agentSetting"]
    elif kind == "system" and entry.get("subtype") == "away_summary" and entry.get("content"):
        info["summary"] = entry["content"]
        count_hits(info, words, entry["content"])
    if kind not in ("user", "assistant") or entry.get("isSidechain"):
        return
    if info["cwd"] is None and entry.get("cwd"):
        info["cwd"] = entry["cwd"]
    stamp = entry.get("timestamp")
    if stamp and (info["last_active"] is None or stamp > info["last_active"]):
        info["last_active"] = stamp
    text = message_text(entry)
    if not text:
        return
    if kind == "user":
        if entry.get("isMeta") or text.startswith("<"):
            return
        info["turns"] += 1
        info["first_prompt"] = info["first_prompt"] or text
    count_hits(info, words, text)


def message_text(entry):
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(parts).strip()
    return ""


def count_hits(info, words, text):
    lowered = text.lower()
    for word in words:
        info["hits"][word] += lowered.count(word)


def rank(info, words):
    # Bracketed title tags such as "[On-duty]" name a category shared by many
    # conversations, so a match there counts for little.
    title_text = title_of(info).lower()
    tags = " ".join(TITLE_TAG.findall(title_text))
    title = TITLE_TAG.sub(" ", title_text)
    first = (info["first_prompt"] or "").lower()
    recent = f"{info['last_prompt'] or ''} {info['summary'] or ''}".lower()
    score, matched = 0.0, {}
    for word in words:
        places = []
        if word in title:
            score += 10
            places.append("title")
        elif word in tags:
            score += 2
            places.append("title tag")
        if word in first:
            score += 5
            places.append("first prompt")
        if word in recent:
            score += 3
            places.append("last prompt or summary")
        hits = info["hits"][word]
        if hits:
            score += min(hits, 30) / 3
            places.append(f"{hits}x in text")
        if places:
            matched[word] = places
    if words and len(matched) == len(words):
        score += 5
    return round(score, 1), matched


def describe(info, status, row, score, matched):
    result = {
        "id": info["id"],
        "title": title_of(info),
        "folder": shorten_home(info["cwd"]),
        "last_active": info["last_active"],
        "last_active_ago": ago(info["last_active"]),
        "first_prompt": clip(info["first_prompt"], 160),
        "last_prompt": clip(info["last_prompt"], 160),
        "summary": clip(info["summary"], 220),
        "prompts": info["turns"],
        "status": status,
        "score": score,
        "matched": matched,
    }
    if row:
        result["row"] = row["row"]
        result["row_name"] = row.get("name")
    return result


def title_of(info):
    for entry_type, _ in reversed(TITLE_ENTRIES):
        if info["titles"].get(entry_type):
            return info["titles"][entry_type]
    return clip(info["first_prompt"], 60) or info["id"][:8]


def keywords(raw_words):
    words = []
    for raw in raw_words:
        for word in re.split(r"[\s,]+", raw.lower()):
            word = word.strip("\"'`.!?()[]{}")
            if len(word) >= 3 and word not in STOPWORDS and word not in words:
                words.append(word)
    return words


def in_scope(cwd, scope):
    if scope is None:
        return True
    return bool(cwd) and (cwd == scope or cwd.startswith(scope.rstrip("/") + "/"))


def expand(path):
    return str(Path(path).expanduser().resolve())


def shorten_home(path):
    home = str(Path.home())
    if path and (path == home or path.startswith(home + "/")):
        return "~" + path[len(home):]
    return path


def clip(text, limit):
    if not text:
        return None
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def ago(stamp):
    try:
        then = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    seconds = max((datetime.now(timezone.utc) - then).total_seconds(), 0)
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{int(seconds // size)}{unit} ago"
    return "just now"


def wait_for_row(row, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            listing = subprocess.run(["claude", "agents", "--json", "--all"], stdin=subprocess.DEVNULL,
                                     capture_output=True, text=True, timeout=60)
            if any(r.get("id") == row for r in json.loads(listing.stdout)):
                return True
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
        time.sleep(1)
    return False


def report(code, **fields):
    print(json.dumps(fields, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
