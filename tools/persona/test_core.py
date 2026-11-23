#!/usr/bin/env python3
"""Cases for the persona kit, with made-up data and a fake model (no spend, no network).
Run: python3 persona/test_core.py"""
import json, os, shutil, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core
from adapters import change_page, tmux

bad = 0


def check(name, got, want):
    global bad
    if got != want:
        bad += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")


# ---- worth(): the cheap filter before the model call
for name, words, want in [
    ("a remark", "That's not my workflow, most are a keep", True),
    ("two words is a go-ahead", "Build it", False),
    ("three words can be a habit", "Test it first", True),
    ("injected", "<task-notification>done</task-notification> and more text", False),
    ("slash command", "/bridge leave a note", False),
    ("an agent's brief", "# Show compactions properly in the chat thread", False),
    ("a rewrite chat's own prompt", "[persona rewrite] The persona log has patterns", False),
    ("a paste", "word " * 400, False),
    ("empty", "   ", False),
]:
    check(f"worth: {name}", core.worth(words), want)
check("worth: the app's own report, named by the adapter",
      core.worth("I ran this in ~/x:\n\n```\npwd\n```", skip_prefixes=("I ran this in ",)), False)

# ---- parse_answer(): one JSON line from the model
for name, text, want in [
    ("trait against", '{"kind": "trait", "id": "t4", "side": "against", "pattern": ""}',
     {"kind": "trait", "id": "T4", "side": "against", "pattern": ""}),
    ("observation, fenced, with chatter", 'Here you go:\n```\n{"kind":"observation","id":"O1","side":"for"}\n```',
     {"kind": "observation", "id": "O1", "side": "for", "pattern": ""}),
    ("pending pattern id", '{"kind":"observation","id":"N2","side":"for"}',
     {"kind": "observation", "id": "N2", "side": "for", "pattern": ""}),
    ("new needs a sentence", '{"kind":"new","id":"","side":"for","pattern":""}', None),
    ("new", '{"kind":"new","pattern":"You  check sizes first."}',
     {"kind": "new", "id": "", "side": "for", "pattern": "You check sizes first."}),
    ("direct", '{"kind":"direct","pattern":"You do not want a digest."}',
     {"kind": "direct", "id": "", "side": "for", "pattern": "You do not want a digest."}),
    ("none", '{"kind":"none","id":"","side":"for","pattern":""}', None),
    ("trait with a made-up id", '{"kind":"trait","id":"H2","side":"for"}', None),
    ("not json", "I think this is none.", None),
    ("empty", "", None),
]:
    check(f"parse: {name}", core.parse_answer(text), want)

check("who: a slug from the index", core.parse_who('{"persona": "Organiser"}', ["player", "organiser"]), "organiser")
check("who: none", core.parse_who('{"persona": "none"}', ["player", "organiser"]), None)
check("who: a made-up slug", core.parse_who('{"persona": "coach"}', ["player", "organiser"]), None)
check("who: not json", core.parse_who("the organiser, I think", ["player", "organiser"]), None)

# ---- due(): different days, from the page's Observations lines plus the waiting log lines
PAGE = """## The traits
### T4. You take away what does not earn its place
Analysis.

## Observations
- **O1. You want files that keep themselves true.** · for: 2026-11-14 ("x"), 2026-11-23 ("y") · against: none
- **O2. You start your own reviews.** · for: 2026-10-18 ("z") · against: none
"""
check("page_days", core.page_days(PAGE),
      {"O1": {"for": {"2026-11-14", "2026-11-23"}, "against": set()}, "O2": {"for": {"2026-10-18"}, "against": set()}})
check("page_names", core.page_names(PAGE),
      {"T4": "You take away what does not earn its place", "O1": "You want files that keep themselves true.",
       "O2": "You start your own reviews."})


def row(day, ident, side="for", kind="observation", folded=False, pattern="", **more):
    return {"day": day, "id": ident, "side": side, "kind": kind, "folded": folded, "pattern": pattern, "words": "w", **more}


def ids(rows):
    return [(i, s) for i, s, _, _ in core.due(rows, PAGE)]


