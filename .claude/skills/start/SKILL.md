---
name: start
description: Begin work on a tracker item or brand-new task. Use when the user types /start followed by an item number, an item title, or a short description of new work. Finds or creates the item, stamps this session on it, cuts the branch, then begins the work.
---

# Start

1. **Find or create the item**: `python3 scripts/board.py find "<keywords>"`; reuse the
   closest match, else `create` with a plain-language product body (see
   `board-workflow` for the voice) and `--start`.
2. **Stamp the session**: `python3 scripts/board.py start "<item>"` — records this session
   id and working directory on the item, moves `Todo` → `Investigating`, assigns the
   user, and posts the resume comment. Never downgrades a later phase.
3. **Shape before coding**: interview the user on every PM and engineering question that
   is even slightly ambiguous — one question at a time, recommended answer first — until
   shared understanding. Questions the codebase can answer, answer by exploring instead.
   Post the agreed answers as a `## Decision log` comment on the item.
   **This interview is where questions belong; after it, try hard not to ask** — make
   forced decisions conservatively and log them `(decided without you)` per the
   `merge-report` skill.
4. **Research before building**: per AGENTS.md's guideline, search this codebase, the
   stack's current docs or guidance skill, installed dependencies and existing
   libraries for something that already does the job. Add one `Eng` line to the
   Decision log comment from step 3 (`Does something already do <the job>? → <reuse X |
   write it>. Why: searched <where>; found <what>.`). Skip for trivial work.
5. **Cut the branch** off up-to-date `main`: `feat/<n>-short-slug` or
   `fix/<n>-short-slug`.
6. **Begin** — set the item to `Coding` the moment implementation starts (e.g. when
   dispatching a worker).
