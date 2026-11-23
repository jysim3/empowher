#!/usr/bin/env python3
"""Persona kit, chat adapter: feeds the core from what the owner types in a coding chat, and starts
one visible rewrite chat when a pattern is due.

    tmux.py note --hook        the app's own UserPromptSubmit hook runs this on every prompt, with
                               Claude Code's payload on stdin. It reads the payload, then carries on
                               in the background, so the prompt is never delayed
    tmux.py note <turn file>   the same from a JSON record (prompt, prompt_at, reply, cwd, session_id)
    tmux.py pending            the log lines not yet on a page (a persona round reads these)
    tmux.py due                which patterns have reached 3 different days
    tmux.py folded             a rewrite chat runs this once its page commit has landed

The app declares itself. There is no list of apps anywhere: the app is found from the chat's
folder. Walk up to the repo root; from a git worktree go to the main checkout (pages are read
there, so every chat sees the landed page, not a branch's); look for the settings file beside the
pages, `docs/personas/kit.json`. No file: this is not an app with the kit, do nothing. A repo
nested inside another is its own app or none; the outer repo's file does not claim it.

    {"app": "shuttle", "words": "relayed", "kit": "tools/persona", "skip": ["I ran this in "]}

Every key is optional, and none is tied to one machine:

    app      the app's name in prompts and in the default log folder (default: the repo folder's name)
    words    "direct", "relayed", or "index" to go by each persona's index line (default index)
    skill    the round skill's name (default persona-round)
    kit      where this copy lives, from the repo root, for the rewrite prompt (default: found from this file)
    model    the small model (default haiku)
    skip     prefixes of the app's own reports that are never remarks
    start    the command that opens a chat (default jig-start; it is called as
             `<start> --dir <repo> --worktree --name "persona update" <prompt>`)
    logs     the log folder, outside git (default ~/.local/share/persona-kit/<app>)
    runlog   default <logs>/run.log

When a rewrite is due and `start` is not on this machine, `pending` and `due` say so in their first
line, and the working session passes it on (the round skill, step 4).

Nothing mixes between apps or personas: each app has its own log folder, each persona its own log.
"""
import datetime, json, os, shutil, subprocess, sys, time
from pathlib import Path

try:
    from .. import core
except ImportError:      # run as a script
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import core

SETTINGS = Path("docs") / "personas" / "kit.json"    # in the app, beside its pages
WORKDIR = Path.home() / ".cache" / "persona-kit"     # an empty folder for the model call to run in
STALE = 120          # a turn record older than this kept an earlier prompt

REWRITE = """[persona rewrite] The persona log of {app} has patterns that are due. Load the `{skill}` skill and \
follow `rewrite.md` beside it exactly. Due now:

{due}

Start with `python3 {kit}/adapters/tmux.py pending` and `python3 {kit}/adapters/tmux.py due`. \
Do not ask anyone to read or approve a page. End with one short reply saying what moved."""

NO_START_MARK = "REWRITE DUE:"
NO_START = (NO_START_MARK + " a persona rewrite is due and no chat could be started for it on this machine "
            "(`{name}` not found). Tell the owner: open a chat in this repo and say \"persona rewrite\".")


def repo_root(path):
    """The nearest folder at or above `path` that holds `.git`, or None."""
    for d in [path, *path.parents]:
        if (d / ".git").exists():
            return d
    return None


def main_checkout(root):
    """The main checkout of the repo `root` belongs to: itself, unless `root` is a git worktree."""
    git = root / ".git"
    try:
        if git.is_file():
            gitdir = root / git.read_text().split("gitdir:", 1)[1].strip()      # an absolute path stays as it is
            common = (gitdir / (gitdir / "commondir").read_text().strip()).resolve()
            if common.name == ".git":
                return common.parent
    except (OSError, IndexError):
        pass        # a submodule, a bare repo's worktree, something odd: the folder stands for itself
    return root


def _path(value, base):
    p = Path(str(value)).expanduser()
    return p if p.is_absolute() else base / p


