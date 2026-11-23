# EmpowHER site

This file holds rules coding agents must see without digging. Keep procedures in skills and domain facts in `docs/`.

## Where facts live

- Product, architecture, decisions and binding design: `docs/PRODUCT_SPEC.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/DESIGN.md`.
- Who the app is for: `docs/personas/`. Only a persona rewrite chat edits persona pages; working sessions do not.
- Session state and handover: GitHub Issues and comments, never docs.
- A PR that changes a documented procedure or invalidates a fact in a skill updates that skill in the same PR.

## Skill growth rules

- Write a procedure skill the second time a session re-derives the same “how to do X here”.
- Write a charter skill the second time a session re-derives the same domain knowledge.
- Never write either speculatively. Turn logic drift between copies into shared code or mechanical checks.

## Engineering guidelines

- Interview before planning a feature unless the user supplied the decisions or asked to proceed directly.
- Read the actual flow before coding; state consequential assumptions and choose the smallest complete implementation.
- Research in this order: this repo (`src/components/`, `src/layouts/`, `src/data/`, `src/content.config.ts`, `docs/`), Astro’s current docs at `https://docs.astro.build/`, `modern-web-guidance` for handwritten web code, installed dependencies, then a maintained library.
- Record meaningful reuse research as an `Eng` line in the issue Decision log using the `merge-report` grammar.
- Re-read the diff and remove unsupported abstractions, knobs and duplicate logic without cutting validation, real error handling, security or repo invariants.
- Touch only the requested scope. Workers use documented conservative defaults and flag decisions instead of asking mid-task.

## Finish every workflow with tests

Run the coverage required below, then `PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run validate`. No unit-test runner exists yet.

| Surface | Change type | Required coverage | Command |
| --- | --- | --- | --- |
| Public Astro website | Content, component, CSS or user flow | `astro check`, production build, and headless-Chromium screenshots inspected at relevant phone and desktop sizes | `PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run validate` |
| Workflow tooling | Python or hook behavior | The tool’s offline/self-test plus site validation | `python3 <tool> --help` and the tool-specific check |

## Delegate implementation to workers

The parent explores, resolves ambiguity, dispatches, reviews and verifies. Codex CLI workers implement most bounded changes; the parent keeps interactive design, tracker/git/network work and final verification.

- Compose cold-start prompts with `worker-prompts`.
- The parent/design conversations use Claude Fable 5.2. Fact-finding uses Claude Sonnet 5.5; implementation, review, evaluation and persona rounds use Codex GPT-5.4 via Codex CLI. (decided without you)
- Never accept a worker’s reported pass without rerunning checks and reviewing its diff.

## Commits close GitHub Issues

Use `python3 scripts/board.py` for `jysim3/empowher`. Every commit on a non-`main` branch includes the exact `Board:`, `Item:` and `Closes:` footer printed by `python3 scripts/board.py commit-link <item>`.

Work never lands directly on `main`. Branch from it as `feat/<n>-short-slug` or `fix/<n>-short-slug`, rebase on `origin/main`, open a PR and squash-merge. The parent Claude Code session alone commits, pushes, runs networked commands and changes git configuration.

Independent code review asks whether the diff is correct. A persona round asks whether the affected person would want the change. Neither replaces inspecting the screenshot report.

## Changes get a persona round

The framework is installed but there are no persona pages yet. Persona rounds begin once the first persona line and page exist in `docs/personas/README.md`; the first will be “the committee,” whose words are relayed by the developer. Run the `persona-round` skill before and after a visible change once that page exists.

- Use only habits and words the developer relays or information already public on the site. Never include names, addresses, tokens, secrets or other private data.
- Working sessions never edit `docs/personas/` or log remarks. `tools/persona/` does; a rewrite chat may land a commit touching only `docs/personas/` without review, and `.githooks/commit-msg` exempts such commits.
- Needs on the machine: trusted project hooks in Claude Code, signed-in `claude`, `python3`, and optionally `jig-start`.

## User flows and UI changes require review artifacts

Publish pages and screenshot reports with `~/Documents/reports/publish-page.sh empowher <slug> <source-folder> <shots-dir>`. Use headless Chromium, inspect every screenshot before reporting, and never use the Artifact tool.

## Web platform code

- Before changing HTML, CSS or client-side DOM, use `modern-web-guidance` to search and retrieve the current guide.
- Browser support: Baseline Widely available; newer features only behind feature detection with a small fallback and no new dependency.
- Prefer native platform capabilities. Do not enable Origin Trials, single-engine features or `.mwgrc` experiments without the owner’s approval.
- Put the guidance usage note in the PR body under `### Modern Web Guidance`.

## Hard guardrails

- Never create project files in the home directory or `/tmp`; use the session scratchpad for temporary work and this repo for durable work.
- Never track names, addresses, tokens or secrets. Public information already on the public EmpowHER site may be used.
- Commits and pushes are parent-session only. Every project state change also requires a subagent to update the project index at `~/Documents/projects`.
- Do not modify `docs/DESIGN.md`, `reference/` or `src/` unless the active task explicitly authorises it.

## Project overview

This is one public, user-facing Astro 7 static site using strict TypeScript, loader content collections and plain Astro components/CSS. Wix handles transactions. GitHub Pages continuous deployment on merge to `main` is planned but not configured.

## Commands

Astro requires Node 22.23.4 or newer. Prefix every Node/npm/npx command exactly as shown:

```sh
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run dev
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run check
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run build
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run preview
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run validate
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run reports:index
```

## Skill routing

- `start`, `continue`, `handover`: begin, resume or hand over issue-backed work.
- `board-workflow`: any tracker action and every commit/review/PR flow.
- `worker-prompts`: prompts for delegated workers.
- `merge-report`: build the generated pre-merge report when a PR is ready.
- `design`: `/design`, a restyle, style choices or a screen absent from `docs/DESIGN.md`.
- `modern-web-guidance`: before handwritten HTML/CSS/DOM changes (install remains a parent-session step).
- `persona-round`: visible proposals and screenshots once the first persona exists; also `[persona rewrite]` sessions.
