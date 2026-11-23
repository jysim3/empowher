#!/usr/bin/env python3
"""Import captured Wix blog posts and, separately, download their images."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "reference/original-site/pages"
HTML = ROOT / "reference/original-site/html"
CONTENT = ROOT / "src/content/posts"
ASSETS = ROOT / "src/assets/blog"
BASE = "https://www.empowhersydney.com/post/"
UA = "Mozilla/5.0 (compatible; EmpowHER blog importer/1.0)"
CATEGORY_FILES = sorted(PAGES.glob("blog__categories__*.md"))
TAG_FILES = sorted(PAGES.glob("blog__tags__*.md"))
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]")


def capture(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"\n## Content\n\n(.*?)(?=\n## Images\n|\Z)", text, re.S)
    return match.group(1).strip() if match else ""


def slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.casefold())).strip("-")


def post_links(text: str) -> list[str]:
    return re.findall(r"https://www\.empowhersydney\.com/post/([^)\s]+)", text)


def taxonomy() -> tuple[dict[str, list[str]], dict[str, str], dict[str, list[str]]]:
    categories: dict[str, list[str]] = {}
    names: dict[str, str] = {}
    for path in CATEGORY_FILES:
        category = path.stem.removeprefix("blog__categories__")
        body = capture(path)
        title = re.search(r"\[([^]]+)\]\(https://www\.empowhersydney\.com/blog/categories/" + re.escape(category) + r"\)", body)
        names[category] = title.group(1) if title else category.replace("-", " ").title()
        for post in post_links(body):
            categories.setdefault(post, []).append(category)
    tags: dict[str, list[str]] = {}
    for path in TAG_FILES:
        body = capture(path)
        tag_slug = path.stem.removeprefix("blog__tags__")
        title = re.search(r"\[([^]]+)\]\(https://www\.empowhersydney\.com/blog/tags/" + re.escape(tag_slug) + r"\)", body)
        tag = title.group(1) if title else tag_slug.replace("-", " ")
        for post in post_links(body):
            tags.setdefault(post, []).append(tag)
    return categories, names, tags


class PostHTML(HTMLParser):
    """Read JSON-LD and turn the server-rendered Ricos viewer into Markdown."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ld: list[dict[str, object]] = []
        self._script: list[str] | None = None
        self._viewer = 0
        self._runs: list[tuple[str, bool, bool, str | None]] = []
        self.blocks: list[str] = []
        self._tag = ""
        self._list: list[str] = []
        self._link: str | None = None
        self._bold = 0
        self._italic = 0
        self.images: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "script" and values.get("type") == "application/ld+json":
            self._script = []
        if values.get("data-id") == "content-viewer":
            self._viewer = 1
            return
        if self._viewer:
            if tag == "div":
                self._viewer += 1
            if tag in {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"} and not self._tag:
                self._tag = tag
                self._runs = []
            elif tag in {"ul", "ol"}:
                self._list.append(tag)
            elif tag == "a":
                self._link = values.get("href")
            elif tag in {"strong", "b"}:
                self._bold += 1
            elif tag in {"em", "i"}:
                self._italic += 1
            elif tag == "br":
                self._append_run("\n")
            elif tag == "img" and values.get("src"):
                source, alt = values["src"], (values.get("alt") or "").strip()
                self.images.append((source, alt))
                self.blocks.append(f"![{alt}]({source})")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if self._script is not None:
            self._script.append(data)
        elif self._viewer and self._tag:
            self._append_run(data)

    def _append_run(self, data: str) -> None:
        data = EMOJI.sub("", data.replace("\xa0", " "))
        run = (data, bool(self._bold), bool(self._italic), self._link)
        if self._runs and self._runs[-1][1:] == run[1:]:
            previous = self._runs.pop()
            run = (previous[0] + data, *run[1:])
        self._runs.append(run)

    def _inline(self, heading: bool = False) -> str:
        rendered: list[str] = []
        for index, (text, bold, italic, link) in enumerate(self._runs):
            before = next((run[0][-1:] for run in reversed(self._runs[:index]) if run[0]), "")
            after = next((run[0][:1] for run in self._runs[index + 1:] if run[0]), "")
            value = styled(text, bold, italic, before, after, heading)
            if link and value.strip():
                leading = value[:len(value) - len(value.lstrip())]
                trailing = value[len(value.rstrip()):]
                value = f"{leading}[{value.strip()}]({rewrite_url(link)}){trailing}"
            rendered.append(value)
        return re.sub(r"[ \t]+", " ", "".join(rendered)).strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._script is not None:
            try:
                value = json.loads("".join(self._script))
                if isinstance(value, dict): self.ld.append(value)
            except json.JSONDecodeError:
                pass
            self._script = None
        if not self._viewer:
            return
        if tag in {"strong", "b"}:
            self._bold = max(0, self._bold - 1)
        elif tag in {"em", "i"}:
            self._italic = max(0, self._italic - 1)
        elif tag == "a" and self._link:
            self._link = None
        elif tag == self._tag:
            value = self._inline(heading=tag.startswith("h"))
            if value:
                if tag.startswith("h"):
                    value = f"{'#' * min(6, int(tag[1]) + 1)} {value}"
                elif tag == "li":
                    marker = "1." if self._list and self._list[-1] == "ol" else "-"
                    value = f"{marker} {value}"
                elif tag == "blockquote":
                    value = "\n".join(f"> {line}" for line in value.splitlines())
                self.blocks.append(value)
            self._tag, self._runs = "", []
        elif tag in {"ul", "ol"} and self._list:
            self._list.pop()
        if tag == "div":
            self._viewer -= 1


def word_character(value: str) -> bool:
    return bool(value) and (value.isalnum() or value == "_")


def styled(text: str, bold: bool, italic: bool, before: str, after: str, heading: bool = False) -> str:
    leading = text[:len(text) - len(text.lstrip())]
    trailing = text[len(text.rstrip()):]
    core = text.strip()
    if not core:
        return text
    if heading:
        bold = False
    html_style = word_character(before[-1:] if before else "") or word_character(after[:1] if after else "")
    if html_style:
        if italic: core = f"<em>{core}</em>"
        if bold: core = f"<strong>{core}</strong>"
    else:
        if italic: core = f"*{core}*"
        if bold: core = f"**{core}**"
    return leading + core + trailing


def rewrite_url(url: str) -> str:
    if not url.startswith("https://www.empowhersydney.com/"):
        return url
    path = urlparse(url).path
    exact = {
        "/whatson": "/events", "/event-list": "/events",
        "/pricing-plans/list": "/membership", "/membership": "/membership",
        "/empowher-magazine": "/magazine", "/magazine": "/magazine",
        "/empowher-women": "/women", "/women": "/women",
        "/blog": "/blog", "/about-us": "/about", "/contactus": "/contact",
        "/sponsors": "/sponsors", "/faq": "/faq", "/helphotline": "/hotline",
    }
    path = path.rstrip("/") or "/"
    if path in exact: return exact[path]
    # Event pages moved from /event-details/<slug> to /events/<slug>; only link
    # locally when that event file exists, otherwise keep the old site's address.
    if path.startswith("/event-details/"):
        slug = path.split("/event-details/", 1)[1]
        if (ROOT / "src" / "content" / "events" / f"{slug}.md").exists():
            return f"/events/{slug}"
        return url
    if path.startswith("/post/"):
        slug = path.split("/post/", 1)[1]
        if (ROOT / "reference" / "original-site" / "pages" / f"post__{slug}.md").exists():
            return f"/blog/{slug}"
    return url


def words(value: str) -> int:
    value = re.sub(r"!?\[[^]]*\]\([^)]*\)", " ", value)
    return len(re.findall(r"\b[\w’'-]+\b", value, re.UNICODE))


def plain_body(path: Path) -> str:
    body = capture(path)
    body = re.sub(r"\A(?:\[[^]]+\]\(https://www\.empowhersydney\.com/blog[^)]*\)\s*)+", "", body)
    body = re.sub(r"(?mi)^\(field:.*\)\s*$|^Search\s*$", "", body)
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def clean_body(body: str, title: str) -> str:
    body = EMOJI.sub("", body)
    body = re.sub(r"(?m)^([*-]|\d+\.)\s+\s*", r"\1 ", body)
    body = re.sub(r"(?mi)^\(field:.*\)\s*$", "", body)
    body = re.sub(r"(?m)^#\s+", "## ", body)
    first = next((line for line in body.splitlines() if line.strip()), "")
    if re.sub(r"\W+", "", first).casefold() == re.sub(r"\W+", "", title).casefold():
        body = body.replace(first, "", 1).lstrip()
    # Wix sometimes stores numbered section labels as isolated one-item lists (or
    # plain paragraphs) followed by their prose. They are section headings, not
    # ordered lists that restart at every item.
    body = re.sub(r"(?m)^(?:1\. )?(\d+\.\s+[^\n]{3,100})\n\n(?=[^#\n])", r"### \1\n\n", body)
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def excerpts() -> dict[str, str]:
    body = capture(PAGES / "blog.md")
    matches = list(re.finditer(r"\[[^]]+\]\(https://www\.empowhersydney\.com/post/([^)]+)\)\n\n(.*?)(?=\n\n\[[^]]+\]\(https://www\.empowhersydney\.com/profile|\Z)", body, re.S))
    return {m.group(1): " ".join(m.group(2).split()) for m in matches}


def first_sentences(body: str) -> str:
    paragraphs: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "![")) or re.match(r"^(?:[-*]|\d+\.)\s+", line):
            continue
        line = re.sub(r"!?\[([^]]*)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"</?(?:strong|em)>", "", line)
        line = re.sub(r"[*_]+", "", line).strip()
        if re.match(r"^Event Title\s*:", line, re.I):
            continue
        # A short, sentence-less line is a display subheading captured as a
        # paragraph (for example "Empowering Women: Unleashing Your Potential").
        if len(line.split()) <= 10 and not re.search(r"[.!?]$", line):
            continue
        paragraphs.append(line)
    prose = " ".join(paragraphs)
    return prose.strip()


def clean_excerpt(value: str, title: str, body: str) -> str:
    value = re.sub(r"!?\[([^]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"</?(?:strong|em)>", "", value)
    value = re.sub(r"[*_]+", "", value)
    value = re.sub(r"^\s*" + re.escape(title) + r"\s*[:—–-]?\s*", "", value, flags=re.I)
    value = re.sub(r"^\s*Event Title:\s*[^.!?]*(?:[.!?]\s*|$)", "", value, flags=re.I)
    value = " ".join(value.split()).strip()
    first_body_line = next((line.strip("# *_") for line in body.splitlines() if line.strip()), "")
    subtitle = first_body_line.partition(":")[2].strip()
    repeats_subtitle = bool(subtitle) and value.casefold().startswith(subtitle.casefold())
    if len(value.split()) < 12 or repeats_subtitle:
        value = first_sentences(body)
    tokens = value.split()
    if len(tokens) <= 32:
        return value
    prefix = " ".join(tokens[:32])
    sentence = re.search(r"^(.+?[.!?])(?:\s|$)", prefix)
    if sentence and len(sentence.group(1).split()) >= 18:
        return sentence.group(1)
    return " ".join(tokens[:30]).rstrip(".,;:—–-") + "…"


def source_image(path: Path) -> tuple[str | None, str | None]:
    text = path.read_text(encoding="utf-8")
    block = text.partition("\n## Images\n")[2]
    match = re.search(r"^- (https?://\S+)(?: — alt: (.*))?$", block, re.M)
    return (match.group(1), (match.group(2) or "").strip()) if match else (None, None)


def parse_post(path: Path) -> dict[str, object]:
    slug = path.stem.removeprefix("post__")
    html_path = HTML / f"post__{slug}.html"
    parser = PostHTML()
    if html_path.is_file(): parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
    metadata = next((item for item in parser.ld if item.get("@type") == "BlogPosting"), {})
    title = str(metadata.get("headline") or path.read_text(encoding="utf-8").splitlines()[0].removeprefix("# "))
    rich = "\n\n".join(parser.blocks).strip()
    fallback = plain_body(path)
    body = clean_body(rich or fallback, title)
    body = body.replace("![](", f"![{title}](")
    categories, _, tags = taxonomy()
    cover, alt = source_image(path)
    if cover:
        cover_base = source_base(cover)
        body = re.sub(
            r"(?m)^!?\[[^]]*\]\((" + re.escape(cover_base) + r"[^)]*)\)\s*\n?",
            "",
            body,
        ).strip()
    own_excerpt = excerpts().get(slug)
    author_data = metadata.get("author", {})
    author = author_data.get("name") if isinstance(author_data, dict) else None
    published = metadata.get("datePublished")
    if not published: raise ValueError(f"missing published date for {slug}")
    excerpt = clean_excerpt(EMOJI.sub("", own_excerpt or first_sentences(body)), title, body)
    return {"slug": slug, "title": title, "published": str(published),
            "updated": str(metadata.get("dateModified")) if metadata.get("dateModified") != published else None,
            "excerpt": excerpt, "categories": categories.get(slug, []),
            "tags": tags.get(slug, []), "author": author, "sourceImage": cover,
            "imageAlt": alt or title, "sourceUrl": BASE + slug, "body": body,
            "source": "rich-html" if rich else "text-fallback", "textWords": words(fallback),
            "importedWords": words(body), "inlineImages": parser.images}


def yaml(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def existing_cover(text: str) -> str | None:
    match = re.search(r'^coverImage:\s*"?([^"\n]+)', text, re.M)
    return match.group(1) if match else None


def document(post: dict[str, object], cover_image: str | None = None) -> str:
    keys = ["title", "published", "updated", "excerpt", "categories", "tags", "author", "sourceImage", "imageAlt", "sourceUrl"]
    lines = ["---"] + [f"{key}: {yaml(post[key])}" for key in keys if post.get(key) not in (None, "")]
    if cover_image: lines.append(f"coverImage: {yaml(cover_image)}")
    return "\n".join(lines + ["---", "", str(post["body"]).rstrip(), ""])


def posts() -> list[dict[str, object]]:
    if not PAGES.is_dir(): raise FileNotFoundError(f"Captured pages are missing: {PAGES}")
    if not HTML.is_dir(): raise FileNotFoundError(f"Raw Wix HTML is missing: {HTML}. Restore the git-ignored reference/original-site/html/ before importing.")
    return [parse_post(path) for path in sorted(PAGES.glob("post__*.md"))]


def content_command(force: bool) -> None:
    CONTENT.mkdir(parents=True, exist_ok=True)
    values = posts(); written = 0
    for post in values:
        target = CONTENT / f"{post['slug']}.md"
        old = target.read_text(encoding="utf-8") if target.exists() else ""
        new = document(post, existing_cover(old))
        if new == old or (old and not force): continue
        temporary = target.with_suffix(".md.tmp"); temporary.write_text(new, encoding="utf-8"); temporary.replace(target); written += 1
    print(f"Imported {len(values)} posts; wrote {written} files.")
    print(f"Rich content: {sum(p['source'] == 'rich-html' for p in values)}; plain-text fallback: {sum(p['source'] == 'text-fallback' for p in values)}.")


def resized(source: str) -> str:
    base = source.split("/v1/", 1)[0]
    return f"{base}/v1/fit/w_1600,h_1600,q_82/{Path(urlparse(base).path).name}"


def download(url: str, target: Path) -> Path:
    request = urllib.request.Request(resized(url), headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=45) as response: data = response.read()
    temporary = target.with_name(f".{target.name}.part"); temporary.write_bytes(data); temporary.replace(target)
    if target.suffix.lower() == ".png":
        try:
            from PIL import Image
        except ImportError:
            return target
        with Image.open(target) as image:
            rgba = image.convert("RGBA")
            flat = Image.new("RGB", rgba.size, "white")
            flat.paste(rgba, mask=rgba.getchannel("A"))
            jpeg = target.with_suffix(".jpg")
            partial = jpeg.with_name(f".{jpeg.name}.part")
            flat.save(partial, "JPEG", quality=86, optimize=True)
        partial.replace(jpeg); target.unlink(); return jpeg
    return target


def source_base(url: str) -> str:
    return url.split("/v1/", 1)[0]


def replace_source(body: str, source: str, relative: str) -> str:
    base = source_base(source)
    return re.sub(rf"{re.escape(base)}[^\s)]*", relative, body)


def images_command(force: bool) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True); count = 0
    for post in posts():
        source = str(post.get("sourceImage") or "")
        sources: list[tuple[str, str]] = []
        if source: sources.append((source, str(post["slug"])))
        seen = {source_base(source)} if source else set()
        inline_number = 0
        for inline_source, _ in post["inlineImages"]:
            base = source_base(inline_source)
            if base in seen: continue
            seen.add(base); inline_number += 1
            sources.append((inline_source, f"{post['slug']}-inline-{inline_number:02d}"))
        content = CONTENT / f"{post['slug']}.md"; old = content.read_text(encoding="utf-8")
        old = re.sub(r"^coverImage:.*\n", "", old, flags=re.M)
        frontmatter, marker, body = old.partition("\n---\n")
        cover_relative: str | None = None
        for media_source, name in sources:
            suffix = Path(urlparse(source_base(media_source)).path).suffix.lower() or ".jpg"
            candidates = sorted(ASSETS.glob(f"{name}.*"))
            target = candidates[0] if candidates else ASSETS / f"{name}{suffix}"
            if force or not target.exists():
                if force:
                    for candidate in candidates:
                        candidate.unlink()
                    target = ASSETS / f"{name}{suffix}"
                target = download(media_source, target); count += 1
            relative = f"../../assets/blog/{target.name}"
            body = replace_source(body, media_source, relative)
            if media_source == source: cover_relative = relative
        if cover_relative:
            frontmatter = re.sub(r"^---\n", f"---\ncoverImage: {yaml(cover_relative)}\n", frontmatter, count=1)
        content.write_text(frontmatter + marker + body, encoding="utf-8")
    print(f"Downloaded {count} images.")


def audit_command() -> None:
    _, names, _ = taxonomy()
    for post in posts():
        cats = ",".join(names.get(c, c) for c in post["categories"]) or "none"
        print(f"{post['slug']}: source={post['source']}; text={post['textWords']}; imported={post['importedWords']}; date={post['published']}; categories={cats}")
    values = {p["slug"]: p for p in posts()}
    a = values["sold-out-the-july-empowher-coffee-meetup-is-officially-full"]["body"]
    b = values["sold-out-the-july-empowher-coffee-meetup-is-officially-full-1"]["body"]
    print(f"sold-out bodies identical: {'yes' if a == b else 'no'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    content = sub.add_parser("content", help="write post Markdown from local captures")
    content.add_argument("--force", action="store_true", help="replace existing generated Markdown")
    images = sub.add_parser("images", help="download recorded Wix images")
    images.add_argument("--force", action="store_true", help="replace existing downloaded images")
    sub.add_parser("audit", help="report source, word counts, date, and categories per post")
    args = parser.parse_args()
    try:
        if args.command == "content": content_command(args.force)
        elif args.command == "images": images_command(args.force)
        else: audit_command()
        return 0
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
