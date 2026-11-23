#!/usr/bin/env python3
"""Build the merge report page and its terminal twin from one JSON file.

    merge-report.py report.json            # writes <REPORTS_DIR>/<item>/<stamp>/index.html
    merge-report.py report.json --twin     # also prints the markdown twin to stdout (default)
    merge-report.py report.json --no-twin

Fill the CONFIG block once at install time. The Decision log rows are read from the
tracker (DECISIONS_CMD), never from the JSON, so the report cannot invent a decision.

report.json shape (HTML allowed inside strings; it is inserted as-is, so escape `<`
in prose yourself, and use <code>…</code> for names):

{
  "item": 8, "pr": 9, "branch": "feat/8-slug", "phase": "Reviewing",
  "title": "optional; fetched from the tracker when absent",
  "needs_call": null | {"claim": "…", "now": "…", "later": "…", "guards": "…", "pick": "…"},
  "changed": ["<strong>Lead.</strong> What now works that didn't.", "…"],
  "schema": null | {"file": "path", "fields": [{"name": "…", "type": "…", "required": "…", "means": "…"}],
                    "existing": "…", "optionality": "…", "writers": "…", "access": "…"},
  "looks": {"video": "/abs/path.mp4", "watch_for": "…",
            "shots": [{"file": "/abs/path.png", "caption": "…", "alt": "…"}],
            "note": "Backend only — <code>test.spec.ts</code> proves it: …"},
  "rounds": 2,
  "findings": [{"round": 1, "cat": "Bug|Edge case|Missing test|Cleanup|Speed|Not real",
                "what": "…", "repro": ["…"], "slipped": "…",
                "status": "fixed|deferred|not real", "fix": "…", "why": "…"}],
  "worth": "none — the rest are style calls",
  "after": null | "…"
}
"""
import datetime
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

# ---- CONFIG: fill at install time -------------------------------------------------
REPO = "jysim3/empowher"
ITEM_URL_BASE = "https://github.com/jysim3/empowher/issues/"
PR_URL_BASE = "https://github.com/jysim3/empowher/pull/"
BOARD_URL = "https://github.com/jysim3/empowher/issues"
BOARD_NAME = "jysim3/empowher issues"
REVIEWER = "Codex"
MERGE_STYLE = "squash merge"
REPORTS_DIR = "~/Documents/empowher/dist/merge-reports"
SERVED_URL_BASE = "https://pcsaur.tail7a7f12.ts.net/empowher/merge-reports/"
TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "skills" / "merge-report" / "references" / "report-template.html"
# Shell commands with {item} substituted. Each prints raw text to stdout.
DECISIONS_CMD = os.environ.get("MERGE_REPORT_DECISIONS_CMD", "gh api repos/jysim3/empowher/issues/{item}/comments --paginate --jq '.[].body'")
TITLE_CMD = os.environ.get("MERGE_REPORT_TITLE_CMD", "gh issue view {item} --repo jysim3/empowher --json title --jq .title")
INDEX_CMD = "python3 scripts/reports-index.py"
# -----------------------------------------------------------------------------------

CATEGORY_ORDER = ["Bug", "Edge case", "Missing test", "Cleanup", "Speed", "Not real"]
DECISION_RE = re.compile(
    r"^- \*\*(PM|Eng)\*\*\s+—\s+(?P<q>.+?)\s+→\s+(?P<c>.+?)\s+Why:\s+(?P<y>.+?)(?P<auto>\s+\(decided without you\))?\s*$"
)

e = html.escape


def sh(cmd):
    return subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True).stdout


def read_decisions(item):
    """Every line matching the grammar inside comments whose first line starts '## Decision log'."""
    out = []
    text = sh(DECISIONS_CMD.format(item=item))
    in_log = False
    for line in text.splitlines():
        if line.startswith("## Decision log"):
            in_log = True
            continue
        if line.startswith("## "):
            in_log = False
        if not in_log:
            continue
        m = DECISION_RE.match(line.strip())
        if m:
            out.append({"who": m.group(1), "q": m.group("q"), "c": m.group("c").rstrip("."),
                        "y": m.group("y").rstrip("."), "auto": bool(m.group("auto"))})
    auto = [d for d in out if d["auto"]]
    pm = [d for d in out if not d["auto"] and d["who"] == "PM"]
    eng = [d for d in out if not d["auto"] and d["who"] == "Eng"]
    return auto + pm + eng


