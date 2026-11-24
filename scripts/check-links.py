#!/usr/bin/env python3
"""Fail when a root-relative link in the built site has no built target."""
from __future__ import annotations

import argparse
import os
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]

class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[str] = []
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"href", "src"} and value and value.startswith("/"):
                self.values.append(value)

def normalize_base(value: str) -> str:
    path = "/" + value.strip("/")
    return "/" if path == "/" else path

def exists(dist: Path, value: str, base: str) -> bool:
    path = unquote(urlsplit(value).path)
    if base != "/":
        path = path[len(base):]
    path = path.lstrip("/")
    candidate = dist / path
    return candidate.is_file() or (candidate / "index.html").is_file() or (not candidate.suffix and candidate.with_suffix(".html").is_file())

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", nargs="?", type=Path, default=ROOT / "dist")
    parser.add_argument("--base", default=os.environ.get("BASE_PATH", "/"), help="expected deployment base path (also read from BASE_PATH)")
    args = parser.parse_args()
    base = normalize_base(args.base)
    if not args.dist.is_dir():
        parser.error(f"build directory does not exist: {args.dist}")
    missing: list[tuple[str, str]] = []
    for page in sorted(args.dist.rglob("*.html")):
        parsed = Links(); parsed.feed(page.read_text(encoding="utf-8", errors="replace"))
        for value in parsed.values:
            path = unquote(urlsplit(value).path)
            if base != "/" and path != base and not path.startswith(f"{base}/"):
                missing.append((str(page.relative_to(args.dist)), f"unprefixed for base {base}: {value}"))
            elif not exists(args.dist, value, base):
                missing.append((str(page.relative_to(args.dist)), value))
    if missing:
        for page, target in missing:
            print(f"{page} → invalid internal target {target}")
        return 1
    print(f"Internal link check passed ({len(list(args.dist.rglob('*.html')))} HTML pages)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
