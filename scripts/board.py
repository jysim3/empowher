#!/usr/bin/env python3
"""GitHub Issues workflow helper for jysim3/empowher (stdlib + gh only)."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
from datetime import datetime, timezone

REPO = "jysim3/empowher"
BOARD_URL = "https://github.com/jysim3/empowher/issues"
PHASES = ["Todo", "Investigating", "Coding", "Reviewing", "Done"]
PHASE_PREFIX = "workflow:"
DRY_RUN = False


def gh(*args: str, input_text: str | None = None) -> str:
    command = ["gh", *args]
    if DRY_RUN:
        print("DRY RUN:", shlex.join(command))
        if input_text:
            print(input_text)
        return ""
    try:
        result = subprocess.run(command, input=input_text, text=True, capture_output=True, check=True)
    except FileNotFoundError:
        sys.exit("gh is not installed; install it, then run `gh auth login`.")
    except subprocess.CalledProcessError as error:
        message = (error.stderr or error.stdout).strip()
        if "scope" in message.lower() or "authentication" in message.lower():
            sys.exit(f"GitHub authentication failed: {message}\nRun: gh auth refresh -h github.com -s repo")
        sys.exit(message or f"gh exited {error.returncode}")
    return result.stdout


def issue_rows(state: str = "all") -> list[dict]:
    if DRY_RUN:
        return []
    raw = gh("issue", "list", "--repo", REPO, "--state", state, "--limit", "200",
             "--json", "number,title,body,state,labels,url")
    return json.loads(raw)


def phase(row: dict) -> str:
    names = {label["name"] for label in row.get("labels", [])}
    return next((p for p in reversed(PHASES) if PHASE_PREFIX + p in names),
                "Done" if row.get("state") == "CLOSED" else "Todo")


def resolve(ref: str) -> dict:
    token = ref.removeprefix("#")
    if token.isdigit():
        if DRY_RUN:
            return {"number": int(token), "title": f"Dry-run issue #{token}", "labels": [], "state": "OPEN"}
        raw = gh("issue", "view", token, "--repo", REPO, "--json", "id,number,title,body,state,labels,url,comments")
        return json.loads(raw)
    matches = [r for r in issue_rows() if ref.casefold() in r["title"].casefold()]
    exact = [r for r in matches if r["title"].casefold() == ref.casefold()]
    matches = exact or matches
    if len(matches) != 1:
        sys.exit(f"Expected one item for {ref!r}; found {len(matches)}. Use an issue number.")
    return matches[0]


def ensure_label(name: str) -> None:
    gh("label", "create", name, "--repo", REPO, "--color", "D4C5F9", "--force")


def set_phase(row: dict, wanted: str, allow_downgrade: bool = False) -> None:
    current = phase(row)
    if not allow_downgrade and PHASES.index(wanted) < PHASES.index(current):
        print(f"#{row['number']} remains {current}; start never downgrades an item.")
        return
    ensure_label(PHASE_PREFIX + wanted)
    existing = {label["name"] for label in row.get("labels", [])}
    for old in PHASES:
        if old != wanted and PHASE_PREFIX + old in existing:
            gh("issue", "edit", str(row["number"]), "--repo", REPO, "--remove-label", PHASE_PREFIX + old)
    gh("issue", "edit", str(row["number"]), "--repo", REPO, "--add-label", PHASE_PREFIX + wanted)


def session_id() -> str:
    return next((os.environ[key] for key in ("CLAUDE_SESSION_ID", "CODEX_THREAD_ID", "CODEX_SESSION_ID")
                 if os.environ.get(key)), "unknown")


def session_stamp() -> str:
    tmux = os.environ.get("TMUX_PANE", "none")
    return ("<!-- sourdough-session -->\n## Session stamp\n"
            f"- Session: `{session_id()}`\n- Directory: `{pathlib.Path.cwd()}`\n"
            f"- tmux pane: `{tmux}`\n- Picked up: {datetime.now(timezone.utc).isoformat()}")


def command_list(_: argparse.Namespace) -> None:
    if DRY_RUN:
        gh("issue", "list", "--repo", REPO, "--state", "open", "--limit", "200", "--json", "number,title,body,state,labels,url")
        return
    for row in issue_rows("open"):
        print(f"#{row['number']}\t{phase(row)}\t{row['title']}")


def command_find(args: argparse.Namespace) -> None:
    needle = args.keywords.casefold()
    if DRY_RUN:
        gh("issue", "list", "--repo", REPO, "--state", "all", "--search", args.keywords)
        return
    for row in issue_rows():
        if needle in (row["title"] + "\n" + (row.get("body") or "")).casefold():
            print(f"#{row['number']}\t{phase(row)}\t{row['title']}")


def command_create(args: argparse.Namespace) -> None:
    labels = [PHASE_PREFIX + args.status]
    for value in (args.type, args.priority, args.size):
        if value:
            labels.append(value)
    for label in labels:
        ensure_label(label)
    output = gh("issue", "create", "--repo", REPO, "--title", args.title, "--body", args.body,
                *sum((["--label", label] for label in labels), []))
    if DRY_RUN:
        return
    number = int(output.rstrip("/").rsplit("/", 1)[-1])
    print(output.strip())
    if args.parent:
        parent = resolve(args.parent)
        child = resolve(str(number))
        try:
            gh("api", "--method", "POST", f"repos/{REPO}/issues/{parent['number']}/sub_issues",
               "-F", f"sub_issue_id={child['id']}")
        except SystemExit as error:
            print(f"Issue #{number} was created, but its parent link failed: {error}", file=sys.stderr)
            raise
    if args.start:
        start_item(resolve(str(number)))


def start_item(row: dict) -> None:
    gh("issue", "edit", str(row["number"]), "--repo", REPO, "--add-assignee", "@me")
    set_phase(row, "Investigating")
    sid = session_id()
    comments = row.get("comments", [])
    already = any(f"Session: `{sid}`" in c.get("body", "") for c in comments) if sid != "unknown" else False
    if not already:
        gh("issue", "comment", str(row["number"]), "--repo", REPO, "--body", session_stamp())
    print(f"Started #{row['number']}: {row['title']}")


def command_start(args: argparse.Namespace) -> None:
    start_item(resolve(args.item))


def command_status(args: argparse.Namespace) -> None:
    row = resolve(args.item)
    set_phase(row, args.phase, allow_downgrade=True)
    print(f"#{row['number']} -> {args.phase}")


def command_commit_link(args: argparse.Namespace) -> None:
    row = resolve(args.item)
    print(f"Board: {BOARD_URL}\nItem: {row['title']}\nCloses: #{row['number']}")


def command_handover(args: argparse.Namespace) -> None:
    row = resolve(args.item)
    body = ("## Session handover\n"
            f"### Done\n{args.done}\n\n### Broken / unresolved\n{args.broken}\n\n"
            f"### Do NOT re-investigate\n{args.avoid}\n\n### Next step\n{args.next}")
    if args.pr:
        body += f"\n\nPR: {args.pr}"
    gh("issue", "comment", str(row["number"]), "--repo", REPO, "--body", body)
    print(f"Posted handover to #{row['number']}")


def command_resume(args: argparse.Namespace) -> None:
    row = resolve(args.item)
    comments = row.get("comments")
    if comments is None and not DRY_RUN:
        row = resolve(str(row["number"]))
        comments = row.get("comments", [])
    stamps = [c["body"] for c in (comments or []) if "<!-- sourdough-session -->" in c.get("body", "")]
    if not stamps:
        sys.exit("No recorded session for this item.")
    latest = stamps[-1]
    values = dict(line[2:].split(":", 1) for line in latest.splitlines() if line.startswith("- "))
    sid = values["Session"].strip().strip("`")
    directory = values["Directory"].strip().strip("`")
    harness = "codex" if os.environ.get("CODEX_THREAD_ID") else "claude"
    print(f"cd {shlex.quote(directory)} && {harness} resume {shlex.quote(sid)}")


def command_sessions(_: argparse.Namespace) -> None:
    if DRY_RUN:
        gh("issue", "list", "--repo", REPO, "--state", "open", "--comments")
        return
    now = datetime.now(timezone.utc)
    for row in issue_rows("open"):
        full = resolve(str(row["number"]))
        stamps = [c for c in full.get("comments", []) if "<!-- sourdough-session -->" in c.get("body", "")]
        if not stamps:
            continue
        age = now - datetime.fromisoformat(stamps[-1]["createdAt"].replace("Z", "+00:00"))
        state = "resumable" if age.days < 1 else "stale"
        print(f"#{row['number']}\t{state}\t{row['title']}")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="print gh calls without contacting GitHub")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list").set_defaults(func=command_list)
    f = sub.add_parser("find"); f.add_argument("keywords"); f.set_defaults(func=command_find)
    c = sub.add_parser("create"); c.add_argument("--title", required=True); c.add_argument("--body", required=True)
    c.add_argument("--type"); c.add_argument("--priority"); c.add_argument("--size")
    c.add_argument("--status", choices=PHASES, default="Todo"); c.add_argument("--parent"); c.add_argument("--start", action="store_true"); c.set_defaults(func=command_create)
    for name, func in (("start", command_start), ("commit-link", command_commit_link), ("resume", command_resume)):
        q = sub.add_parser(name); q.add_argument("item"); q.set_defaults(func=func)
    s = sub.add_parser("status"); s.add_argument("item"); s.add_argument("phase", choices=PHASES); s.set_defaults(func=command_status)
    h = sub.add_parser("handover"); h.add_argument("item"); h.add_argument("--done", required=True); h.add_argument("--broken", required=True)
    h.add_argument("--avoid", required=True); h.add_argument("--next", required=True); h.add_argument("--pr"); h.set_defaults(func=command_handover)
    sub.add_parser("sessions").set_defaults(func=command_sessions)
    return p


def main() -> None:
    global DRY_RUN
    args = parser().parse_args()
    DRY_RUN = args.dry_run
    args.func(args)


if __name__ == "__main__":
    main()