def find_app(cwd):
    """The app this folder belongs to, from its own settings file, or None. See the top of this file."""
    if not cwd:
        return None
    try:
        here = Path(cwd).expanduser().resolve()
    except OSError:
        return None
    root = repo_root(here)
    if root:
        main, rel = main_checkout(root), here.relative_to(root)
        # The main checkout first. A worktree's own file counts only while main has none (the kit
        # is being installed on a branch), so an install can be tried before it lands.
        tries = [(base, d) for base in dict.fromkeys((main, root))
                 for d in [base / rel, *(base / rel).parents] if d == base or base in d.parents]
    else:
        tries = [(None, d) for d in [here, *here.parents]]
    for base, d in tries:
        f = d / SETTINGS
        if not f.is_file():
            continue
        try:
            row = json.load(open(f))
        except (OSError, ValueError):
            return None
        if not isinstance(row, dict):
            return None
        base = base or d
        name = str(row.get("app") or base.name)
        logs = _path(row.get("logs") or Path.home() / ".local" / "share" / "persona-kit" / name, base)
        return {**row, "app": name, "dir": base, "personas": f.parent, "logs": logs,
                "runlog": _path(row.get("runlog") or logs / "run.log", base)}
    return None


def kit_path(app):
    """Where the kit lives, as the rewrite prompt should name it: from the repo root when it can be."""
    if app.get("kit"):
        return str(app["kit"])
    kit = Path(__file__).resolve().parent.parent
    root = repo_root(kit)
    return str(kit.relative_to(root)) if root and root != kit else str(kit)


def starter(app):
    """(name, path or None) of the command that opens a chat."""
    name = str(app.get("start") or "jig-start")
    exe = shutil.which(os.path.expanduser(name))
    if not exe and (Path.home() / ".local" / "bin" / name).is_file():
        exe = str(Path.home() / ".local" / "bin" / name)
    return name, exe


def stuck(app):
    """The line to pass on when a rewrite is due and this machine cannot open a chat for it; "" otherwise."""
    name, exe = starter(app)
    if exe or core.rewrite_open(app["logs"]) or not core.due_all(app["personas"], app["logs"]):
        return ""
    return NO_START.format(name=name)


def runlog(app, msg):
    try:
        app["runlog"].parent.mkdir(parents=True, exist_ok=True)
        with open(app["runlog"], "a") as fh:
            fh.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    except OSError:
        pass


def asker(model):
    def ask(prompt):
        WORKDIR.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["claude", "-p", "--model", model, "--setting-sources", "project",
                            "--no-session-persistence", "--tools", ""],
                           input=prompt, capture_output=True, text=True, cwd=WORKDIR, timeout=120,
                           # so the call's own prompt does not come back through the hook
                           env=dict(os.environ, PERSONA_KIT_NO_HOOK="1", JIG_NO_HOOK="1"))
        if r.returncode:
            raise RuntimeError(f"model rc={r.returncode} {r.stderr.strip()[:160]}")
        return r.stdout
    return ask


def due_lines(due_by_slug):
    return "\n".join(f"- {slug} · {i} ({s}): {', '.join(d)} {p}".rstrip()
                     for slug, items in due_by_slug.items() for i, s, d, p in items)


def start_rewrite(app, due_by_slug):
    """Start the one visible rewrite chat, unless one was started in the last day and is unfinished."""
    what = [f"{slug}:{i}" for slug, items in due_by_slug.items() for i, *_ in items]
    if os.environ.get("PERSONA_KIT_DRY"):
        runlog(app, f"dry: would start a rewrite chat for {what}")
        return False
    if core.rewrite_open(app["logs"]):
        return False
    name, exe = starter(app)
    if not exe:
        # Not silent: `pending` and `due` say it in their first line (stuck), and a round passes it on.
        runlog(app, f"due, but no chat could be started (`{name}` not found): {what}")
        return False
    prompt = REWRITE.format(app=app["app"], skill=app.get("skill") or "persona-round", kit=kit_path(app),
                            due=due_lines(due_by_slug))
    try:
        r = subprocess.run([exe, "--dir", str(app["dir"]), "--worktree", "--name", "persona update", prompt],
                           capture_output=True, text=True,
                           env={k: v for k, v in os.environ.items() if k not in ("PERSONA_KIT_NO_HOOK", "JIG_NO_HOOK")})
    except OSError as e:
        runlog(app, f"due, but no chat could be started ({e}): {what}")
        return False
    if r.returncode:
        runlog(app, f"{name} rc={r.returncode} {(r.stderr or r.stdout).strip()[:200]}")
        return False
    core.rewrite_started(app["logs"], what)
    runlog(app, f"rewrite chat started for {what}")
    return True


