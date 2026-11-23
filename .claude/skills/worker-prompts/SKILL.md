---
name: worker-prompts
description: Compose tightly scoped prompts for delegated worker agents and handover prompts for agents continuing work in another worktree or session. Use whenever launching a worker, when the user asks for "a prompt for the other agent" or a task brief, or when delegating an implementation slice per AGENTS.md's delegation rule.
---

# Worker & Handover Prompts

Workers start cold: no conversation history, no memory, no ability to ask questions.
Every stall or wrong turn in past worker runs traced to a prompt that omitted context the
parent already had. Fill the template completely — each section has been the missing
piece at least once.

## Before writing the prompt (parent's job)

- Resolve all ambiguity yourself: explore the code, pick the approach, decide edge
  cases. A worker prompt with an open question is not ready to send.
- Do the research yourself (AGENTS.md, "Research before building") and put the result
  in the prompt: the existing function, doc page, guide id or library the worker must
  use. A worker that is not told what already exists writes it again.
- Pull the exact verification commands from AGENTS.md's Coverage By Surface table for
  the touched surface(s).
- If the worker runs in a worktree, decide the bootstrap command and environment flags
  now.
- Pin the model: workers run on the repo's work model (named once in AGENTS.md,
  "Delegate Implementation To Workers"), never the parent's design model. A fact-finding brief for a design conversation is a
  worker too — same model, read-only scope.

## Template

```markdown
## Task

<one paragraph: what to build/fix and why, in behavioral terms>

## Scope — files to touch

<explicit list; state "do not touch anything else">

## Environment setup (do this first)

- You are in worktree <path>. Bootstrap with `PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm install` and
  nothing else — never symlink node_modules from another checkout.
- Astro requires the pinned Node PATH; do not use network, git commits, pushes or git configuration in workers.

## Constraints

- <repo guardrails that apply, copied from AGENTS.md Hard Guardrails>
- <task-specific constraints and decided edge cases>
- If you hit an undecidable choice, apply the most conservative default and flag it in
  your report — you cannot ask questions mid-task.

## Verification (run all, report each with pass/fail)

- <focused test/e2e command for the touched surface>
- <workspace validate command>
- <fixture rules, e.g. derive test ids from the per-run id; never rely on backend reset>

## Report format

- Every command you ran, with pass/fail and the failing output if any.
- Every file you changed, one line each on what changed.
- Any conservative default you applied in place of a question.
```

## Handover prompts (agent mid-task in another worktree/session)

Same template, plus a **Status** section at the top:

```markdown
## Status

- Done so far: <verified facts only — what passed, what is committed>
- Currently broken/unknown: <exact failing command + error>
- Do NOT re-investigate: <dead ends already disproven, with why>
- Next step: <the single concrete next action>
```

The "Do NOT re-investigate" line matters most: handovers without it re-burn hours on
already-disproven leads.

## Parent responsibilities after the worker returns

Do not treat the worker's self-reported pass as verification. Re-run the validate and the
focused suite yourself, review the diff against the Scope section, produce the review
artifact, and own the tracker item and commit. Monitor async workers for stalls instead
of assuming completion.
