#!/usr/bin/env python3
"""Write the report archive front page: <ARCHIVE>/index.html, newest round first.

Layout: <item>/<YYYYMMDD-HHMMSS>/index.html per merge-report round, media under its
assets/. Reads each report's first <h1> and first PR link. Fill CONFIG at install time.
"""
import html
import os
import re
from datetime import datetime

# ---- CONFIG: fill at install time -------------------------------------------------
ARCHIVE = os.path.expanduser("~/.local/share/empowher/merge-reports")
TITLE = "EmpowHER merge reports"
URL_PREFIX = "/empowher/merge-reports/"
ITEM_URL_BASE = "https://github.com/jysim3/empowher/issues/"
PR_URL_RE = r'href="(https://github\.com/jysim3/empowher/pull/(\d+))"'
HUB_LINK = "/"
# -----------------------------------------------------------------------------------

H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
PR = re.compile(PR_URL_RE)


def rounds():
    out = []
    if not os.path.isdir(ARCHIVE):
        return out
    for item in os.listdir(ARCHIVE):
        item_dir = os.path.join(ARCHIVE, item)
        if not item.isdigit() or not os.path.isdir(item_dir):
            continue
        for stamp in os.listdir(item_dir):
            page = os.path.join(item_dir, stamp, "index.html")
            if not os.path.isfile(page):
                continue
            text = open(page, encoding="utf-8", errors="replace").read()
            h1 = H1.search(text)
            title = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else f"Item #{item}"
            pr = PR.search(text)
            try:
                when = datetime.strptime(stamp, "%Y%m%d-%H%M%S")
            except ValueError:
                when = datetime.fromtimestamp(os.path.getmtime(page))
            out.append({"item": int(item), "stamp": stamp, "title": title,
                        "pr_url": pr.group(1) if pr else None, "pr": pr.group(2) if pr else None, "when": when})
    out.sort(key=lambda r: r["when"], reverse=True)
    return out


def render(entries):
    e = html.escape
    rows = "\n".join(
        f'<tr><td class="when">{r["when"]:%d %b %Y}<br><small>{r["when"]:%H:%M}</small></td>'
        f'<td><a href="{URL_PREFIX}{r["item"]}/{e(r["stamp"])}/">{e(r["title"])}</a>'
        f'<div class="sub">item <a href="{ITEM_URL_BASE}{r["item"]}">#{r["item"]}</a>'
        + (f' · PR <a href="{e(r["pr_url"])}">#{r["pr"]}</a>' if r["pr"] else "") + "</div></td></tr>"
        for r in entries) or '<tr><td colspan="2" class="sub">No reports yet.</td></tr>'
    hub = f' · <a href="{HUB_LINK}">all archives</a>' if HUB_LINK else ""
    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__TITLE__</title>
<style>
:root { --bg:#fff; --ink:#1a1d21; --muted:#5c6470; --line:#e3e6ea; --accent:#2563eb; }
@media (prefers-color-scheme: dark) { :root { --bg:#101418; --ink:#e6e9ec; --muted:#9aa4af; --line:#2a323b; --accent:#7aa2ff; } }
* { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
main { max-width:720px; margin:0 auto; padding:24px 16px 48px; } h1 { font-size:22px; margin:0 0 4px; }
.lede { color:var(--muted); margin:0 0 20px; font-size:14px; } table { width:100%; border-collapse:collapse; }
td { padding:12px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
td.when { white-space:nowrap; color:var(--muted); font-size:14px; width:1%; } .sub { color:var(--muted); font-size:13px; }
a { color:var(--accent); text-decoration:none; } a:hover { text-decoration:underline; }
</style></head><body><main>
<h1>__TITLE__</h1>
<p class="lede">One page per PR round: what changed, decisions, the flow video, review findings. Newest first.</p>
<table>__ROWS__</table>
<p class="lede">Built __BUILT____HUB__</p>
</main></body></html>
"""
    return (page.replace("__TITLE__", e(TITLE)).replace("__ROWS__", rows)
            .replace("__BUILT__", f"{datetime.now():%Y-%m-%d %H:%M}").replace("__HUB__", hub))


if __name__ == "__main__":
    os.makedirs(ARCHIVE, exist_ok=True)
    entries = rounds()
    with open(os.path.join(ARCHIVE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render(entries))
    print(f"wrote {ARCHIVE}/index.html ({len(entries)} rounds)")