def md_inline(s):
    """HTML snippet -> markdown for the terminal twin."""
    s = re.sub(r"</?code>", "`", s)
    s = re.sub(r"</?strong>", "**", s)
    s = re.sub(r'<a href="([^"]+)">(.*?)</a>', r"[\2](\1)", s)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def decision_rows_html(decisions):
    if not decisions:
        return '<p class="note">No decisions needed — the item was already exact.</p>'
    rows = []
    for d in decisions:
        who = f'<span class="badge {d["who"].lower()}">{d["who"]}</span>'
        if d["auto"]:
            rows.append(f'<tr class="auto"><td>{who}<span class="badge auto">decided without you</span></td>'
                        f'<td>{d["q"]}</td><td>{d["c"]}.</td><td>{d["y"]}.</td></tr>')
        else:
            rows.append(f'<tr><td>{who}</td><td>{d["q"]}</td><td>{d["c"]}.</td><td>{d["y"]}.</td></tr>')
    return ('<div class="tablewrap"><table><tr><th>Who</th><th>Question</th><th>What we chose</th><th>Why</th></tr>'
            + "\n".join(rows) + "</table></div>")


def decision_rows_md(decisions):
    if not decisions:
        return "No decisions needed — the item was already exact."
    lines = ["| Who | Question | What we chose | Why |", "| --- | --- | --- | --- |"]
    for d in decisions:
        who = f"**{d['who']}**" + (" ⚠ decided without you" if d["auto"] else "")
        lines.append(f"| {who} | {md_inline(d['q'])} | {md_inline(d['c'])} | {md_inline(d['y'])} |")
    return "\n".join(lines)


def finding_sort_key(f):
    return (f.get("round", 1), CATEGORY_ORDER.index(f["cat"]) if f["cat"] in CATEGORY_ORDER else 99)


def findings_html(findings, rounds):
    fixed = sum(1 for f in findings if f["status"] == "fixed")
    deferred = sum(1 for f in findings if f["status"] == "deferred")
    head = f'<h2>What the {e(REVIEWER)} review found ({rounds} round{"s" if rounds != 1 else ""}, {fixed} fixed, {deferred} deferred)</h2>'
    if not findings:
        return head + f'\n<p class="note">The review ran {rounds} round{"s" if rounds != 1 else ""} and found nothing in scope.</p>'
    rows = []
    for f in sorted(findings, key=finding_sort_key):
        cat = f["cat"]
        cat_html = ('<span class="badge bug">Bug</span>' if cat == "Bug"
                    else '<span class="badge dead">Not real</span>' if cat == "Not real" else e(cat))
        what = f["what"]
        if not what.startswith("Round "):
            what = f"Round {f.get('round', 1)} — {what}"
        repro = ""
        if f.get("repro"):
            repro = '<ol class="repro">' + "".join(f"<li>{s}</li>" for s in f["repro"]) + "</ol>"
        fix = {"fixed": f'<span class="badge fix">fixed</span> {f.get("fix", "")}',
               "deferred": '<span class="badge defer">deferred</span>',
               "not real": '<span class="badge dead">not real</span>'}[f["status"]]
        why = f.get("why") or "—" if f["status"] == "deferred" else "—"
        rows.append(f"<tr><td>{cat_html}</td><td>{what}{repro}</td><td>{f['slipped']}</td><td>{fix}</td><td>{why}</td></tr>")
    return (head + '\n<div class="tablewrap"><table><tr><th>Category</th><th>What we found</th>'
            '<th>Why it slipped past</th><th>Fix</th><th>Why deferred</th></tr>' + "\n".join(rows) + "</table></div>")


def findings_md(findings, rounds):
    fixed = sum(1 for f in findings if f["status"] == "fixed")
    deferred = sum(1 for f in findings if f["status"] == "deferred")
    head = f"## What the {REVIEWER} review found ({rounds} round{'s' if rounds != 1 else ''}, {fixed} fixed, {deferred} deferred)"
    if not findings:
        return head + f"\nThe review ran {rounds} round{'s' if rounds != 1 else ''} and found nothing in scope."
    lines = [head, "| Category | What we found | Why it slipped past | Fix | Why deferred |", "| --- | --- | --- | --- | --- |"]
    for f in sorted(findings, key=finding_sort_key):
        cat = "**Bug**" if f["cat"] == "Bug" else f["cat"]
        what = md_inline(f["what"])
        if not what.startswith("Round "):
            what = f"Round {f.get('round', 1)} — {what}"
        if f.get("repro"):
            what += " " + " ".join(f"{i}. {md_inline(s)}" for i, s in enumerate(f["repro"], 1))
        fix = {"fixed": "fixed — " + md_inline(f.get("fix", "")), "deferred": "deferred", "not real": "not real"}[f["status"]]
        why = md_inline(f.get("why") or "—") if f["status"] == "deferred" else "—"
        lines.append(f"| {cat} | {what} | {md_inline(f['slipped'])} | {fix} | {why} |")
    return "\n".join(lines)


