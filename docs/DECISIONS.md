# Decisions

Format: date, decision, why. Newest first. Read before reversing one.

- **2026-11-24 Hosting on hold.** No preview hosting is set up yet; previews are local and on the owner's tailnet. GitHub Pages stays the intended host, but a private repo needs a paid plan and the site would be public either way, so it waits until there are more pages to show the committee.
- **2026-11-24 Sourdough workflow and tracked hooks.** GitHub Issues is the only tracker; workflow phases use labels, session state lives in issue comments, and tracked hooks run validation plus commit-footer checks after the parent activates `.githooks`. UI review uses headless-Chromium screenshots published to the private `empowher` reports archive.
- **2026-11-24 Main with squash merge (decided without you).** Work branches from `main`, lands through pull requests and squash-merges; continuous GitHub Pages deployment is intended after it is configured.
- **2026-11-24 Model tiers (decided without you).** Claude Fable 5.2 directs design, Claude Sonnet 5.5 handles fact-finding subagents, and Codex GPT-5.4 via Codex CLI handles implementation, review, evaluation and persona rounds.
- **2026-11-24 Web platform support.** Target Baseline Widely available; a newer feature needs feature detection, a small fallback and no new dependency. Current guidance comes from `modern-web-guidance` once the parent installs it with network access.
- **2026-11-24 Content editing.** The committee will edit content through an editing screen in a later phase; from now on all content is one file per item in content collections.
- **2026-11-24 GitHub Pages during the build.** Publish build previews with GitHub Pages while the live domain stays on Wix until the committee approves a switch. Pages from a private repository requires a paid GitHub plan, and the Pages site is public even when its repository is private.
- **2026-11-24 Persona kit installed but empty.** Install the persona framework and workflow, but leave persona pages empty for now. The committee persona will be filled later (“we will circle back”), feedback will be relayed by the developer, and no persona rounds run until a persona exists.
- **2026-11-24 Private GitHub repository with Issues only.** The future repository will be private at `jysim3/empowher`; use GitHub Issues without a second project-management system.
- **2026-11-24 E + A · Front Cover design direction.** Combine A · Front Page's calm paper system with E · Cover Story's cover, contents list, portrait row, magazine shelf and narrow labels. Rejected: B · Morning Tea, C · Rise Lead Shine, D · Plum Room, F · Anniversary Issue, G · Issue 03, H · The Monthly, I · Two-Ink Zine and J · Her Words; A and E are ingredients of the chosen hybrid. Binding detail is in `docs/DESIGN.md`.
- **2026-11-24 Astro static stack with self-hosted fonts.** Astro 7 static output, strict TypeScript, Astro image processing and locally packaged Fraunces, Source Sans 3 and Oswald provide a small public site without a runtime backend or third-party font request.
- **2026-11-24 Scope is pages first.** Rebuild public information while Wix keeps event registration, membership payments, shop, forms and accounts.
- **2026-11-24 Single tenant.** Build one site for one organisation, EmpowHER Sydney Inc; multi-tenant abstractions add no current value.
- **2026-11-24 Dark mode refused.** The approved visual language is a consistent print-on-paper surface, so the site does not offer a dark colour scheme.
