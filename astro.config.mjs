// @ts-check
import { defineConfig } from 'astro/config';
// Node types are intentionally not a project dependency; this config runs in Node.
// @ts-expect-error -- built-in Node module is available to the config runtime
import { readFile, readdir, writeFile } from 'node:fs/promises';
// @ts-expect-error -- built-in Node module is available to the config runtime
import { fileURLToPath } from 'node:url';
import { normalizeBase, prefixRenderedLinks } from './src/lib/url.ts';

// @ts-expect-error -- process is supplied by the Node config runtime
const base = normalizeBase(process.env.BASE_PATH ?? '/');
/** @type {import('astro').AstroIntegration} */
const baseAwareRenderedLinks = {
  name: 'base-aware-rendered-links',
  hooks: {
    'astro:build:done': async ({ dir }) => {
      /** @param {string} directory */
      const visit = async (directory) => {
        for (const entry of await readdir(directory, { withFileTypes: true })) {
          const path = `${directory}/${entry.name}`;
          if (entry.isDirectory()) await visit(path);
          else if (entry.name.endsWith('.html')) {
            const html = await readFile(path, 'utf8');
            await writeFile(path, prefixRenderedLinks(html, base));
          }
        }
      };
      await visit(fileURLToPath(dir).replace(/\/$/, ''));
    },
  },
};

// https://astro.build/config
export default defineConfig({
  // @ts-expect-error -- process is supplied by the Node config runtime
  site: process.env.SITE_URL ?? 'http://localhost:4321',
  base,
  trailingSlash: 'always',
  build: { format: 'directory' },
  integrations: [baseAwareRenderedLinks],
});