def looks_html(looks, out_dir):
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    parts = []
    if looks.get("video"):
        src = pathlib.Path(looks["video"])
        shutil.copy2(src, assets / src.name)
        parts.append(f'<figure><video controls preload="metadata" src="assets/{e(src.name)}"></video>'
                     f'<figcaption>Watch for: {looks.get("watch_for", "")}</figcaption></figure>')
    if looks.get("shots"):
        figs = []
        for s in looks["shots"]:
            src = pathlib.Path(s["file"])
            shutil.copy2(src, assets / src.name)
            figs.append(f'<figure><img class="shot" src="assets/{e(src.name)}" alt="{e(s.get("alt", ""))}" />'
                        f'<figcaption>{s.get("caption", "")}</figcaption></figure>')
        parts.append('<div class="shots">' + "".join(figs) + "</div>")
    if looks.get("note"):
        parts.append(f'<p class="note">{looks["note"]}</p>')
    if not parts:
        sys.exit("looks: a UI PR needs a video or shots; a backend/tooling PR needs a note")
    return "\n".join(parts)


def looks_md(looks, url):
    bits = []
    if looks.get("video"):
        bits.append(f"Flow video in the report{(' at ' + url) if url else ''}. Watch for: {md_inline(looks.get('watch_for', ''))}")
    if looks.get("shots"):
        bits.append("Screenshots: " + "; ".join(md_inline(s.get("caption", "")) for s in looks["shots"]))
    if looks.get("note"):
        bits.append(md_inline(looks["note"]))
    return "\n".join(bits)


def schema_html(s):
    rows = "".join(f'<tr><td><code>{e(f["name"])}</code></td><td><code>{e(f["type"])}</code></td><td>{e(f["required"])}</td><td>{f["means"]}</td></tr>'
                   for f in s["fields"])
    return (f'<h2>Schema changes</h2><p class="note"><code>{e(s["file"])}</code></p>'
            '<div class="tablewrap"><table><tr><th>Field</th><th>Type</th><th>Required?</th><th>What it means</th></tr>'
            f"{rows}</table></div><ul>"
            f'<li><strong>Documents that already exist:</strong> {s["existing"]}</li>'
            f'<li><strong>Optional vs nullable vs required:</strong> {s["optionality"]}</li>'
            f'<li><strong>Who writes it:</strong> {s["writers"]}</li>'
            f'<li><strong>Access rules:</strong> {s["access"]}</li></ul>')


def schema_md(s):
    lines = ["## Schema changes", f"`{s['file']}`", "| Field | Type | Required? | What it means |", "| --- | --- | --- | --- |"]
    lines += [f"| `{f['name']}` | `{f['type']}` | {f['required']} | {md_inline(f['means'])} |" for f in s["fields"]]
    lines += [f"- **Documents that already exist:** {md_inline(s['existing'])}",
              f"- **Optional vs nullable vs required:** {md_inline(s['optionality'])}",
              f"- **Who writes it:** {md_inline(s['writers'])}",
              f"- **Access rules:** {md_inline(s['access'])}"]
    return "\n".join(lines)


def needs_call_html(n):
    return (f'<div class="callout"><h2>Needs your call — do not merge yet</h2><p>{n["claim"]}</p><ul>'
            f'<li><strong>Restructure now</strong> — {n["now"]}</li>'
            f'<li><strong>Restructure as a follow-up</strong> — {n["later"]}</li>'
            f'<li><strong>Accept the guards</strong> — {n["guards"]}</li></ul>'
            f'<p><strong>Our pick:</strong> {n["pick"]}</p></div>')


