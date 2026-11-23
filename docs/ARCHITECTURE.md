# Architecture

## Stack

Astro 7.4 static output, strict TypeScript and plain Astro components/CSS. Images are imported from `src/assets/` and processed by Astro; Fraunces, Source Sans 3 and Oswald are self-hosted from installed Fontsource packages. There is no client framework, backend, runtime state or external font request. Wix remains the transaction service during Phase 1.

## Surfaces by route

```text
/                    Home page, built now
/events              Event list, Phase 1
/events/[slug]       Event detail with Wix registration link, Phase 1
/women               EmpowHER Women directory, Phase 1
/women/[slug]        Woman profile, Phase 1
/membership          Membership with Wix checkout links, Phase 1
/magazine            Magazine shelf, Phase 1
/blog                 Blog list, Phase 1
/blog/[slug]          Blog post, Phase 1
/about and others     Committee, speakers, sponsors, FAQ, contact and hotline, Phase 1
```

Only `/` is implemented now. Future-route header links point to the corresponding live Wix page until the local route exists.

## Content layout

This is a single-tenant site. Astro's loader-based content collections are defined and strictly validated in `src/content.config.ts`. Every editable item has its own file under `src/content/`; referenced images live in `src/assets/` and pass through the collection `image()` helper and Astro image pipeline.

| Collection | File type | Fields | Who edits |
|---|---|---|---|
| `events` | Markdown | Title, start/end, venue, locality, summary, registration URL, optional image/status; body description | Committee through the later editing screen |
| `members` | Markdown | Name, role/business, portrait, optional links, home feature flag/order; body bio | Committee through the later editing screen |
| `plans` | JSON | Name, numeric yearly price, summary, benefits, checkout URL, order | Committee through the later editing screen |
| `issues` | JSON | Title, issue number, optional confirmed month, cover, Issuu URL | Committee through the later editing screen |

`src/data/site.ts` is a typed singleton for site-wide and home-page copy that is not a repeatable content item, including navigation, hero, highlights, cover lines and quote. All content is public and build-time only. Direct repository editing is the current path; the later editor will write these same files through external authentication and trigger a rebuild.

## Local development

Astro requires Node 22.23.4 or newer. Prefix every command with the pinned Node path:

```sh
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run dev
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run check
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run build
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run preview
PATH=$HOME/.nvm/versions/node/v22.23.5/bin:$PATH npm run validate
```

`validate` checks types/content and then produces `dist/`. Deployment, domain changes, redirects and production Wix configuration belong to the owner.

## Later-phase boundary

Transactions stay behind outbound HTTPS links, so the static information architecture does not depend on a future provider. Replacing Wix requires separate decisions on identity, privacy, payments, refunds, migration and administration. GitHub Pages has no application server, so the committee editing screen will require an external authentication and Git-writing service.
