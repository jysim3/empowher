"""Persona kit core: keeps an app's persona pages fed from what people say, with no working
session doing the bookkeeping. Standard library only. Nothing here knows about tmux, a
chat tool or a model: the caller hands in an `ask(prompt) -> text` function.

    note(personas_dir, log_dir, words, context, relayed, ask, ...)   one remark in, at most one log line out
    due(rows, page)            which patterns have reached DAYS different days (pure)
    pending_text(rows)         the log lines not yet on the page (a round reads these)
    folded(log_dir, ...)       mark lines as on the page (only a rewrite does this)

How it fits together (why: concepts/persona.md):

- A small model answers one question about one remark with one line of JSON. It never
  edits a page. The answer is one line in `<log_dir>/<persona>.jsonl`, outside git.
- Counting is plain code: different days per pattern, from the log plus the dates the
  page already carries on its Observations lines.
- When something is due, `note` says so in what it returns. The adapter decides what
  that starts: a rewrite chat (adapters/tmux.py) or a note to the owner
  (adapters/change_page.py).

Folders: `personas_dir` holds README.md (the index) and one page per persona, in git.
`log_dir` holds `<persona>.jsonl`, `seen.txt` and `rewrite.json`, on the app's side,
never in git.
"""
import datetime, hashlib, json, os, re, time
from pathlib import Path

VERSION = "1.1"    # bump on any change to behaviour or formats; check.py compares installed copies

DAYS = 3            # different days before a pattern moves
BACKLOG = 15        # waiting lines that make a rewrite due on their own, so decisions do not pile up
MAX_CHARS = 1500    # longer than this is a paste or an agent's brief, not a remark
INDEX = "README.md"
TAKEN_BACK = ("undone", "abandoned")    # outcomes that stop a request counting as something the person wants
DUE_MARK = "[persona due]"

WHO = """Below is the list of the people an app called {app} is built for, then a short exchange: \
{context_label} and what {typer} typed next.

Whose habits, fears or goals does the typed message tell us about? Answer with ONE line of JSON \
and nothing else:

{{"persona": "<one of: {slugs}, or none>"}}

{rule}
Most messages are none: a go-ahead, a question, a bug report, an instruction with no taste in it.

=== THE PEOPLE ===
{index}

=== {context_head} ===
{context}

=== WHAT WAS TYPED ===
{words}
"""

ASK = """Below is a page describing {title}, a person an app called {app} is built for, then a short \
exchange: {context_label} and what {typer} typed next.

Decide what the message says about THE PERSON ON THE PAGE, set against the page. Answer with ONE line \
of JSON and nothing else:

{{"kind": "none" | "trait" | "observation" | "new" | "direct", "id": "<T3, O1 or N2; empty for new, direct and none>", \
"side": "for" | "against", "pattern": "<for new or direct only: one sentence about the person, starting with You>"}}

- none: a go-ahead, a question, an instruction with no taste in it, a bug report, or text an agent \
wrote (a brief with headers, file paths, background). Most messages are none.
- trait: it clearly shows (for) or clearly goes against (against) one trait T<n> on the page.
- observation: the same, for an Observations line O<n> or a pending pattern N<n> listed below.
- new: it shows a habit, fear or goal of the person that no trait, observation or pending pattern covers.
- direct: a plain decision about the app ("remove X", "I don't want Y", "keep Z on the desk"). \
Put the decision in "pattern" as one sentence. If a message both decides something and shows a trait, \
answer direct.
{rule}
Only count what the message itself shows. Do not guess. If unsure, answer none. Never put a name, \
number, address or secret in "pattern".

=== THE PAGE ===
{page}

=== PENDING PATTERNS (not on the page yet) ===
{pending}

=== {context_head} ===
{context}

=== WHAT WAS TYPED ===
{words}
"""

RULE_DIRECT = ""
RULE_RELAYED = ("- The one typing is the app's owner, NOT the person on the page. Count the message only when it "
                "passes on what that person said or did (\"they said…\", \"he kept doing X\"). The owner's own taste is none.\n")
RULE_REQUEST = ("- Every message here is a request for a change to the app. Asking for a thing is not a decision: answer "
                "direct only when the message turns something down, takes something away or reverses an earlier choice.\n")


# ---- the index and the pages