def needs_call_md(n):
    return ("## Needs your call — do not merge yet\n" + md_inline(n["claim"]) + "\n"
            f"- **Restructure now** — {md_inline(n['now'])}\n- **Restructure as a follow-up** — {md_inline(n['later'])}\n"
            f"- **Accept the guards** — {md_inline(n['guards'])}\n\n**Our pick:** {md_inline(n['pick'])}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    twin = "--no-twin" not in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    r = json.loads(pathlib.Path(args[0]).read_text())
    item, pr = int(r["item"]), int(r["pr"])
    title = r.get("title") or sh(TITLE_CMD.format(item=item)).strip()
    today = datetime.date.today().isoformat()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = pathlib.Path(REPORTS_DIR) / str(item) / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    decisions = read_decisions(item)
    tpl = TEMPLATE.read_text()
    style = tpl[tpl.index("<style>"): tpl.index("</style>") + len("</style>")]
    rounds = int(r.get("rounds", 0))
    findings = r.get("findings", [])
    sections = [f"<h1>{e(title)}</h1>",
                f'<div class="meta"><span>Item <a href="{ITEM_URL_BASE}{item}">#{item}</a></span>'
                f'<span>PR <a href="{PR_URL_BASE}{pr}">#{pr}</a></span><span>Branch <code>{e(r["branch"])}</code></span>'
                f'<span>{today}</span><span>Board: {e(r.get("phase", "Reviewing"))}</span></div>']
    if r.get("needs_call"):
        sections.append(needs_call_html(r["needs_call"]))
    sections.append("<h2>What changed</h2><ul>" + "".join(f"<li>{c}</li>" for c in r["changed"]) + "</ul>")
    sections.append("<h2>Decisions</h2>" + decision_rows_html(decisions))
    if r.get("schema"):
        sections.append(schema_html(r["schema"]))
    sections.append("<h2>What it looks like</h2>" + looks_html(r["looks"], out_dir))
    sections.append(findings_html(findings, rounds))
    sections.append(f'<p><strong>Worth tracking:</strong> {r.get("worth", "none — the rest are style calls")}. Reply with any you want filed.</p>')
    if r.get("after"):
        sections.append(f'<div class="warn"><strong>After merging:</strong> {r["after"]}</div>')
    sections.append(f'<footer>Merge report for <a href="{PR_URL_BASE}{pr}">PR #{pr}</a>, built {today} before {e(MERGE_STYLE)}. '
                    f'Board: <a href="{BOARD_URL}">{e(BOARD_NAME)}</a>.</footer>')
    page = ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\" />"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />"
            f"<title>{e(title)} — merge report</title>{style}</head><body><main>\n"
            + "\n\n".join(sections) + "\n</main></body></html>\n")
    (out_dir / "index.html").write_text(page)

    # verify: every src/href is assets/… or https://…, every asset non-empty
    for m in re.finditer(r'(?:src|href)="([^"]+)"', page):
        v = m.group(1)
        if not (v.startswith("assets/") or v.startswith("https://")):
            sys.exit(f"bad link in report: {v}")
    for f in (out_dir / "assets").glob("*"):
        if f.stat().st_size == 0:
            sys.exit(f"empty asset: {f}")
    if INDEX_CMD:
        subprocess.run(INDEX_CMD, shell=True, check=True)

    url = f"{SERVED_URL_BASE}{item}/{stamp}/" if SERVED_URL_BASE else f"file://{out_dir}/index.html"
    print(f"report: {out_dir / 'index.html'}")
    print(f"url: {url}")
    if not twin:
        return
    md = [f"\n# {title}",
          f"Item [#{item}]({ITEM_URL_BASE}{item}) · PR [#{pr}]({PR_URL_BASE}{pr}) · `{r['branch']}` · {today} · Board: {r.get('phase', 'Reviewing')}", ""]
    if r.get("needs_call"):
        md += [needs_call_md(r["needs_call"]), ""]
    md += ["## What changed"] + [f"- {md_inline(c)}" for c in r["changed"]] + ["", "## Decisions", decision_rows_md(decisions), ""]
    if r.get("schema"):
        md += [schema_md(r["schema"]), ""]
    md += ["## What it looks like", looks_md(r["looks"], url), "", findings_md(findings, rounds), "",
           f"**Worth tracking:** {md_inline(r.get('worth', 'none — the rest are style calls'))}. Reply with any you want filed."]
    if r.get("after"):
        md += ["", f"**After merging:** {md_inline(r['after'])}"]
    print("\n".join(md))


if __name__ == "__main__":
    main()
