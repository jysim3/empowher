const ABSOLUTE_SCHEME = /^[a-z][a-z\d+.-]*:/i;

export function normalizeBase(base: string): string {
  const path = `/${base}`.replace(/\/{2,}/g, '/').replace(/\/$/, '');
  return path === '' ? '/' : `${path}/`;
}

/** Prefix a root-relative site URL with Astro's configured base path. */
export function withBase(value: string, base = import.meta.env.BASE_URL): string {
  if (!value || value.startsWith('#') || value.startsWith('//') || ABSOLUTE_SCHEME.test(value)) return value;
  if (!value.startsWith('/')) return value;

  const normalizedBase = normalizeBase(base);
  if (normalizedBase === '/') return value;
  const prefix = normalizedBase.slice(0, -1);
  if (value === prefix || value.startsWith(`${prefix}/`)) return value;
  return `${prefix}${value}`;
}

/** Rewrite rendered root-relative href/src attributes, including Markdown output. */
export function prefixRenderedLinks(html: string, base: string): string {
  return html.replace(/\b(href|src)=(['"])(\/[^'"]*)\2/g, (_match, attribute, quote, value) =>
    `${attribute}=${quote}${withBase(value, base)}${quote}`,
  );
}
