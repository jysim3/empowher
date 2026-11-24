# EmpowHER Sydney

Static Astro rebuild of the public EmpowHER Sydney Inc website. Phase 1 moves public information to a fast, accessible site while checkout and transactions remain on Wix.

Requires Node 22.23.4 or newer (`.nvmrc` pins 22.23.5).

```sh
npm run dev
npm run check
npm run build
npm run preview
npm run validate
npm run validate:pages
```

Local builds use `/` by default. `validate:pages` builds the GitHub Pages preview at the `/empowher/` base path and checks every internal link. Pushes to `main` deploy that preview to <https://jysim3.github.io/empowher/> through GitHub Actions.

See `docs/PRODUCT_SPEC.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and the binding `docs/DESIGN.md`.
