---
name: merge-report
description: Build the pre-merge report for a PR — the one page the user reads instead of the diff before approving the merge. Use when a PR is open and its review rounds are done, when the user says "merge report", "summarise the PR", "ready to merge?", or asks to merge, and whenever the board workflow's close-out step runs. Also owns the Decision log convention on tracker items.
---

# Merge Report

The user approves merges from this report, not from the diff. It answers four questions
in a fixed order: what changed, what did we decide together, what does it look like, and
what did the independent review find. Build it as the final PR close-out step without
being asked, and hand it over as a page published to the local reports hub.

The report only summarises — it never invents. Every row traces to a tracker comment, a
review round, or a test artifact that already exists.

## The three input stages

1. **Before coding — the shaping interview.** Every product decision (what the user
   gets, edge behaviour, copy, scope cuts) and every engineering decision (where logic
   lives, data shape, trigger vs client) that is even slightly ambiguous is asked as its
   own question, recommended answer first. The agreed answers are posted to the item as
   a `## Decision log` comment (grammar below). This is the only stage that blocks on the
   user.
2. **During the work — decisions made without the user.** Anything that forces a new
   decision mid-implementation is decided with the most conservative, most reversible
   option and appended as a `## Decision log — update` comment, each line ending in
   `(decided without you)`. Asking mid-work is reserved for choices where a wrong guess
   would be expensive to undo. A reviewer claim that the whole approach is wrong, or an
   architecture note from a cause that recurred across review rounds, becomes the
   report's **Needs your call** block — never a mid-work question.
3. **During review — the independent rounds** from the `board-workflow` loop: what was
   fixed, what was deferred and why, what was not real.

A stage that produced nothing gets its section's empty-state line (below), never a
dropped section.

## Decision log grammar

Decisions live on the tracker item, where any later session can read them — never only
in the conversation. Post with `gh issue comment <n> --repo jysim3/empowher --body-file <file>`; the report collects every comment whose first
line starts with `## Decision log` via `gh issue view <n> --repo jysim3/empowher --comments`.

```markdown
## Decision log
- **PM** — Do guests count toward capacity? → Yes, same as players. Why: one seat is one seat, and `registeredCount` stays the single source.
- **Eng** — Where does the seat maths live? → `packages/shared/src/seating.ts`. Why: mobile, web, and Rules all need the same answer.
- **Eng** — Does something already do the waitlist ordering? → Reuse `sortByJoinedAt` in `packages/shared/src/queue.ts`. Why: searched the shared package and the stack docs; found it already used by the session list.
```

