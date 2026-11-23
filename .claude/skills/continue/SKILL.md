---
name: continue
description: Continue work on a tracker item a previous session worked on. Use when the user types /continue with an item reference. Reads the item's handover and session comments as the briefing, stamps this session on the item, and resumes from the recorded state instead of re-investigating.
---

# Continue

1. **Read the item and all its comments** (`gh issue view <n> --repo jysim3/empowher
   --comments`). The latest handover comment is the briefing: treat its "Done" section
   as verified fact, its "Do NOT re-investigate" section as binding — do not re-burn
   time on disproven leads.
2. **Try the recorded resume command first** — a previous transcript may still be
   resumable with full context, which beats starting cold.
3. **If starting cold**: run `python3 scripts/board.py start "<item>"` to stamp this
   session, and verify the recorded worktree is still on the recorded branch
   (`git -C <worktree> branch --show-current`) before reusing it — another session may
   have switched it. If the worktree is gone or diverged, cut a fresh one from the
   branch.
4. **Resume from "Next step"** in the handover, not from scratch.