def personas(personas_dir):
    """[{slug, title, line, relayed}] from the index. One persona per line that links a page:
    `- [The designer](designer.md) · who: … · theirs: … · words: relayed`.
    With no index, every other .md file in the folder is a persona whose words arrive directly."""
    d = Path(personas_dir)
    out = []
    try:
        text = (d / INDEX).read_text()
    except OSError:
        text = ""
    for line in text.splitlines():
        m = re.match(r"\s*[-*]\s*\[([^\]]+)\]\(([\w.-]+)\.md\)", line)
        if not m or not (d / f"{m.group(2)}.md").is_file():
            continue
        w = re.search(r"words:\s*\**(direct|relayed)", line, re.I)
        out.append({"slug": m.group(2), "title": m.group(1).strip(), "line": line.strip(),
                    "relayed": bool(w and w.group(1).lower() == "relayed")})
    if not out and not text:
        for p in sorted(d.glob("*.md")):
            if p.name != INDEX:
                out.append({"slug": p.stem, "title": p.stem, "line": f"- [{p.stem}]({p.name})", "relayed": False})
    return out


def read_page(personas_dir, slug):
    try:
        return (Path(personas_dir) / f"{slug}.md").read_text()
    except OSError:
        return ""


def page_days(page):
    """{O1: {"for": {days}, "against": {days}}} from the page's Observations lines."""
    out = {}
    for line in (page or "").splitlines():
        m = re.match(r"- \*\*(O\d+)\.", line)
        if not m:
            continue
        parts = re.split(r"·\s*against:", line, maxsplit=1)
        day = r"\d{4}-\d{2}-\d{2}"
        out[m.group(1)] = {"for": set(re.findall(day, parts[0])),
                           "against": set(re.findall(day, parts[1])) if len(parts) > 1 else set()}
    return out


def page_names(page):
    """{T3: "Your attention is the scarce thing", O1: "You want files that…"}: the sentence behind an id,
    so a due pattern can be named without quoting anyone."""
    out = {}
    for line in (page or "").splitlines():
        m = re.match(r"#{2,4}\s*(T\d+)\.\s*(.+)", line) or re.match(r"- \*\*(O\d+)\.\s*(.+?)\*\*", line)
        if m:
            out.setdefault(m.group(1), m.group(2).strip())
    return out


# ---- the log (one file per persona)

def log_path(log_dir, slug):
    return Path(log_dir) / f"{slug}.jsonl"


def read_log(log_dir, slug):
    out = []
    try:
        for line in open(log_path(log_dir, slug)):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    except OSError:
        pass
    return out


def write_log(log_dir, slug, rows):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    tmp = str(log_path(log_dir, slug)) + ".tmp"
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, log_path(log_dir, slug))