The third line is the research line every non-trivial item carries (AGENTS.md, "Research
before building"): the question is whether something already does the job, the choice is
what is reused or that it is written new, and `Why:` says where the search looked.

```markdown
## Decision log — update
- **Eng** — Old data has sessions with no `capacity`; block or allow? → Treat missing `capacity` as unlimited. Why: no write is blocked, and a later rule can tighten it. (decided without you)
```

Exact line shape, one decision per line, parsed by the report:

```
- **<WHO>** — <question>? → <what we chose>. Why: <one clause>[ (decided without you)]
```

- `WHO` is exactly `PM` or `Eng`. No other roles.
- The first line of the comment is exactly `## Decision log` or `## Decision log — update`.
- ` → ` separates question from choice; `Why:` introduces the reason; the suffix
  ` (decided without you)` is the only marker the report badges — nothing else counts.
- If the interview happened but the comment was never posted, post it now from
  conversation context before building the report. The report reads the item, not the
  transcript.

## Report structure

Exactly this order, in both the HTML page and the terminal summary. A section marked
*conditional* is cut entirely when its condition fails — never rendered empty.

| # | Section | Heading text | Condition |
| --- | --- | --- | --- |
| 1 | Header | `<item title>` | always |
| 2 | Needs your call | `Needs your call — do not merge yet` | conditional: a blocking decision exists |
| 3 | Summary of changes | `What changed` | always |
| 4 | Decisions | `Decisions` | always (empty-state line if none) |
| 5 | Schema changes | `Schema changes` | conditional: PR touches `src/content.config.ts` |
| 6 | Review artifact | `What it looks like` | always |
| 7 | Review findings | `What the Codex review found (R rounds, F fixed, D deferred)` | always |
| 8 | Worth tracking | `Worth tracking:` (bold lead, one paragraph) | always |
| 9 | After merging | `After merging:` (warn block) | conditional: merging is not the whole story |
| 10 | Footer | — | always |

### 1. Header

`<h1>` is the item title verbatim. One meta line, in this order: item link, PR link,
branch name in `code`, build date `YYYY-MM-DD`, board phase (`Board: Reviewing`). Keep
the `<h1>` and the PR link in the header block exactly — the archive index is regenerated by npm run reports:index.

### 2. Needs your call *(conditional)*

A red callout that leads the page. Included only when the agent **agrees** with a
reviewer claim that the approach is wrong, or an architecture note was raised from a
recurring cause. Contents, in order: the claim and why we agree (one paragraph), then a
list of exactly three options — **Restructure now**, **Restructure as a follow-up**,
**Accept the guards** — each with one clause on what it costs, then `Our pick: <option>,
<one-clause why>`. The PR is marked not merge-ready in the close-out. No "all good"
banner exists when there is nothing to decide.

### 3. What changed

3–6 bullets. Each bullet: bold lead phrase, then what now works that didn't, in the
words of the item. Not a file list, not a diffstat.

### 4. Decisions

One table, columns exactly: **Who | Question | What we chose | Why**. One row per
Decision log line.

Row order: lines marked `(decided without you)` first, then `PM`, then `Eng`; inside each
group, the order the log posted. The auto rows sort first because the user never saw
them — they are what the user is checking.

**Who column colour coding** (fixed, both themes defined in the template):

| Who | Badge text | Class | Colour |
| --- | --- | --- | --- |
| Product decision | `PM` | `badge pm` | blue |
| Engineering decision | `Eng` | `badge eng` | purple |
| Decided without the user | `decided without you`, after the PM/Eng badge | `badge auto` | amber, and the row gets `class="auto"` (amber left border) |

A decided-without-you cell holds two badges: the role badge, then the `auto` badge. The
role badge never changes colour because of the auto marker — the colours answer "whose
decision" and "did you see it" independently.

Empty state: `<p class="note">No decisions needed — the item was already exact.</p>`

### 5. Schema changes *(conditional)*

Required whenever the PR adds, changes, or removes a shared schema or a field on one;
cut when it touches none. Name the schema file exactly in a `note` line, then a table
with columns exactly: **Field | Type | Required? | What it means**, one row per field
touched, followed by one bullet each, bold lead, in this order:

- **Documents that already exist:** still valid as-is, or what backfill is needed, and
  whether a missing value is meaningful.
- **Optional vs nullable vs required:** why, and what must never write a default here.
  A field whose absence means something different from `null` is spelled out.
- **Who writes it:** which surfaces, and whether the value is trusted or a client's
  claim about itself.
- **Access rules:** what changed in the static content schemas; there are no runtime access rules, or why nothing had to.

This is the one section where precision beats plain language — a shipped field costs a
migration across every document ever written.

### 6. What it looks like

- Mobile or web UI change: the flow video (`flow-video` skill) as
  `<figure><video controls preload="metadata" src="assets/<name>.mp4"></video>
  <figcaption>Watch for: …</figcaption></figure>`. The caption starts with `Watch for:`
  and names, in order, what appears on screen.
- Screenshot-only surfaces: a `.shots` grid of `<figure><img class="shot">` with one
  caption each.
- Both are allowed together: video first, then the grid.
- Backend-only PR: `<p class="note">Backend only — <code><test file></code> proves it:
  <one line on what the test asserts>.</p>`
- A UI PR with no artifact is not ready; stop and produce one.

### 7. Review findings

One table across **all** rounds. Heading carries the counts: `R` = rounds run, `F` =
rows fixed, `D` = rows deferred; `Not real` rows count in neither. Columns exactly:
**Category | What we found | Why it slipped past | Fix | Why deferred**.

Row order: by round ascending; inside a round: `Bug`, `Edge case`, `Missing test`,
`Cleanup`, `Speed`, `Not real`.

| Column | Rule |
| --- | --- |
| Category | One of exactly six: `Bug`, `Edge case`, `Missing test`, `Cleanup`, `Speed`, `Not real`. `Bug` renders as `badge bug` (red); `Not real` as `badge dead` (grey); the other four as plain text. |
| What we found | Starts with `Round N — `. Plain words: what a person sees or what data goes wrong, then the code that caused it in `code`. Every `Bug` row gets an `<ol class="repro">` of 3–5 numbered replication steps directly under the text, each step one short sentence. |
| Why it slipped past | One honest clause: "only tested with 1 guest", "copied from the old screen". For `Not real`: why the reviewer was wrong — "misread the guard", "reads the dirty worktree". |
| Fix | Fixed: `badge fix` reading `fixed`, then what was done and the commit it was folded into. Deferred: `badge defer` reading `deferred`, nothing else. Not real: `badge dead` reading `not real`, nothing else. |
| Why deferred | Deferred rows: the real reason — pre-existing on trunk, a different PR's job, a state nothing can reach, round cap reached. Fixed and not-real rows: `—`. |

Empty state (table omitted, heading kept with `0 fixed, 0 deferred`):
`<p class="note">The review ran N rounds and found nothing in scope.</p>`

### 8. Worth tracking

One paragraph: `<strong>Worth tracking:</strong>` then which deferred rows deserve a
tracker item and why, or `none — the rest are style calls`. Ends with `Reply with any
you want filed.` It is a recommendation the user answers in their own time; the agent
files only what they name. Never file on your own.

### 9. After merging *(conditional)*

An amber `.warn` block, lead `<strong>After merging:</strong>`, present only when the
merge does not finish the job: a manual deploy, a store release, a migration or backfill,
a config change on a live system. One or two sentences naming the exact step and its
order relative to other pending steps. GitHub Pages deploys continuously after merge once deployment is configured

### 10. Footer

`Merge report for <a>PR #M</a>, built YYYY-MM-DD before squash merge. Board: <a>https://github.com/jysim3/empowher/issues</a>.`

## Language rules

The whole report — page and terminal — is written so a 12-year-old could read every
sentence:

- Plain, short words. Short sentences. No "leverage", "utilise", "refactor the abstraction".
- **Keep every technical detail.** Exact function, variable, file, and field names stay,
  in `code` style. Simplify the vocabulary around them, never the content.
- Explain a finding as what a person sees or what data goes wrong, then name the code
  that caused it.

## Building the HTML page

The page is **generated, never hand-written**: write one JSON file (shape documented at
the top of `scripts/merge-report.py`) with the item, PR, branch, the What-changed
bullets, the artifact paths, the findings and the after-merge note, then run
`python3 scripts/merge-report.py <report.json>`. The script
reads the Decision log rows from the tracker (so it cannot invent one), copies media
into `assets/`, writes the page from `references/report-template.html`, refreshes the
archive index, checks every link and asset, and prints the served URL plus the terminal
twin ready to paste. Hand-editing the output, or composing the page from the template
by hand, is the mistake the script exists to stop: three sessions re-derived the same
generator before it shipped.

The rules the script enforces, so you can tell when it is wrong:

- **Self-contained**: all CSS in the one `<style>` block, no JavaScript, no CDN links, no
  web fonts. The page must open from `file://` with no network.
- **Media is copied in, then linked relatively.** `mkdir -p <report-dir>/assets` first,
  then `cp` the video and screenshots into it and reference them as `assets/<name>`.
  Never link the original artifact path (those directories get cleaned), and never
  inline media as a `data:` URI (a real `.mp4` streams and seeks; a base64 blob does not).
- Tracker and PR links are absolute `https://` URLs; the page must not break when they
  do not open.
- **Escape every piece of collected text** before inserting it: `&` → `&amp;`, `<` →
  `&lt;`, `>` → `&gt;`, plus `"` → `&quot;` inside attributes; URL-encode paths used in
  `src` / `href`. Item titles, decision lines, and findings routinely contain all of them.
- **Output location**: `~/.local/share/empowher/merge-reports/<item number>/<YYYYMMDD-HHMMSS>/index.html`
  — outside every checkout, so a deleted worktree never takes the only copy of a video
  with it. The item number alone finds the folder; the timestamp (`date +%Y%m%d-%H%M%S`
  at build start) sorts rounds oldest-first and stops a rebuild overwriting the round it
  replaces.
- **Verify before handing over**: `ls -la` the report directory — the HTML and every
  file under `assets/` exist and are non-empty (a 0-byte mp4 plays nothing). Check every
  `src=` and `href=` is `assets/…` or `https://…`. then run PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run reports:index and publish with ~/Documents/reports/publish-page.sh empowher merge-reports ~/.local/share/empowher/merge-reports <shots-dir>

## The terminal twin

The final message repeats the same content in the same order, as markdown, so it stands
alone when the user reads it on a phone. Exact skeleton:

```markdown
# <item title>
Item <link> · PR <link> · `branch` · YYYY-MM-DD · Board: Reviewing

## Needs your call — do not merge yet        ← only when section 2 exists
…

## What changed
- **Lead phrase.** What now works that didn't.

## Decisions
| Who | Question | What we chose | Why |
| --- | --- | --- | --- |
| **Eng** ⚠ decided without you | … | … | … |
| **PM** | … | … | … |
| **Eng** | … | … | … |

## Schema changes                             ← only when section 5 exists
`path/to/schema.ts`
| Field | Type | Required? | What it means |
…
- **Documents that already exist:** …

## What it looks like
<report link to the video, or the screenshot list, or the backend-only line>

## What the <reviewer> review found (R rounds, F fixed, D deferred)
| Category | What we found | Why it slipped past | Fix | Why deferred |
| --- | --- | --- | --- | --- |
| **Bug** | Round 1 — … 1. … 2. … 3. … | … | fixed — …, folded into `<commit>` | — |
| Edge case | Round 2 — … | … | deferred | … |
| Not real | Round 2 — … | … | not real | — |

**Worth tracking:** … Reply with any you want filed.

**After merging:** …                          ← only when section 9 exists
```

Who column in the terminal: `**PM**` / `**Eng**`, with ` ⚠ decided without you` appended
on auto rows. Category column: `**Bug**` bold, the rest plain. Replication steps stay
inline in the cell as `1. … 2. … 3. …`.

## Delivering it

1. **Hand over the report location first**: the URL printed by ~/Documents/reports/publish-page.sh. Never zip it, never send it
   as an attachment when a link exists.
2. Then the terminal twin, in full.
3. Then hand back to the board workflow's close-out: PR URL, item title and phase, which
   round the loop stopped on and why, and the one-line ask — "read the report, then
   approve the merge". If a **Needs your call** block exists, the ask is the decision,
   not the merge.

## Related

- `board-workflow` — the loop this report ends; its review rounds feed section 7.
- `flow-video` — produces the video section 6 embeds.
