---
name: board-workflow
description: Manage tracker items at https://github.com/jysim3/empowher/issues and the branch → commit → review → PR flow for empowher. Use when adding, finding, triaging, or updating tracker items, and whenever work is ready to commit — every commit needs a linked item and launches the review loop that ends in the PR. Also triggered by "commit this", "create the PR", "open the PR", and "PR this".
---

# Board Workflow

Board constants: owner `jysim3`, repo `empowher`, board `https://github.com/jysim3/empowher/issues`, trunk
`main`, helper `python3 scripts/board.py`.

Work never lands directly on `main`. Every change goes onto a branch, gets a PR,
and merges from there with squash merge.

## Helper script

Prefer the helper for lookup, creation, status changes, and footers:

```bash
python3 scripts/board.py find "<keywords>"
python3 scripts/board.py create --title "..." --body "..." --start
python3 scripts/board.py start "<item>"
python3 scripts/board.py status "<item>" Reviewing
python3 scripts/board.py commit-link "<item>"
```

Commands that take an item accept an exact title, a title substring, or an item number.

## Writing the item

An item describes **what changes for the person using the product, and why it matters**
— plain language, no engineering detail; the technical how goes in the PR body. Plain
language is about vocabulary, not simplicity: write all six rules if there are six, as
things a person experiences rather than a state machine. Exception: pure engineering work
(refactors, test infra, CI, build), where the developer is the user — but the
step-by-step plan still stays out.

## Item workflow

1. `find` before creating anything; reuse the closest existing item when it clearly
   represents the work. Follow-up fixes to a recent feature reuse the feature's item —
   create a separate Bug item only when the user asks for separate tracking.
2. Phases: `Todo` → `Investigating` (shaping) → `Coding` → `Reviewing` (PR open) →
   `Done` (merged). Never downgrade a phase.
3. Parent/child work uses the tracker's **native sub-item relationship**, created via the
   helper's `--parent`; a markdown checklist alone is not enough.

## Branch and commit guard

Before every `git commit`:

1. **Be on a branch, not `main`** — re-check right before every commit; branch off
   up-to-date trunk named `fix/<n>-short-slug` or `feat/<n>-short-slug`.
2. Identify the item; in a multi-commit PR, commits default to the PR's overarching item.
3. Generate the footer with `python3 scripts/board.py commit-link "<item>"` and include
   every generated line (`Board:` / `Item:` / `Closes:`). Never commit without it; if the
   user supplied a message lacking it, append it. If several items could match, link the
   closest and flag the choice in the merge report — do not block the commit on a
   question.

## PR hygiene

- **One PR, one overarching scope — commits carry the concerns.** Each commit builds,
  passes tests, and carries the footer.
- **Never ship a commit and a fix for that commit in one PR.** Amend the tip
  (`git commit --amend --no-edit`) or fixup earlier commits
  (`git commit --fixup <sha>` then
  `git -c sequence.editor=: rebase --autosquash origin/main`), then
  `git push --force-with-lease`. A `fix:` commit is only legitimate for defects already
  on trunk. **If the harness denies the amend or the force push** (a permission rule
  classed it destructive), do not work around it: make a plain second commit with the
  footer, say in the merge report that the PR carries a review-fix commit the rule
  blocked from squashing, and offer the squash as the user's call. Never ask for the
  permission mid-loop.
- **Rebase, never merge trunk in.** Force-pushing your own PR branch is expected; never
  force-push trunk or a branch another session builds on without coordinating.
- Stacked PRs: branch off the parent branch, open with `--base <parent>`, say "Stacked
  on #<n>, merge that first" in the body; after the parent lands, restack with
  `git rebase --onto origin/main <parent-branch> <child-branch>` before deleting
  the parent branch, then retarget the PR.

## Commit, review, then PR — one sequence

1. **Commit** under the guard, then `git fetch origin main && git rebase
   origin/main` so the review base is current.
2. **Launch the independent review in the background immediately**, diffing the branch
   against `origin/main` (or the parent branch if stacked):
   `codex review --base origin/main`.
3. **While it runs, explain what was implemented** in the user's terms — not a file
   list, not a "waiting" placeholder.
4. **Triage and amend**: confirm each finding by reading the cited line; fix what
   belongs to this PR's scope, defer the rest. A root cause recurring across two rounds
   stops the loop for an architecture decision instead of another patch.
5. **Report each round on its own** as soon as it is triaged — findings in plain
   language, what was fixed, what was deferred and why. Never batch rounds.
6. **Stop** when a round produces nothing in scope, or after round 3. Expect most
   findings to defer — the reviewer has no stake in the PR's scope and inflates
   severity; fixing everything it raises is how a tight PR turns into a sprawl.
7. **Push and open the PR.** The body **starts with a link block**: `Closes #<n>` per
   completed item plus `Related to` / `Depends on` / `Follows up` / `Reverses` lines;
   sweep the drafted body for bare `#<n>` references and promote them. Attach the
   review artifact for UI work. Move the item to `Reviewing`.
8. **Build the merge report** (`merge-report` skill) and close with where it stands,
   recommending which deferred findings are worth tracking; file only the ones the user
   names in reply.

Move the item to `Done` once the PR merges. Report the item title and status in the
final response.
