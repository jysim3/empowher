---
name: handover
description: Post a session-handover comment on the current work item so another session can continue with /continue. Use when the user types /handover, when pausing work another session will pick up, and ALWAYS before ending a remote/bridge session whose item is unfinished.
---

# Handover

Post the state onto the item itself, where any future session can read it:

```bash
python3 scripts/board.py handover "<item>" \
  --done "verified facts only: what passed, what is committed" \
  --broken "exact failing command + error" \
  --avoid "dead ends already disproven, and why" \
  --next "the single concrete next action" \
  [--pr <n>]
```

Rules:

- **Verified facts only in `--done`** — nothing aspirational; a handover that overstates
  progress costs the next session more than no handover.
- **`--avoid` matters most**: handovers without it re-burn hours on disproven leads.
- **`--next` is one concrete action**, not a plan.
- Branch and worktree are auto-detected by the helper; verify they are recorded.
- When to hand over: always for a remote/bridge session ending with an unfinished item
  (the user cannot resume it directly); for terminal sessions, only when pausing work
  another session is expected to continue — most items are carried end-to-end by one
  session, and per-session comments are noise.
