#!/usr/bin/env python3
"""Import captured Wix events and, separately, download their source images."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = ROOT / "reference/original-site/pages"
HTML_DIR = ROOT / "reference/original-site/html"
CONTENT_DIR = ROOT / "src/content/events"
ASSET_DIR = ROOT / "src/assets/events"
WIX_EVENT_BASE = "https://www.empowhersydney.com/event-details/"
MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "June": 6,
    "July": 7, "Aug": 8, "Sept": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
DATE_RE = re.compile(
    r"^(?P<day>\d{1,2}) (?P<month>Jan|Feb|Mar|Apr|May|June|July|Aug|Sept|Oct|Nov|Dec) "
    r"(?P<year>\d{4}), (?P<start>\d{1,2}:\d{2} [ap]m) – (?P<end>\d{1,2}:\d{2} [ap]m)$"
)
EMOJI_PREFIX = re.compile(r"^[^\w\d#*\[]+\s*")
DECORATIVE_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]")


class ScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []
        self._buffer: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._buffer is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._buffer is not None:
            self.scripts.append("".join(self._buffer))
            self._buffer = None


def capture_files() -> list[Path]:
    return sorted(
        path for path in CAPTURE_DIR.glob("event-details__*.md")
        if not path.name.endswith("__form.md")
    )


def section(text: str, start: str, end: str) -> str:
    match = re.search(re.escape(start) + r"\n\n(.*?)(?=\n\n" + re.escape(end) + r"|\Z)", text, re.S)
    return match.group(1).strip() if match else ""


def content_lines(text: str) -> list[str]:
    captured = section(text, "## Content", "## Images")
    return captured.splitlines()


def parse_time(raw: str, hong_kong: bool) -> tuple[str | None, str | None, bool]:
    if raw == "Date and time is TBD":
        return None, None, True
    match = DATE_RE.fullmatch(raw)
    if not match:
        raise ValueError(f"unrecognised date: {raw!r}")
    values = match.groupdict()
    zone = ZoneInfo("Asia/Hong_Kong" if hong_kong else "Australia/Sydney")
    base = datetime(int(values["year"]), MONTHS[values["month"]], int(values["day"]))
    start_time = datetime.strptime(values["start"], "%I:%M %p").time()
    end_time = datetime.strptime(values["end"], "%I:%M %p").time()
    start = datetime.combine(base.date(), start_time, zone)
    end = datetime.combine(base.date(), end_time, zone)
    if end <= start:
        end = end.replace(day=end.day + 1)
    return start.isoformat(), end.isoformat(), False


def clean_title(title: str) -> str:
    title = re.sub(r"\s*\|\s*Empowher Sydney Inc\s*$", "", title).strip()
    return re.sub(r"^CANCELLED\s*[-:–]?\s*", "", title, flags=re.I).strip()


def location_parts(raw: str) -> tuple[str, str, str]:
    if raw == "Location is TBD":
        return raw, "Sydney", raw
    bits = [part.strip() for part in raw.split(",")]
    venue = bits[0]
    if raw.endswith("Hong Kong"):
        locality = "Hong Kong"
    else:
        locality = "Sydney"
        for part in bits[1:]:
            match = re.search(r"(?:^|\s)([A-Za-z][A-Za-z .'-]+) NSW \d{4}", part)
            if match:
                locality = match.group(1).strip()
                break
    address = ", ".join(bits[1:]) or raw
    return venue, locality, address


def comparable_title(line: str) -> str:
    line = re.sub(r"^#{1,6}\s+", "", line.strip())
    line = re.sub(r"^Event Title:\s*", "", line, flags=re.I)
    line = line.strip("*_ ")
    line = re.sub(r"[^\w\s]+$", "", line, flags=re.UNICODE)
    return re.sub(r"\s+", " ", line).strip().casefold()


def render_inline(nodes: list[object]) -> str:
    rendered: list[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("type") != "TEXT":
            rendered.append(render_inline(node.get("nodes", [])))
            continue
        text_data = node.get("textData", {})
        if not isinstance(text_data, dict):
            continue
        text = str(text_data.get("text", ""))
        decorations = text_data.get("decorations", [])
        if not isinstance(decorations, list):
            decorations = []
        link = next((item for item in decorations if isinstance(item, dict) and item.get("type") == "LINK"), None)
        if isinstance(link, dict):
            link_data = link.get("linkData", {})
            link_value = link_data.get("link", {}) if isinstance(link_data, dict) else {}
            url = link_value.get("url") if isinstance(link_value, dict) else None
            if url:
                text = f"[{text}]({url})"
        types = {item.get("type") for item in decorations if isinstance(item, dict)}
        if "ITALIC" in types and text.strip():
            text = f"*{text}*"
        if "BOLD" in types and text.strip():
            text = f"**{text}**"
        rendered.append(text)
    return "".join(rendered).strip()


def render_list_item(node: dict[str, object], marker: str) -> list[str]:
    blocks: list[str] = []
    for child in node.get("nodes", []):
        if not isinstance(child, dict):
            continue
        if child.get("type") in {"BULLETED_LIST", "ORDERED_LIST"}:
            nested = render_rich_nodes([child])
            if nested:
                blocks.extend(f"  {line}" for line in nested.splitlines())
        else:
            block = render_rich_node(child)
            if block:
                blocks.extend(block.splitlines())
    if not blocks:
        return []
    return [f"{marker} {blocks[0]}", *(f"  {line}" for line in blocks[1:])]


def render_rich_node(node: dict[str, object]) -> str:
    node_type = node.get("type")
    children = node.get("nodes", [])
    children = children if isinstance(children, list) else []
    if node_type == "PARAGRAPH":
        return render_inline(children)
    if node_type == "HEADING":
        heading_data = node.get("headingData", {})
        level = heading_data.get("level", 1) if isinstance(heading_data, dict) else 1
        markdown_level = max(2, min(6, int(level) + 1))
        text = render_inline(children)
        return f"{'#' * markdown_level} {text}" if text else ""
    if node_type in {"BULLETED_LIST", "ORDERED_LIST"}:
        lines: list[str] = []
        for index, child in enumerate(children, start=1):
            if isinstance(child, dict) and child.get("type") == "LIST_ITEM":
                marker = "-" if node_type == "BULLETED_LIST" else f"{index}."
                lines.extend(render_list_item(child, marker))
        return "\n".join(lines)
    if node_type == "LIST_ITEM":
        return "\n".join(render_list_item(node, "-"))
    if node_type == "BLOCKQUOTE":
        text = render_rich_nodes(children)
        return "\n".join(f"> {line}" for line in text.splitlines())
    if node_type in {"IMAGE", "GALLERY", "VIDEO", "DIVIDER"}:
        return ""
    return render_inline(children)


def render_rich_nodes(nodes: list[object]) -> str:
    blocks = [render_rich_node(node) for node in nodes if isinstance(node, dict)]
    return "\n\n".join(block for block in blocks if block.strip())


def find_rich_documents(value: object, slug: str, decoded_depth: int = 0) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    if isinstance(value, dict):
        state = value.get("EventsPageInitialState")
        if isinstance(state, dict):
            event_state = state.get("event", {})
            event = event_state.get("event", {}) if isinstance(event_state, dict) else {}
            navigation = state.get("navigation", {})
            description = event.get("longDescription") if isinstance(event, dict) else None
            if (
                isinstance(event, dict)
                and isinstance(navigation, dict)
                and event.get("slug") == slug
                and navigation.get("slug") == slug
                and isinstance(description, dict)
                and isinstance(description.get("nodes"), list)
            ):
                matches.append(description)
        for child in value.values():
            matches.extend(find_rich_documents(child, slug, decoded_depth))
    elif isinstance(value, list):
        for child in value:
            matches.extend(find_rich_documents(child, slug, decoded_depth))
    elif isinstance(value, str) and decoded_depth < 2:
        candidate = html.unescape(value).strip()
        if candidate.startswith(("{", "[")):
            try:
                matches.extend(find_rich_documents(json.loads(candidate), slug, decoded_depth + 1))
            except json.JSONDecodeError:
                pass
    return matches


def rich_body(slug: str) -> str | None:
    html_path = HTML_DIR / f"event-details__{slug}.html"
    if not html_path.is_file():
        return None
    collector = ScriptCollector()
    collector.feed(html_path.read_text(encoding="utf-8", errors="replace"))
    for script in collector.scripts:
        for candidate in (script, html.unescape(script)):
            try:
                decoded = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            documents = find_rich_documents(decoded, slug)
            if len(documents) == 1:
                nodes = documents[0].get("nodes", [])
                return render_rich_nodes(nodes if isinstance(nodes, list) else [])
            if len(documents) > 1:
                print(f"warning: multiple rich-content documents matched {slug}; using plain-text fallback.", file=sys.stderr)
                return None
    return None


def clean_body(raw: str, title: str) -> str:
    output: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped in {"Show More", "Share this event"}:
            continue
        stripped = re.sub(r"^#{4,6}\s+", "### ", stripped)
        if stripped and not stripped.startswith(("#", "-", "*", "[")):
            stripped = EMOJI_PREFIX.sub("", stripped)
        stripped = re.sub(r"^([-*])\s+[^\w\d#*\[]+\s*", r"\1 ", stripped)
        stripped = re.sub(r"\s{2,}", " ", DECORATIVE_EMOJI.sub("", stripped)).strip()
        output.append(stripped)
    first_content = next((index for index, line in enumerate(output) if line), None)
    if first_content is not None and comparable_title(output[first_content]) == comparable_title(title):
        output.pop(first_content)
        if first_content < len(output) and not output[first_content]:
            output.pop(first_content)
    while output and not output[-1]:
        output.pop()
    return "\n".join(output).strip()


def parse_event(path: Path, use_rich_content: bool = True) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    slug = path.stem.removeprefix("event-details__")
    lines = content_lines(text)
    title_line = next((line[3:] for line in lines if line.startswith("## ")), "")
    title = clean_title(title_line)
    time_location = section(text, "### Time & Location", "### About the event").split("\n\n")
    if len(time_location) < 2:
        raise ValueError("missing Time & Location values")
    raw_date, raw_location = time_location[0].strip(), time_location[1].strip()
    hong_kong = raw_location.endswith("Hong Kong")
    start, end, date_tbd = parse_time(raw_date, hong_kong)
    venue, locality, address = location_parts(raw_location)

    after_title = lines.index(next(line for line in lines if line.startswith("## "))) + 1
    values = [line.strip() for line in lines[after_title:] if line.strip()]
    pipe_index = values.index("|")
    summary = re.sub(r"\s{2,}", " ", DECORATIVE_EMOJI.sub("", values[pipe_index + 2])).strip()
    status_line = values[pipe_index + 3]
    title_status = title_line.lower()
    if "cancelled" in title_status or "cancelled" in status_line.lower():
        status = "cancelled"
    elif "sold out" in title_status or "sold out" in status_line.lower():
        status = "sold-out"
    elif "registration is closed" in status_line.lower() or "tickets are not on sale" in status_line.lower():
        status = "closed"
    else:
        status = "scheduled"

    about = section(text, "### About the event", "### Share this event")
    rich = rich_body(slug) if use_rich_content else None
    images = section(text, "## Images", "THIS SECTION DOES NOT EXIST")
    image_match = re.search(r"^- (https?://\S+)(?: — alt: (.*))?$", images, re.M)
    return {
        "slug": slug, "title": title, "start": start, "end": end,
        "dateTbd": date_tbd, "venue": venue, "locality": locality,
        "address": address, "summary": summary,
        "registrationUrl": WIX_EVENT_BASE + slug, "status": status,
        "sourceImage": image_match.group(1) if image_match else None,
        "imageAlt": (image_match.group(2) or title).strip() if image_match else None,
        "body": clean_body(rich if rich is not None else about, title),
        "bodySource": "rich" if rich is not None else "fallback",
    }


def split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"^---\n.*?\n---\n?(.*)$", text, re.S)
    return (match.group(0), match.group(1).lstrip("\n")) if match else ("", text)


def frontmatter(event: dict[str, object], image_path: str | None = None) -> str:
    order = ["title", "start", "end", "dateTbd", "venue", "locality", "address", "summary",
             "registrationUrl", "status", "sourceImage", "imageAlt"]
    lines = ["---"]
    for key in order:
        value = event.get(key)
        if value is None or (key == "dateTbd" and not value):
            continue
        rendered = "true" if value is True else json.dumps(value, ensure_ascii=False)
        lines.append(f"{key}: {rendered}")
    if image_path:
        lines.append(f"image: {json.dumps(image_path)}")
    lines.append("---")
    return "\n".join(lines)


def existing_image(text: str) -> str | None:
    match = re.search(r'^image:\s*["\']?([^"\'\n]+)', text, re.M)
    return match.group(1).strip() if match else None


def import_content(force: bool) -> int:
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    html_available = HTML_DIR.is_dir()
    if not html_available:
        print(
            f"warning: {HTML_DIR} is missing; it is a git-ignored local capture. "
            "Existing event bodies will be kept unchanged.",
            file=sys.stderr,
        )
    events = [parse_event(path, use_rich_content=html_available) for path in capture_files()]
    expected = {f"{event['slug']}.md" for event in events}
    for path in CONTENT_DIR.glob("*.md"):
        if path.name not in expected:
            path.unlink()
    written = 0
    for event in events:
        target = CONTENT_DIR / f"{event['slug']}.md"
        old = target.read_text(encoding="utf-8") if target.exists() else ""
        _, old_body = split_frontmatter(old)
        preserve_for_missing_html = not html_available and bool(old)
        body = event["body"] if (force or not old) and not preserve_for_missing_html else old_body.rstrip()
        image_path = existing_image(old)
        new = frontmatter(event, image_path) + "\n\n" + str(body).rstrip() + "\n"
        if new != old:
            target.write_text(new, encoding="utf-8")
            written += 1
    print(f"Imported {len(events)} events; wrote {written} files.")
    rich_slugs = [str(event["slug"]) for event in events if event["bodySource"] == "rich"] if html_available else []
    fallback_slugs = [str(event["slug"]) for event in events if event["bodySource"] == "fallback"] if html_available else []
    print(f"Rich content: {len(rich_slugs)}; plain-text fallback: {len(fallback_slugs)}.")
    print("Fallback slugs: " + (", ".join(fallback_slugs) if fallback_slugs else "none"))
    if not html_available:
        preserved_count = sum(1 for event in events if (CONTENT_DIR / (str(event["slug"]) + ".md")).exists())
        print(f"Existing bodies preserved: {preserved_count}.")
    return 0


def resized_wix_url(source: str) -> str:
    base = source.split("/v1/", 1)[0]
    filename = Path(urlparse(source).path).name
    # "fit" keeps the whole poster; "fill" cropped the text off event artwork.
    return f"{base}/v1/fit/w_1200,h_1200,q_82/{filename}"


def as_jpeg(path: Path) -> Path:
    """Posters arrive as large PNGs; store them as JPEG when Pillow is installed."""
    if path.suffix.lower() != ".png":
        return path
    try:
        from PIL import Image
    except ImportError:
        return path
    with Image.open(path) as image:
        flat = Image.new("RGB", image.size, "white")
        flat.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
        jpeg = path.with_suffix(".jpg")
        flat.save(jpeg, quality=84, optimize=True)
    path.unlink()
    return jpeg


def download_images() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    for event in (parse_event(path) for path in capture_files()):
        source = event.get("sourceImage")
        if not source:
            continue
        suffix = Path(urlparse(str(source).split("/v1/", 1)[0]).path).suffix.lower() or ".jpg"
        target = ASSET_DIR / f"{event['slug']}{suffix}"
        existing = sorted(ASSET_DIR.glob(f"{event['slug']}.*"))
        if existing:
            target = existing[0]
        else:
            request = urllib.request.Request(resized_wix_url(str(source)), headers={"User-Agent": "EmpowHER-event-import/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response, target.open("wb") as output:
                output.write(response.read())
            downloaded += 1
            target = as_jpeg(target)
        content = CONTENT_DIR / f"{event['slug']}.md"
        old = content.read_text(encoding="utf-8")
        _, body = split_frontmatter(old)
        relative = f"../../assets/events/{target.name}"
        content.write_text(frontmatter(event, relative) + "\n\n" + body.rstrip() + "\n", encoding="utf-8")
    print(f"Downloaded {downloaded} images.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    content = subparsers.add_parser("content", help="write or refresh event Markdown from the capture")
    content.add_argument("--force", action="store_true", help="replace existing Markdown bodies")
    subparsers.add_parser("images", help="download missing Wix images and attach them to content")
    args = parser.parse_args()
    try:
        return import_content(args.force) if args.command == "content" else download_images()
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