def last_reply(transcript):
    """The end of the assistant's last text in a Claude Code transcript; "" when it cannot be read."""
    try:
        with open(transcript, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 400_000))
            lines = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("type") != "assistant":
            continue
        content = (rec.get("message") or {}).get("content") or []
        text = "".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text") \
            if isinstance(content, list) else str(content)
        if text.strip():
            return text
    return ""


def detach():
    """Carry on in the background, so the hook returns at once. False in the process that should just exit."""
    if not hasattr(os, "fork"):
        return True                       # no fork on this system: run in line, the hook waits for the model
    if os.fork():
        return False
    os.setsid()
    null = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(null, fd)
    return True


def note(rec):
    """One prompt from a chat. `rec` has prompt, prompt_at, reply, cwd, session_id."""
    app = find_app(rec.get("cwd"))
    if not app:
        return None
    words, at = (rec.get("prompt") or "").strip(), int(rec.get("prompt_at") or time.time())
    if time.time() - at > STALE:
        return None
    # A due line pasted from an app's own log (adapters/change_page.py) is counted by code, with no model call.
    took = core.take_due_note(app["personas"], app["logs"], words, at) if core.DUE_MARK in words else []
    if took:
        runlog(app, f"handed over: lines for {took}")
        res = {"status": "handed over", "persona": ",".join(took)}
    else:
        mode = app.get("words") or "index"
        res = core.note(app["personas"], app["logs"], words, (rec.get("reply") or "")[-1500:],
                        None if mode == "index" else mode == "relayed", asker(app.get("model") or "haiku"),
                        app=app["app"], at=at, sid=rec.get("session_id") or "",
                        context_label="the assistant's last reply in a coding chat about the app (cut short)",
                        skip_prefixes=tuple(app.get("skip") or ()))
        if res["status"] in ("skipped", "seen"):
            return res
        row = res.get("row")
        runlog(app, f"{row['persona']} {row['kind']} {row['id']} {row['side']}: {words[:60]!r}" if row
               else f"{res['status']}{' ' + res['detail'] if res.get('detail') else ''}: {words[:60]!r}")
    due = core.due_all(app["personas"], app["logs"])
    if due:
        start_rewrite(app, due)
    return res


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else ""
    if cmd == "note" and len(argv) > 1:
        if os.environ.get("PERSONA_KIT_NO_HOOK"):
            return 0
        try:
            if argv[1] == "--hook":
                p = json.load(sys.stdin)
                rec = {"prompt": p.get("prompt"), "prompt_at": int(time.time()), "cwd": p.get("cwd"),
                       "session_id": p.get("session_id"), "reply": last_reply(p.get("transcript_path") or "")}
            else:
                rec = json.load(open(argv[1]))
        except (OSError, ValueError, AttributeError):
            return 0
        if not isinstance(rec, dict) or (argv[1] == "--hook" and not detach()):
            return 0
        note(rec)
        return 0
    if cmd in ("pending", "due", "folded"):
        app = find_app(os.getcwd())
        if not app:
            print(f"no persona kit here: no readable {SETTINGS} in this repo (from a worktree, in its main checkout)")
            return 1
        slugs = [p["slug"] for p in core.personas(app["personas"])]
        warn = stuck(app) if cmd != "folded" else ""
        if warn:
            print(warn + "\n")
        if cmd == "pending":
            parts = [(s, core.pending_text(core.read_log(app["logs"], s))) for s in slugs]
            parts = [(s, t) for s, t in parts if t]
            # One persona: the bare lines. Several: a header per persona, so a round can cut out its own.
            print("\n\n".join(t if len(slugs) == 1 else f"## {s}\n{t}" for s, t in parts) or "(nothing waiting)")
        elif cmd == "due":
            print(due_lines(core.due_all(app["personas"], app["logs"])) or "(nothing due)")
        else:
            # Only what the rewrite chat could have read: a remark logged after it started stays waiting.
            upto = core.rewrite_done(app["logs"]) or time.time()
            done = core.folded(app["logs"], slugs, upto=upto)
            print("\n".join(f"{s}: {a} of {b} lines are folded" for s, (a, b) in done.items()) or "(no log yet)")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
