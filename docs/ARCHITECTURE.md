# Architecture

## Stack

Astro 7.4 static output, strict TypeScript and plain Astro components/CSS. Images are imported from `src/assets/` and processed by Astro; Fraunces, Source Sans 3 and Oswald are self-hosted from installed Fontsource packages. There is no client framework, backend, runtime state or external font request. Wix remains the transaction service during Phase 1.

## Surfaces by route

```text
/                    Home page, built now
/events              Event list, built
/events/[slug]       Event detail with Wix registration link, built
/women               EmpowHER Women directory, built
/women/[slug]        Woman profile, built
/membership          Membership with Wix checkout links, built
/magazine            Magazine shelf with Issuu reading links, built
/resources           Filterable document and external-resource library, built
/blog                 Blog list, built
/blog/[slug]          Blog post, built
/blog/category/[slug] Blog category list, built
/about and others     Organisation and resource pages, built
/programs             Programme and campaign index, built
/programs/[slug]      Programme detail and related photo set, built
/gallery              Programme and event photo sets, built
/404                   Static not-found help page, built
```

All Phase 1 informational routes are implemented. Wix continues to host transactions, forms, accounts and the shop.

## Content layout

This is a single-tenant site. Astro's loader-based content collections are defined and strictly validated in `src/content.config.ts`. Every editable item has its own file under `src/content/`; referenced images live in `src/assets/` and pass through the collection `image()` helper and Astro image pipeline.

| Collection | File type | Fields | Who edits |
|---|---|---|---|
| `events` | Markdown | Title, optional start/end or date-TBD state, venue, locality, address, summary, registration URL, optional local/source image metadata and status; body description | Committee through the later editing screen |
| `members` | Markdown | Name, role/business, optional portrait/banner, image sources and alt text, optional contact fields and links, home feature flag/order; body profile | Committee through the later editing screen |
| `plans` | JSON | Name, numeric yearly price, short home summary, full description, short home benefits, full membership-page benefits, checkout URL, order | Committee through the later editing screen |
| `issues` | JSON | Title, issue number, optional confirmed month, cover, Issuu URL | Committee through the later editing screen |
| `resources` | Markdown | Title, type, topics, optional date, summary, exactly one hosted file or external URL, action metadata, optional publisher/cover/file metadata/order | Committee through direct repository editing |
| `pages` | Markdown | Title, lede, source URL and optional image; body long-form copy | Imported from the captured public site |
| `committee`, `speakers` | Markdown | Name, role/title, order and optional portrait metadata; speaker body biography | Imported from the captured public site |
| `sponsors` | Markdown | Name, tier/order and optional logo/link metadata | Imported from the captured public site |
| `faq` | Markdown | Question, category and order; body answer | Imported from the captured public site |
| `hotlines` | Markdown | Service, description, phones, hours, link and order | Imported from the captured public site |
| `programs` | Markdown | Title, label, lede, order, source URLs, optional hero/related event slugs/gallery; body long-form copy | Imported from the captured public site |
| `galleries` | Markdown | Title, optional source-stated date, order, source URLs and photo source/local/alt metadata | Imported from the captured public site |

`src/data/site.ts` is a typed singleton for site-wide and home-page copy that is not a repeatable content item, including navigation, hero, highlights, cover lines and quote. All content is public and build-time only. Direct repository editing is the current path; the later editor will write these same files through external authentication and trigger a rebuild.

Hosted resource files live in `public/downloads/`. `python3 scripts/build-resources.py` validates those files, refreshes their type, size and page metadata, and generates a first-page cover when PDF tools are available. Its `--check` mode reports stale metadata without changing files.

## Local development

Astro requires Node 22.23.4 or newer. Prefix every command with the pinned Node path:

```sh
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run dev
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run check
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run build
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run preview
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run validate
```

`validate` checks types/content, produces a root-hosted `dist/`, and runs `scripts/check-links.py` over every root-relative built `href` and `src`. `validate:pages` builds with `SITE_URL=https://jysim3.github.io` and `BASE_PATH=/empowher`, then checks that every internal URL carries that exact base. `SITE_URL` defaults to `http://localhost:4321` and `BASE_PATH` to `/`, so local development and a future custom-domain build remain root-hosted.

Routes use directory output and `trailingSlash: 'always'`, producing `route/index.html` so GitHub Pages serves route URLs without redirect-dependent `.html` paths. Components pass internal URLs through `withBase`. Astro 7's installed Sätteri Markdown processor does not accept rehype plugins without an additional package, so a no-dependency `astro:build:done` integration applies the same helper to root-relative `href` and `src` attributes in rendered HTML, including all collection Markdown. Astro's imported-image pipeline emits base-aware asset URLs. The shared head combines the configured site, base and current route for canonical URLs; preview builds default to `noindex, nofollow`, and `public/robots.txt` also disallows crawling until launch.

Pushes to `main` deploy `dist/` to the public GitHub Pages project site at <https://jysim3.github.io/empowher/> through `.github/workflows/deploy-pages.yml`. The preview repository is public. Domain changes, redirects and production Wix configuration remain owner decisions.

## Captured event import

`python3 scripts/import-events.py content` reproducibly imports all captured Wix event detail pages into the events collection without network access. Full descriptions come from the event's Ricos rich-content document in the git-ignored, machine-local `reference/original-site/html/` capture; individual events fall back to the shorter plain-text capture when no matching rich content is available. If the entire HTML capture directory is absent, the command warns clearly and preserves existing event bodies, including with `--force`. It otherwise preserves an existing Markdown body unless passed `--force`. `python3 scripts/import-events.py images` is the separate networked step: it downloads missing first images through Wix's 1200 by 1200 fit endpoint into `src/assets/events/`, converts posters to JPEG where supported, then attaches their relative paths to the event frontmatter. Both commands are idempotent.

## Later-phase boundary

Organisation content is imported with `python3 scripts/import-org.py content`. Its separate `images` command uses Wix fit endpoints and atomic downloads to attach local portraits and logos; the pages render before that networked step runs.

Programme and gallery content is imported offline with `python3 scripts/import-programs.py content`; `audit` reports capture word and photo selection counts. Its separate `images` command fetches the selected whole photos and attaches them to gallery entries. Programme and gallery pages remain buildable before images are downloaded.

Transactions stay behind outbound HTTPS links, so the static information architecture does not depend on a future provider. Replacing Wix requires separate decisions on identity, privacy, payments, refunds, migration and administration. GitHub Pages has no application server, so the committee editing screen will require an external authentication and Git-writing service.