THREE = ("2026-11-24", "2026-11-25", "2026-11-26")
check("two days on the page, nothing new: not due", ids([]), [])
check("third day arrives for O1", ids([row("2026-11-25", "O1")]), [("O1", "for")])
check("same day again is not a third day", ids([row("2026-11-23", "O1")]), [])
check("O2 needs two more days", ids([row("2026-11-24", "O2")]), [])
check("O2 with two more days", ids([row("2026-11-24", "O2"), row("2026-11-25", "O2")]), [("O2", "for")])
check("a trait seen again is not news", ids([row(d, "T4", kind="trait") for d in THREE]), [])
check("a trait contradicted on 3 days", ids([row(d, "T4", "against", "trait") for d in THREE]), [("T4", "against")])
check("3 remarks on one day against a trait", ids([row("2026-11-24", "T4", "against", "trait")] * 3), [])
check("a new pattern on 3 days", ids([row(d, "N1", pattern="You p.") for d in THREE]), [("N1", "for")])
check("folded lines do not count", ids([row(d, "N1", folded=True) for d in THREE]), [])
check("decisions never count as a pattern", ids([row(d, "", kind="direct") for d in THREE]), [])
check("a backlog is due on its own", ids([row("2026-11-24", "", kind="direct")] * core.BACKLOG), [("backlog", "for")])
check("next_n", core.next_n([row("d", "N1"), row("d", "N7"), row("d", "O3")]), "N8")
check("next_n empty", core.next_n([]), "N1")
# extended: relayed words, the outcome signal, the sentence behind an id
check("relayed words count like any others",
      ids([row(d, "N1", pattern="You p.", via="relayed") for d in THREE]), [("N1", "for")])
check("a mix of direct and relayed days counts together",
      ids([row(THREE[0], "N1", via="relayed"), row(THREE[1], "N1", via="direct"), row(THREE[2], "N1", via="relayed")]), [("N1", "for")])
check("a request that was undone is not a day",
      ids([row(THREE[0], "N1"), row(THREE[1], "N1"), row(THREE[2], "N1", outcome="undone")]), [])
check("nor is one that was abandoned",
      ids([row(THREE[0], "N1"), row(THREE[1], "N1"), row(THREE[2], "N1", outcome="abandoned")]), [])
check("an applied request is a day",
      ids([row(THREE[0], "N1"), row(THREE[1], "N1"), row(THREE[2], "N1", outcome="applied")]), [("N1", "for")])
check("requests taken back do not fill the backlog",
      ids([row("2026-11-24", "", kind="direct", outcome="undone")] * core.BACKLOG), [])
check("a due trait is named from the page",
      core.due([row(d, "T4", "against", "trait") for d in THREE], PAGE)[0][3], "You take away what does not earn its place")
check("pending marks relayed lines and hides taken-back ones",
      core.pending_text([row("2026-11-24", "N1", pattern="You p.", via="relayed"), row("2026-11-24", "N2", outcome="undone"),
                         row("2026-11-25", "", kind="direct", pattern="You do not want X.")]),
      '- 2026-11-24 · N1 for [You p.] · relayed · "w"\n- 2026-11-25 · DECISION [You do not want X.] · "w"')

# ---- a line written by jig's first version of this code still reads (formats stay compatible)
OLD = {"at": 1763900000, "day": "2026-11-23", "sid": "abc", "words": "Test it first", "kind": "trait", "id": "T3",
       "side": "against", "pattern": "", "folded": False}
check("an old log line counts", [(i, s) for i, s, _, _ in core.due([dict(OLD, day=d) for d in THREE], "")], [("T3", "against")])

