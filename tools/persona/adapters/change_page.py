"""Persona kit, Change page adapter: for an app whose users ask for changes inside the app itself.
No tmux and no fixed model: the app hands in its own `ask(prompt) -> text`.

    request(personas_dir, log_dir, text, ask, ref=..., on_due=...)   after a request is planned
    outcome(personas_dir, log_dir, ref, "applied" | "undone" | "abandoned", on_due=...)   when it is known

What crosses back to the app, and nothing else: `on_due(lines, items)` gets the pattern sentence and
its days. `lines` are ready to send to the owner as they are (core.due_note); pasted into a coding
chat on the repo's side, the chat adapter counts them with no model call. The raw request never
leaves `log_dir`, which stays on the app's side of any privacy wall. This file reads only the two
folders it is given.

Neither call raises and neither blocks anything: a failure is returned as {"status": "failed"} and
the person's change carries on. Call them after the work the person is waiting for, or from a
background thread.
"""
import re
import sys
from pathlib import Path

try:
    from .. import core
except ImportError:      # imported from a flat copy
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import core

OUTCOMES = ("applied", "undone", "abandoned")


def _hand_over(personas_dir, log_dir, on_due):
    """Tell the app about every pattern that is due and every plain decision, once each.
    A line is marked folded here once the app has taken it: on this side, folded means handed over."""
    sent = []
    for p in core.personas(personas_dir):
        slug = p["slug"]
        rows = core.read_log(log_dir, slug)
        live = [r for r in rows if not r.get("folded") and r.get("outcome") not in core.TAKEN_BACK]
        items = [i for i in core.due(rows, core.read_page(personas_dir, slug)) if i[0] != "backlog"]
        # A plain decision applies at once (it does not wait for 3 days), unless the request is still open.
        decisions = [r for r in live if r.get("kind") == "direct" and r.get("pattern")
                     and (not r.get("ref") or r.get("outcome") == "applied")]
        items += [("", "for", [r.get("day")], r["pattern"]) for r in decisions]
        if not items:
            continue
        lines = [core.due_note(slug, i) for i in items]
        if on_due is None or on_due(lines, [{"persona": slug, "id": i, "side": s, "days": d, "pattern": pt}
                                            for i, s, d, pt in items]) is False:
            continue                      # nobody took it: it stays waiting for the next call
        ids = {(i, s) for i, s, _, _ in items if i}
        for r in rows:
            if (r.get("id") and (r["id"], r.get("side") or "for") in ids) or any(r is x for x in decisions):
                r["folded"] = True
        core.write_log(log_dir, slug, rows)
        sent += lines
    return sent


def request(personas_dir, log_dir, text, ask, *, ref, app="the app", persona=None, page="", who="", at=None, on_due=None):
    """A request the person typed into the app's Change page. `ref` is the app's id for it, `page` what they
    were looking at, `persona` the slug when the app knows who is signed in. Text between <pasted> tags is
    dropped before anything is asked or logged."""
    try:
        own = re.sub(r"<pasted>.*?</pasted>", " ", text or "", flags=re.S).strip()
        res = core.note(personas_dir, log_dir, own, page, False, ask, app=app, persona=persona, at=at,
                        ref=str(ref), who=who, request=True,
                        context_label="the screen they were on when they asked for a change")
        res["sent"] = _hand_over(personas_dir, log_dir, on_due) if res["status"] == "logged" else []
        return res
    except Exception as e:  # noqa: BLE001  the feedback call can only add; it never stops a change
        return {"status": "failed", "detail": f"{type(e).__name__}: {e}"[:200], "sent": []}


def outcome(personas_dir, log_dir, ref, result, *, on_due=None):
    """How the request ended. `undone` and `abandoned` stop its lines counting; `applied` lets a decision go out."""
    try:
        if result not in OUTCOMES:
            return {"status": "failed", "detail": f"outcome must be one of {OUTCOMES}", "sent": []}
        slugs = [p["slug"] for p in core.personas(personas_dir)]
        n = core.set_outcome(log_dir, slugs, str(ref), result)
        return {"status": "recorded" if n else "none", "changed": n,
                "sent": _hand_over(personas_dir, log_dir, on_due) if n else []}
    except Exception as e:  # noqa: BLE001
        return {"status": "failed", "detail": f"{type(e).__name__}: {e}"[:200], "sent": []}