def append_log(log_dir, slug, row):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    with open(log_path(log_dir, slug), "a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _live(rows):
    return [r for r in rows if not r.get("folded") and r.get("outcome") not in TAKEN_BACK]


def pending_text(rows):
    lines = []
    for r in _live(rows):
        tag = {"direct": "DECISION"}.get(r.get("kind"), f"{r.get('id')} {r.get('side', 'for')}")
        note = f" [{r['pattern']}]" if r.get("pattern") else ""
        via = " · relayed" if r.get("via") == "relayed" else ""
        lines.append(f"- {r.get('day')} · {tag}{note}{via} · \"{r.get('words', '')}\"")
    return "\n".join(lines)


def new_patterns(rows):
    """N ids with their sentence, for the model to match later remarks against."""
    seen = {}
    for r in _live(rows):
        if str(r.get("id", "")).startswith("N") and r.get("pattern"):
            seen.setdefault(r["id"], r["pattern"])
    return seen


def next_n(rows):
    nums = [int(r["id"][1:]) for r in rows if re.fullmatch(r"N\d+", str(r.get("id", "")))]
    return f"N{max(nums, default=0) + 1}"


def due(rows, page):
    """[(id, side, days, pattern)] for every pattern seen on DAYS different days, plus a ("backlog", …)
    entry when too many lines wait. Pure: the caller hands in one persona's log rows and page text.
    Days come from the page's Observations lines plus the waiting log lines. A request the person
    took back (outcome undone or abandoned) is not counted."""
    live = _live(rows)
    days = {}       # (id, side) -> set of days
    names = {}
    for ident, d in page_days(page).items():
        days[(ident, "for")] = set(d["for"])
        days[(ident, "against")] = set(d["against"])
    for r in live:
        if r.get("kind") == "direct" or not r.get("id"):
            continue
        days.setdefault((r["id"], r.get("side") or "for"), set()).add(r.get("day"))
        if r.get("pattern"):
            names.setdefault(r["id"], r["pattern"])
    titles = page_names(page)
    out = []
    for (ident, side), ds in sorted(days.items()):
        if len(ds) < DAYS:
            continue
        if ident.startswith("T") and side == "for":
            continue                      # a trait seen again is not news
        if not any(r.get("id") == ident and (r.get("side") or "for") == side for r in live):
            continue                      # nothing new since the page was last written
        out.append((ident, side, sorted(ds), names.get(ident) or titles.get(ident, "")))
    # A trait seen again changes nothing on the page, so it does not add to the backlog.
    waiting = [r for r in live if not (r.get("kind") == "trait" and (r.get("side") or "for") == "for")]
    if len(waiting) >= BACKLOG:
        out.append(("backlog", "for", [], f"{len(waiting)} remarks wait to be folded into the page"))
    return out


def due_all(personas_dir, log_dir):
    """{slug: [(id, side, days, pattern)]} for every persona with something due."""
    out = {}
    for p in personas(personas_dir):
        items = due(read_log(log_dir, p["slug"]), read_page(personas_dir, p["slug"]))
        if items:
            out[p["slug"]] = items
    return out


def folded(log_dir, slugs, upto=None, only=None):
    """Mark waiting lines as on the page. `upto` (a timestamp) leaves later lines waiting;
    `only` is a set of (id, side) to fold, for a handover of some patterns. Returns {slug: (folded, total)}."""
    out = {}
    for slug in slugs:
        rows = read_log(log_dir, slug)
        if not rows:
            continue
        for r in rows:
            if upto is not None and r.get("at", 0) > upto:
                continue
            if only is not None and (r.get("id") or "", r.get("side") or "for") not in only:
                continue
            r["folded"] = True
        write_log(log_dir, slug, rows)
        out[slug] = (sum(1 for r in rows if r.get("folded")), len(rows))
    return out


def set_outcome(log_dir, slugs, ref, outcome):
    """Record how a request ended (applied, undone, abandoned) on the lines it produced. Returns how many changed."""
    n = 0
    for slug in slugs:
        rows = read_log(log_dir, slug)
        hit = [r for r in rows if ref and r.get("ref") == ref and r.get("outcome") != outcome]
        for r in hit:
            r["outcome"] = outcome
        if hit:
            write_log(log_dir, slug, rows)
            n += len(hit)
    return n


# ---- the one open rewrite (a guard the adapters share)

def rewrite_open(log_dir, within=86400):
    """The record of a rewrite started in the last day and not finished, or None."""
    try:
        rec = json.load(open(Path(log_dir) / "rewrite.json"))
    except (OSError, ValueError):
        return None
    return rec if time.time() - rec.get("at", 0) < within else None


def rewrite_started(log_dir, what):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    json.dump({"at": int(time.time()), "due": what}, open(Path(log_dir) / "rewrite.json", "w"))


def rewrite_done(log_dir):
    """Returns when the rewrite started (so `folded` leaves later lines waiting), and clears the guard."""
    p = Path(log_dir) / "rewrite.json"
    try:
        at = json.load(open(p)).get("at")
    except (OSError, ValueError):
        at = None
    try:
        p.unlink()
    except OSError:
        pass
    return at


# ---- one remark

def worth(words, skip_prefixes=()):
    """Is this worth a model call? Cheap checks only; the model still answers "none" for most."""
    w = (words or "").strip()
    if not w:
        return False
    if w[0] in "<#/[":
        return False                      # injected text, a brief, a slash command, a rewrite prompt
    if any(w.startswith(p) for p in skip_prefixes):
        return False                      # the app's own reports, named by the adapter
    if len(w) > MAX_CHARS or len(w.split()) < 3:
        return False                      # a paste or brief; or "go", "merge it", "build it"
    return True


def _one_json(text):
    for line in reversed((text or "").strip().splitlines()):
        line = line.strip().strip("`")
        if line.startswith("{") and line.endswith("}"):
            try:
                a = json.loads(line)
            except ValueError:
                return None
            return a if isinstance(a, dict) else None
    return None


def parse_answer(text):
    """The model's one JSON line -> a clean dict, or None when it is unusable or says none."""
    a = _one_json(text)
    if a is None:
        return None
    kind = str(a.get("kind") or "").lower()
    ident = str(a.get("id") or "").strip().upper()
    side = "against" if str(a.get("side") or "").lower() == "against" else "for"
    pattern = re.sub(r"\s+", " ", str(a.get("pattern") or "")).strip()[:300]
    if kind == "trait" and re.fullmatch(r"T\d+", ident):
        return {"kind": "trait", "id": ident, "side": side, "pattern": ""}
    if kind == "observation" and re.fullmatch(r"[ON]\d+", ident):
        return {"kind": "observation", "id": ident, "side": side, "pattern": ""}
    if kind in ("new", "direct") and pattern:
        return {"kind": kind, "id": "", "side": "for", "pattern": pattern}
    return None


def parse_who(text, slugs):
    """The model's {"persona": "<slug>"} -> a slug from the index, or None."""
    a = _one_json(text)
    who = str((a or {}).get("persona") or "").strip().lower()
    for s in slugs:
        if s.lower() == who:
            return s
    return None


def _labels(relayed, context_label):
    typer = "the app's owner" if relayed else "the person"
    return {"typer": typer, "context_label": context_label or "what they were answering (cut short)",
            "context_head": "WHAT THEY WERE ANSWERING (end of it)"}


def who_question(app, people, context, words, relayed=None, context_label=""):
    """The first question when an app has several personas: whose remark is this? Index only, no pages."""
    if relayed is None:
        rule = ("Each line says how that person's words arrive. \"words: direct\" means the one typing IS that person. "
                "\"words: relayed\" means the one typing is the app's owner: pick that person only when the message passes "
                "on what they said or did.")
    elif relayed:
        rule = ("The one typing is the app's owner, not one of these people. Pick a person only when the message passes on "
                "what they said or did.")
    else:
        rule = "The one typing is one of these people. Pick the one whose part of the app the message is about."
    return WHO.format(app=app, slugs=", ".join(p["slug"] for p in people), rule=rule,
                      index="\n".join(p["line"] for p in people), context=context or "(none)", words=words,
                      **_labels(relayed, context_label))


def question(app, title, page, pending, context, words, relayed=False, context_label="", request=False):
    """The one question about one remark, set against one persona's page."""
    rule = (RULE_RELAYED if relayed else RULE_DIRECT) + (RULE_REQUEST if request else "")
    return ASK.format(app=app, title=title, rule=rule, page=page, pending=pending or "(none)",
                      context=context or "(none)", words=words, **_labels(relayed, context_label))


def seen_before(log_dir, key):
    """True when this remark was already handled; otherwise remembers it. Most remarks are "none" and never logged."""
    p = Path(log_dir) / "seen.txt"
    try:
        if key in p.read_text().split():
            return True
    except OSError:
        pass
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    with open(p, "a") as fh:
        fh.write(key + "\n")
    return False


def note(personas_dir, log_dir, words, context, relayed, ask, *, app="the app", persona=None, at=None,
         sid="", who="", ref="", context_label="", request=False, skip_prefixes=()):
    """One remark in, at most one log line out. Never edits a page.

    personas_dir, log_dir   the two folders (see the top of this file)
    words                   what was typed
    context                 what it replied to: the end of the assistant's reply, or the screen they were on
    relayed                 False: the one typing is the persona. True: the owner passing on what the persona
                            said or did. None: per persona, as the index says ("words: direct | relayed")
    ask                     ask(prompt) -> text, the caller's small model. May raise; that is reported, not raised
    persona                 the slug, when the caller already knows whose remark it is (skips the first question)
    who                     for a group persona: a made-up label for which person said it. Never a name
    ref                     the caller's id for this request, so set_outcome() can find the line later
    request                 True when every message is a request for a change (an app's own Change page)

    Returns {"status": "skipped" | "seen" | "no personas" | "none" | "failed" | "logged", "persona", "row",
    "due": [(id, side, days, pattern)], "detail"}."""
    words = (words or "").strip()
    out = {"status": "skipped", "persona": persona or "", "row": None, "due": [], "detail": ""}
    if not worth(words, skip_prefixes):
        return out
    at = int(at or time.time())
    key = hashlib.sha1(f"{sid}:{ref}:{at}:{words}".encode()).hexdigest()[:16]
    if seen_before(log_dir, key):
        return dict(out, status="seen")
    people = personas(personas_dir)
    if not people:
        return dict(out, status="no personas")
    try:
        if persona:
            chosen = next((p for p in people if p["slug"] == persona), None)
        elif len(people) == 1:
            chosen = people[0]
        else:
            chosen_slug = parse_who(ask(who_question(app, people, context, words, relayed, context_label)),
                                    [p["slug"] for p in people])
            chosen = next((p for p in people if p["slug"] == chosen_slug), None)
        if not chosen:
            return dict(out, status="none", detail="nobody's remark")
        slug = chosen["slug"]
        via = chosen["relayed"] if relayed is None else bool(relayed)
        page = read_page(personas_dir, slug)
        if not page:
            return dict(out, status="failed", persona=slug, detail="no page")
        pend = "\n".join(f"- {k}. {v}" for k, v in new_patterns(read_log(log_dir, slug)).items())
        ans = parse_answer(ask(question(app, chosen["title"], page, pend, context, words, via, context_label, request)))
    except Exception as e:  # noqa: BLE001  the caller's model failed: say so, never raise into a hook or a request
        return dict(out, status="failed", detail=f"{type(e).__name__}: {e}"[:200])
    if not ans:
        return dict(out, status="none", persona=slug)
    rows = read_log(log_dir, slug)
    if ans["kind"] == "new":
        ans["id"] = next_n(rows)
    row = {"at": at, "day": f"{datetime.date.fromtimestamp(at):%Y-%m-%d}", "sid": sid,
           "words": re.sub(r"\s+", " ", words)[:600], **ans, "folded": False,
           "persona": slug, "via": "relayed" if via else "direct"}
    if who:
        row["who"] = who
    if ref:
        row["ref"] = ref
    append_log(log_dir, slug, row)
    return dict(out, status="logged", persona=slug, row=row, due=due(rows + [row], page))


# ---- carrying a due pattern across a wall by hand

def due_note(slug, item):
    """One line the owner can paste into a chat on the other side: the pattern sentence and its days, never
    anyone's words. `item` is (id, side, days, pattern); a decision is ("", "for", [day], sentence)."""
    ident, side, days, pattern = item
    tag = f"{ident} {side}" if ident else "DECISION"
    return f"{DUE_MARK} {slug} · {tag} · {', '.join(days)} · {pattern}".rstrip(" ·")


def parse_due_note(text):
    """[(slug, id, side, [days], pattern)] for every due line in a pasted message."""
    out = []
    for line in (text or "").splitlines():
        m = re.search(re.escape(DUE_MARK) + r"\s*([\w.-]+)\s*·\s*(DECISION|[TON]\d+ (?:for|against))\s*·\s*([\d, -]*?)\s*(?:·\s*(.*))?$", line.strip())
        if not m:
            continue
        ident, _, side = m.group(2).partition(" ")
        days = re.findall(r"\d{4}-\d{2}-\d{2}", m.group(3))
        if days:
            out.append((m.group(1), "" if ident == "DECISION" else ident, side or "for", days, (m.group(4) or "").strip()))
    return out


def take_due_note(personas_dir, log_dir, text, at=None):
    """Log a pasted due line as one waiting line per day, so the count carries across. No model call.
    A pattern the other side numbered N<n> gets this side's next N. Returns the slugs that got lines."""
    known = {p["slug"] for p in personas(personas_dir)}
    got = []
    at = int(at or time.time())
    for slug, ident, side, days, pattern in parse_due_note(text):
        if slug not in known:
            continue
        rows = read_log(log_dir, slug)
        if ident.startswith("N"):
            same = [k for k, v in new_patterns(rows).items() if v == pattern]
            ident = same[0] if same else next_n(rows)
        kind = "direct" if not ident else "trait" if ident.startswith("T") else "observation"
        have = {(r.get("id"), r.get("side") or "for", r.get("day")) for r in rows if r.get("via") == "handed over"}
        for day in days:
            if (ident, side, day) in have:
                continue
            append_log(log_dir, slug, {"at": at, "day": day, "sid": "", "words": "(a pattern handed over from the app's own log)",
                                       "kind": kind, "id": ident, "side": side, "pattern": pattern, "folded": False,
                                       "persona": slug, "via": "handed over"})
        got.append(slug)
    return got