# ---- note(): several personas, relayed words, one log each
tmp = Path(tempfile.mkdtemp(prefix="persona-kit-test-"))
try:
    P, L = tmp / "personas", tmp / "logs"
    P.mkdir()
    (P / "README.md").write_text(
        "# Who this app is for\n\n"
        "- [The player](player.md) · who: plays socials · theirs: joining, the roster · words: relayed\n"
        "- [The organiser](organiser.md) · who: runs socials · theirs: the session editor, payments · words: relayed\n"
        "- [The owner](owner.md) · who: builds the app · theirs: admin · words: direct\n"
        "- [Nobody yet](missing.md) · who: no page · theirs: nothing · words: direct\n")
    for slug in ("player", "organiser", "owner"):
        (P / f"{slug}.md").write_text(f"# The {slug}\n\n### T1. You like it quick\nAnalysis.\n\n## Observations\n")
    people = core.personas(P)
    check("index: one persona per linked page that exists", [p["slug"] for p in people], ["player", "organiser", "owner"])
    check("index: how each one's words arrive", [p["relayed"] for p in people], [True, True, False])

    calls = []

    def fake(answers):
        left = list(answers)

        def ask(prompt):
            calls.append(prompt)
            return left.pop(0)
        return ask

    T0 = int(time.time()) - 60
    r = core.note(P, L, "The organisers said they hate retyping the venue", "…reply…", None,
                  fake(['{"persona": "organiser"}', '{"kind":"new","pattern":"You do not want to type the same thing twice."}']),
                  app="shuttle", at=T0, sid="s1")
    check("several personas: logged for the one the model named", (r["status"], r["persona"], r["row"]["id"]), ("logged", "organiser", "N1"))
    check("several personas: the first question shows the index, not a page", ("words: relayed" in calls[0], "### T1" in calls[0]), (True, False))
    check("several personas: the second question shows that persona's page", "# The organiser" in calls[1], True)
    check("a relayed persona's question says the owner is typing", "NOT the person on the page" in calls[1], True)
    check("the line says how the words arrived", r["row"]["via"], "relayed")
    check("one log per persona", sorted(p.name for p in L.glob("*.jsonl")), ["organiser.jsonl"])

    calls.clear()
    r = core.note(P, L, "I never want to see a wizard here", "", None,
                  fake(['{"persona": "owner"}', '{"kind":"direct","pattern":"You do not want a wizard."}']), app="shuttle", at=T0 + 1)
    check("a direct persona's line", (r["persona"], r["row"]["via"], r["row"]["kind"]), ("owner", "direct", "direct"))
    check("a direct persona's question does not talk about the owner", "NOT the person on the page" in calls[1], False)
    check("nothing mixes between personas", (len(core.read_log(L, "organiser")), len(core.read_log(L, "owner")), len(core.read_log(L, "player"))), (1, 1, 0))

    r = core.note(P, L, "Please make the build faster somehow", "", None, fake(['{"persona": "none"}']), app="shuttle", at=T0 + 2)
    check("nobody's remark: one call, no line", (r["status"], r["row"]), ("none", None))
    r = core.note(P, L, "The organisers said they hate retyping the venue", "", None, fake([]), app="shuttle", at=T0, sid="s1")
    check("the same remark twice is asked once", r["status"], "seen")
    r = core.note(P, L, "They said it twice, they hate retyping", "", True,
                  fake(['{"kind":"observation","id":"N1","side":"for"}']), app="shuttle", persona="organiser", at=T0 + 3, who="organiser-b")
    check("a known persona skips the first question; the pending pattern is matched", (r["status"], r["row"]["id"], r["row"]["who"]), ("logged", "N1", "organiser-b"))

    def broken(prompt):
        raise TimeoutError("model timed out")
    r = core.note(P, L, "This one will fail in the model", "", False, broken, persona="owner", at=T0 + 4)
    check("a failing model is reported, not raised", r["status"], "failed")
    r = core.note(tmp / "empty", L, "A remark for a folder with no pages", "", False, fake([]), at=T0 + 5)
    check("no personas folder", r["status"], "no personas")

    # due across days, then folded
    day = 86400
    for n in (1, 2):
        core.note(P, L, f"They said again {n} that retyping is the worst part", "", True,
                  fake(['{"kind":"observation","id":"N1","side":"for"}']), persona="organiser", at=T0 + n * day)
    check("due_all: only the persona whose pattern reached 3 days",
          {s: [(i, sd) for i, sd, _, _ in v] for s, v in core.due_all(P, L).items()}, {"organiser": [("N1", "for")]})
    core.rewrite_started(L, ["organiser:N1"])
    check("a rewrite is open", bool(core.rewrite_open(L)), True)
    upto = core.rewrite_done(L)
    core.folded(L, ["organiser", "owner", "player"], upto=upto)
    check("folded leaves later lines waiting", [r["folded"] for r in core.read_log(L, "organiser")], [True, True, False, False])
    check("the guard is cleared", core.rewrite_open(L), None)

    # ---- the Change page adapter: its own ask, the outcome signal, only the sentence crosses
    L2 = tmp / "app-side"
    got = []

    def on_due(lines, items):
        got.append((lines, items))

    D0 = T0 - 5 * day
    for n, ref in enumerate(("c1", "c2", "c3")):
        res = change_page.request(P, L2, f"Put the price beside the name, request {n} <pasted>SECRET 123</pasted>",
                                  fake(['{"kind":"new","pattern":"You want the number next to the thing it belongs to."}'] if n == 0
                                       else ['{"kind":"observation","id":"N1","side":"for"}']),
                                  ref=ref, app="shuttle", persona="player", page="/roster", at=D0 + n * day, on_due=on_due)
        check(f"change page: request {n} logged", res["status"], "logged")
    check("change page: pasted text is never logged", "SECRET" in (L2 / "player.jsonl").read_text(), False)
    check("change page: the question says every message is a request", "Every message here is a request" in calls[-1], True)
    check("change page: due on the third day, called back once", len(got), 1)
    lines, items = got[0]
    check("change page: only the sentence and its days cross",
          items, [{"persona": "player", "id": "N1", "side": "for",
                   "days": sorted(f"{__import__('datetime').date.fromtimestamp(D0 + n * day):%Y-%m-%d}" for n in range(3)),
                   "pattern": "You want the number next to the thing it belongs to."}])
    check("change page: the line for the owner carries no request text", "request 0" in lines[0] or "Put the price" in lines[0], False)
    check("change page: handed-over lines do not fire again", [r["folded"] for r in core.read_log(L2, "player")], [True, True, True])

    got.clear()
    change_page.request(P, L2, "Take the weather widget away for good", fake(['{"kind":"direct","pattern":"You do not want a weather widget."}']),
                        ref="c4", persona="player", at=T0, on_due=on_due)
    check("change page: a decision waits while its request is open", got, [])
    check("change page: undone stops it going out", (change_page.outcome(P, L2, "c4", "undone", on_due=on_due)["status"], got), ("recorded", []))
    change_page.request(P, L2, "Remove the weather widget, I mean it", fake(['{"kind":"direct","pattern":"You do not want a weather widget."}']),
                        ref="c5", persona="player", at=T0 + 1, on_due=on_due)
    res = change_page.outcome(P, L2, "c5", "applied", on_due=on_due)
    check("change page: an applied decision goes out at once", [i["pattern"] for _, its in got for i in its], ["You do not want a weather widget."])
    check("change page: an unknown outcome is refused, not raised", change_page.outcome(P, L2, "c5", "exploded")["status"], "failed")
    check("change page: an outcome for a request that logged nothing", change_page.outcome(P, L2, "nope", "applied")["status"], "none")
    check("change page: a failing ask never raises", change_page.request(P, L2, "This request will fail in the model", broken, ref="c6", persona="player")["status"], "failed")

    def refuses(lines, items):
        return False
    change_page.request(P, L2, "Take the banner away too please", fake(['{"kind":"direct","pattern":"You do not want a banner."}']), ref="c7", persona="player", at=T0 + 2)
    change_page.outcome(P, L2, "c7", "applied", on_due=refuses)
    check("change page: a line nobody took stays waiting", core.read_log(L2, "player")[-1]["folded"], False)

    # ---- the owner pastes a due line into a chat on the repo's side: counted with no model call
    L3 = tmp / "repo-side"
    note_line = lines[0]
    check("due note round trip", core.parse_due_note("He keeps asking:\n" + note_line),
          [("player", "N1", "for", items[0]["days"], "You want the number next to the thing it belongs to.")])
    check("due note: a decision", core.parse_due_note(core.due_note("player", ("", "for", ["2026-11-20"], "You do not want a banner."))),
          [("player", "", "for", ["2026-11-20"], "You do not want a banner.")])
    check("take_due_note: lines for that persona", core.take_due_note(P, L3, note_line), ["player"])
    check("take_due_note: one line per day, so it is due here too",
          {s: [(i, sd) for i, sd, _, _ in v] for s, v in core.due_all(P, L3).items()}, {"player": [("N1", "for")]})
    core.take_due_note(P, L3, note_line)
    check("take_due_note: pasting it twice adds nothing", len(core.read_log(L3, "player")), 3)
    check("take_due_note: an unknown persona is ignored", core.take_due_note(P, L3, "[persona due] stranger · N1 for · 2026-11-20 · You x."), [])

    # ---- the chat adapter: the app declares itself (docs/personas/kit.json); there is no list
    def repo(path, settings=None):
        (path / ".git").mkdir(parents=True)
        if settings is not None:
            (path / "docs" / "personas").mkdir(parents=True)
            (path / "docs" / "personas" / "kit.json").write_text(json.dumps(settings) if isinstance(settings, dict) else settings)
        return path

    def worktree(main, path):       # what `git worktree add` leaves behind
        gitdir = main / ".git" / "worktrees" / path.name
        gitdir.mkdir(parents=True)
        (gitdir / "commondir").write_text("../..\n")
        path.mkdir(parents=True)
        (path / ".git").write_text(f"gitdir: {gitdir}\n")
        return path

    tmp = tmp.resolve()
    one = repo(tmp / "one", {"app": "one", "logs": str(tmp / "one-logs")})
    (one / "src" / "deep").mkdir(parents=True)
    wt = worktree(one, one / ".claude" / "worktrees" / "b")
    (wt / "docs" / "personas").mkdir(parents=True)
    (wt / "docs" / "personas" / "kit.json").write_text('{"app": "the copy on the branch"}')
    (wt / "src").mkdir()
    repo(one / "apps" / "inner", {"app": "inner", "logs": str(tmp / "inner-logs")})
    repo(one / "vendor" / "clone")
    repo(tmp / "plain")
    repo(tmp / "bare-settings", {})
    repo(tmp / "broken", "{not json")
    fresh = repo(tmp / "fresh")
    wt2 = worktree(fresh, fresh / ".claude" / "worktrees" / "install")
    (wt2 / "docs" / "personas").mkdir(parents=True)
    (wt2 / "docs" / "personas" / "kit.json").write_text('{"app": "being installed"}')
    (tmp / "loose" / "docs" / "personas").mkdir(parents=True)
    (tmp / "loose" / "docs" / "personas" / "kit.json").write_text('{"app": "loose"}')

    a = tmux.find_app(str(one))
    check("find_app: found from the main checkout", (a["app"], a["dir"], a["personas"], a["logs"], a["runlog"]),
          ("one", one, one / "docs" / "personas", tmp / "one-logs", tmp / "one-logs" / "run.log"))
    check("find_app: found from a folder inside it", tmux.find_app(str(one / "src" / "deep"))["app"], "one")
    a = tmux.find_app(str(wt / "src"))
    check("find_app: found from a worktree, with the main checkout's file and pages",
          (a["app"], a["dir"], a["personas"]), ("one", one, one / "docs" / "personas"))
    check("find_app: the deepest repo wins", tmux.find_app(str(one / "apps" / "inner"))["app"], "inner")
    check("find_app: a repo inside an app, with no file of its own, is not that app", tmux.find_app(str(one / "vendor" / "clone")), None)
    check("find_app: no file means nothing", tmux.find_app(str(tmp / "plain")), None)
    check("find_app: no folder", tmux.find_app(""), None)
    check("find_app: a file that is not JSON means nothing", tmux.find_app(str(tmp / "broken")), None)
    a = tmux.find_app(str(tmp / "bare-settings"))
    check("find_app: an empty file takes the folder's name and the default log folder",
          (a["app"], a["logs"]), ("bare-settings", Path.home() / ".local" / "share" / "persona-kit" / "bare-settings"))
    a = tmux.find_app(str(wt2))
    check("find_app: a worktree's own file counts while the main checkout has none (an install being tried)",
          (a["app"], a["dir"]), ("being installed", wt2))
    check("find_app: a folder outside git still works", tmux.find_app(str(tmp / "loose"))["app"], "loose")
    check("kit_path: the settings file's own path wins", tmux.kit_path({"kit": "tools/persona"}), "tools/persona")
    # The kit is copied into apps under other folder names, so work the answer out from this file's own place.
    here = Path(__file__).resolve().parent
    top = next((d for d in here.parents if (d / ".git").exists()), None)
    check("kit_path: otherwise from the repo root of the running copy", tmux.kit_path({}),
          str(here.relative_to(top)) if top else str(here))

    # a pasted due line through the chat adapter: counted, and a rewrite would start (dry run)
    os.environ["PERSONA_KIT_DRY"] = "1"
    shutil.copytree(P, one / "docs" / "personas", dirs_exist_ok=True)
    res = tmux.note({"prompt": "From the site:\n" + note_line, "prompt_at": int(time.time()), "cwd": str(wt), "session_id": "s9"})
    check("chat adapter: a pasted due line is handed over", res["status"], "handed over")
    check("chat adapter: the run log says a rewrite chat would start", "would start a rewrite chat for ['player:N1']" in (tmp / "one-logs" / "run.log").read_text(), True)
    check("chat adapter: an old turn record is ignored",
          tmux.note({"prompt": "I never want a wizard here", "prompt_at": 1, "cwd": str(one)}), None)
    check("chat adapter: a chat in a repo with no settings file is ignored",
          tmux.note({"prompt": "I never want a wizard here", "prompt_at": int(time.time()), "cwd": str(tmp / "plain")}), None)

    # ---- a rewrite is due and this machine has nothing that can open a chat: it is said, not swallowed
    import contextlib, io

    def run(cmd, cwd):
        out, was = io.StringIO(), os.getcwd()
        os.chdir(cwd)
        try:
            with contextlib.redirect_stdout(out):
                rc = tmux.main([cmd])
        finally:
            os.chdir(was)
        return rc, out.getvalue()

    del os.environ["PERSONA_KIT_DRY"]
    kit_json = one / "docs" / "personas" / "kit.json"
    kit_json.write_text(json.dumps({"app": "one", "logs": str(tmp / "one-logs"), "start": "no-such-chat-starter"}))
    app = tmux.find_app(str(one))
    check("no starter: the rewrite does not start", tmux.start_rewrite(app, core.due_all(app["personas"], app["logs"])), False)
    check("no starter: the run log says why", "no chat could be started (`no-such-chat-starter` not found)" in (tmp / "one-logs" / "run.log").read_text(), True)
    rc, out = run("pending", wt)
    check("no starter: `pending` says so in its first line",
          (rc, out.splitlines()[0].startswith(tmux.NO_START_MARK), 'say "persona rewrite"' in out.splitlines()[0]), (0, True, True))
    check("no starter: the waiting lines still follow", "## player\n- " in out, True)
    rc, out = run("due", one)
    check("no starter: `due` says so in its first line", (out.splitlines()[0].startswith(tmux.NO_START_MARK), "- player · N1 (for)" in out), (True, True))
    core.rewrite_started(app["logs"], ["player:N1"])
    check("no starter: quiet while a rewrite is open", tmux.stuck(app), "")
    core.rewrite_done(app["logs"])
    kit_json.write_text(json.dumps({"app": "one", "logs": str(tmp / "one-logs"), "start": "sh"}))
    rc, out = run("due", one)
    check("with a starter on the machine nothing changes", out.splitlines()[0].startswith("- player · N1 (for)"), True)
    rc, out = run("pending", one / "apps" / "inner")
    check("nothing due: no first line", out, "(nothing waiting)\n")
    rc, out = run("pending", tmp / "plain")
    check("a repo with no settings file: the commands say so", (rc, "no persona kit here" in out), (1, True))

    # ---- check.py: which installed copies are behind
    import check as kitcheck
    old = tmp / "apps" / "a" / "tools" / "persona"
    (old / "adapters").mkdir(parents=True)
    (old / "adapters" / "change_page.py").write_text("")
    (old / "core.py").write_text('VERSION = "0.9"\n')
    new = tmp / "apps" / "b" / "persona"
    (new / "adapters").mkdir(parents=True)
    (new / "adapters" / "change_page.py").write_text("")
    (new / "core.py").write_text(f'VERSION = "{core.VERSION}"\n')
    found = {str(p.relative_to(tmp / "apps")): v for p, v in kitcheck.copies([tmp / "apps"])}
    check("check: finds every copy with its version", found, {"a/tools/persona/core.py": "0.9", "b/persona/core.py": core.VERSION})
    repo(tmp / "apps" / "b", {"app": "b"})
    check("check: says which copies sit in an app that declares itself",
          {str(p.relative_to(tmp / "apps")): kitcheck.declared(p) for p, _ in kitcheck.copies([tmp / "apps"])},
          {"a/tools/persona/core.py": False, "b/persona/core.py": True})
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("FAILED" if bad else "ok: persona kit cases pass")
sys.exit(1 if bad else 0)
