#!/usr/bin/env python3
"""Import captured Wix member profiles and, separately, download their images."""

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
CAPTURE_DIR = ROOT / "reference/original-site/pages"
HTML_DIR = ROOT / "reference/original-site/html"
CONTENT_DIR = ROOT / "src/content/members"
ASSET_DIR = ROOT / "src/assets/members"
WIX_BASE = "https://www.empowhersydney.com/"

PROFILES = (
    {
        "capture": "sharonz", "slug": "sharon-zhang", "name": "Sharon Zhang",
        "role": "Vice Chairwoman", "businessName": "Cafe Botanica", "order": 1,
        "profileTitle": "Founder of Cafe Botanica",
        "featuredOnHome": True, "portrait": "../../assets/sharon-s.jpg",
    },
    {
        "capture": "tinaw", "slug": "tina-wu", "name": "Tina Wu",
        "role": "Founder of Bloom Naturals", "businessName": "Bloom Naturals", "order": 2,
        "featuredOnHome": True, "portrait": "../../assets/tina.jpg",
    },
    {
        "capture": "jacquelinelo", "slug": "jacqueline-lo", "name": "Jacqueline Lo",
        "role": "Founder of Yu Liang Pty Ltd", "businessName": "Yu Liang Pty Ltd", "order": 3,
        "featuredOnHome": True, "portrait": "../../assets/jacq.jpg",
    },
    {
        "capture": "copy-of-jacqueline-l", "slug": "joyce-tam", "name": "Joyce Tam",
        "role": "Founder @StellarLuna", "businessName": "@StellarLuna", "order": 6,
        "featuredOnHome": False,
    },
    {
        "capture": "rachelw", "slug": "rachel-wingman", "name": "Rachel WingMan",
        "role": "Founder of Wonderlab Wellness", "businessName": "Wonderlab Wellness", "order": 4,
        "featuredOnHome": True, "portrait": "../../assets/rachel.jpg",
    },
    {
        "capture": "vincenzav", "slug": "vincenza-visciano", "name": "Vincenza Visciano",
        "role": "Founder of Soul Earth Therapies", "businessName": "Soul Earth Therapies", "order": 5,
        "featuredOnHome": True, "portrait": "../../assets/vincenza.jpg",
    },
)


class VisibleText(HTMLParser):
    """Collect visible text so the raw capture is genuinely compared with Markdown."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def section(text: str, start: str, end: str) -> str:
    match = re.search(re.escape(start) + r"\n\n(.*?)(?=\n\n" + re.escape(end) + r"|\Z)", text, re.S)
    return match.group(1).strip() if match else ""


def content_capture(text: str) -> str:
    return section(text, "## Content", "## Images")


def image_capture(text: str) -> list[tuple[str, str]]:
    images = section(text, "## Images", "THIS SECTION DOES NOT EXIST")
    return [
        (match.group(1), (match.group(2) or "").strip())
        for match in re.finditer(r"^- (https?://\S+?)(?: — alt: (.*))?$", images, re.M)
    ]


def markdown_body(content: str) -> str:
    match = re.search(r"^#{3,6}\s+Bio\s*$\n(.*?)(?=^###\s+Let's Get\s*$|\Z)", content, re.M | re.S)
    if not match:
        raise ValueError("missing Bio section")
    body = match.group(1).strip()
    body = re.sub(r"^######\s+", "### ", body, flags=re.M)
    body = re.sub(
        r"^(What advice would you give to other women seeking to start their own businesses or take their current ventures to the next level\?|What is your go-to word, and what does it mean to you\?|Do you currently hold workshops or seminars as part of your business or community involvement\? If so, please provide details about these events, along with any relevant photos\. We're excited to share this information with our community!)$",
        r"### \1", body, flags=re.M,
    )
    body = re.sub(r"^#{1,6}\s+(.+)$", demote_prose_heading, body, flags=re.M)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def demote_prose_heading(match: re.Match[str]) -> str:
    """Turn Wix prose styled as a heading back into a Markdown paragraph."""

    text = match.group(1).strip()
    if "?" in text:
        return match.group(0)
    if len(text) > 100 or text.endswith((".", "!")):
        return text
    return match.group(0)


def word_count(text: str) -> int:
    plain = re.sub(r"\[[^]]+\]\([^)]+\)", " ", text)
    plain = re.sub(r"[#*_>`]", " ", plain)
    return len(re.findall(r"\b[\w’'-]+\b", plain, re.UNICODE))


def html_has_body(capture: str, body: str) -> bool:
    path = HTML_DIR / f"{capture}.html"
    if not path.is_file():
        return False
    raw = html.unescape(path.read_text(encoding="utf-8", errors="replace"))
    collector = VisibleText()
    collector.feed(raw)
    visible = " ".join(collector.parts)
    # Wix also serialises rich content in scripts. Compare against both the visible
    # page and decoded raw state using a distinctive prose sample.
    prose = re.sub(r"^#{1,6}\s+.*$", "", body, flags=re.M)
    sample_words = re.findall(r"\b[\w’'-]+\b", prose, re.UNICODE)[:18]
    sample = " ".join(sample_words)
    normal = lambda value: re.sub(r"\W+", " ", value, flags=re.UNICODE).casefold().strip()
    return bool(sample and (normal(sample) in normal(visible) or normal(sample) in normal(raw)))


def links_for(content: str) -> list[dict[str, str]]:
    before_bio = re.split(r"^#{3,6}\s+Who's That Girl\?\s*$", content, maxsplit=1, flags=re.M)[0]
    links: list[dict[str, str]] = []
    for label, url in re.findall(r"\[([^]]+)\]\((https?://[^)]+)\)", before_bio):
        hostname = (urlparse(url).hostname or "").casefold()
        if "facebook.com" in hostname:
            normalized_label = "Facebook"
        elif "instagram.com" in hostname:
            normalized_label = "Instagram"
        elif "linkedin.com" in hostname:
            normalized_label = "LinkedIn"
        else:
            normalized_label = "Website"
        links.append({"label": normalized_label, "url": url})
    return links


def normalized_banner_alt(alt: str, business_name: str | None, name: str) -> str:
    """Replace machine-like Wix image labels while retaining meaningful site copy."""

    value = alt.strip()
    filename = bool(re.search(r"\.(?:avif|gif|jpe?g|png|svg|webp)$", value, re.I))
    compact = re.sub(r"[^A-Za-z0-9]", "", value)
    identifier = bool(
        len(compact) >= 12
        and re.fullmatch(r"[A-Fa-f0-9]+", compact)
        and sum(character.isdigit() for character in compact) >= len(compact) // 3
    )
    if filename or identifier or not value:
        return f"{business_name} banner" if business_name else f"{name}'s business banner"
    return value


def field_after(content: str, label: str, stopping: tuple[str, ...]) -> str | None:
    pattern = rf"^(?:#{{1,6}}\s+)?{re.escape(label)}:?\s*$\n(.*?)(?=^(?:#{{1,6}}\s+)?(?:{'|'.join(map(re.escape, stopping))}):?\s*$|\Z)"
    match = re.search(pattern, content, re.M | re.S | re.I)
    if not match:
        return None
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", match.group(1)).strip()
    value = re.sub(r"\n{2,}", "\n", value)
    return value if value and value.casefold() != "na" else None


def parse_profile(profile: dict[str, object], html_available: bool) -> dict[str, object]:
    capture = str(profile["capture"])
    text = (CAPTURE_DIR / f"{capture}.md").read_text(encoding="utf-8")
    content = content_capture(text)
    body = markdown_body(content)
    images = image_capture(text)
    portrait_index = 0 if capture == "copy-of-jacqueline-l" else 1
    source_portrait, _portrait_alt = images[portrait_index]
    source_banner = None if capture == "copy-of-jacqueline-l" else images[0][0]
    banner_alt = None if capture == "copy-of-jacqueline-l" else normalized_banner_alt(
        images[0][1], str(profile.get("businessName") or "") or None, str(profile["name"]),
    )
    result = dict(profile)
    result.update({
        "sourceUrl": WIX_BASE + capture,
        "sourcePortrait": source_portrait,
        "portraitAlt": f"Portrait of {profile['name']}",
        "sourceBanner": source_banner,
        "bannerAlt": banner_alt,
        "email": field_after(content, "Email", ("Address", "Language", "Social Media", "Website", "Who's That Girl?")),
        "address": field_after(content, "Address", ("Opening Hours", "Language", "Social Media", "Website", "Who's That Girl?")),
        "languages": field_after(content, "Language", ("Social Media", "Website", "Who's That Girl?")),
        "links": links_for(content),
        "body": body,
        "bodySource": "md",
        "htmlConfirmed": html_has_body(capture, body) if html_available else False,
    })
    return result


def split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"^---\n.*?\n---\n?(.*)$", text, re.S)
    return (match.group(0), match.group(1).lstrip("\n")) if match else ("", text)


def existing_asset(text: str, field: str) -> str | None:
    match = re.search(rf'^{field}:\s*["\']?([^"\'\n]+)', text, re.M)
    return match.group(1).strip() if match else None


def frontmatter(profile: dict[str, object], portrait: str | None = None, banner: str | None = None) -> str:
    scalar_order = (
        "name", "role", "profileTitle", "businessName", "email", "phone", "address", "languages",
        "sourceUrl", "sourcePortrait", "portraitAlt", "sourceBanner", "bannerAlt",
    )
    lines = ["---"]
    for key in scalar_order:
        value = profile.get(key)
        if value:
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    if portrait:
        lines.append(f"portrait: {json.dumps(portrait)}")
    if banner:
        lines.append(f"banner: {json.dumps(banner)}")
    links = profile.get("links", [])
    if links:
        lines.append("links:")
        for link in links:
            lines.append(f"  - label: {json.dumps(link['label'], ensure_ascii=False)}")
            lines.append(f"    url: {json.dumps(link['url'], ensure_ascii=False)}")
    lines.extend([
        f"featuredOnHome: {'true' if profile['featuredOnHome'] else 'false'}",
        f"order: {profile['order']}",
        "---",
    ])
    return "\n".join(lines)


def import_content(force: bool) -> int:
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    html_available = HTML_DIR.is_dir()
    if not html_available:
        print(
            f"warning: {HTML_DIR} is missing; it is a git-ignored local capture. "
            "Existing member bodies will be kept unchanged.", file=sys.stderr,
        )
    profiles = [parse_profile(profile, html_available) for profile in PROFILES]
    written = 0
    for profile in profiles:
        target = CONTENT_DIR / f"{profile['slug']}.md"
        old = target.read_text(encoding="utf-8") if target.exists() else ""
        _, old_body = split_frontmatter(old)
        keep_old = bool(old_body.strip()) and (not force or not html_available)
        body = old_body.rstrip() if keep_old else str(profile["body"])
        portrait = existing_asset(old, "portrait") or profile.get("portrait")
        banner = existing_asset(old, "banner")
        new = frontmatter(profile, str(portrait) if portrait else None, banner) + "\n\n" + body.rstrip() + "\n"
        if new != old:
            target.write_text(new, encoding="utf-8")
            written += 1
        confirmation = "confirmed in raw HTML" if profile["htmlConfirmed"] else "HTML confirmation unavailable"
        print(f"{profile['slug']}: md, {word_count(body)} words ({confirmation})")
    print(f"Imported {len(profiles)} members; wrote {written} files.")
    return 0


def resized_wix_url(source: str) -> str:
    base = source.split("/v1/", 1)[0]
    filename = Path(urlparse(base).path).name
    return f"{base}/v1/fit/w_1200,h_1200,q_82/{filename}"


def as_jpeg(path: Path) -> Path:
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return path
    try:
        from PIL import Image
    except ImportError:
        return path
    with Image.open(path) as image:
        flat = Image.new("RGB", image.size, "white")
        rgba = image.convert("RGBA")
        flat.paste(rgba, mask=rgba.split()[-1])
        target = path.with_suffix(".jpg")
        flat.save(target, quality=84, optimize=True)
    path.unlink()
    return target


def download_one(source: str, stem: str) -> tuple[Path, bool]:
    existing = sorted(ASSET_DIR.glob(f"{stem}.*"))
    if existing:
        return existing[0], False
    suffix = Path(urlparse(source.split("/v1/", 1)[0]).path).suffix.lower() or ".jpg"
    target = ASSET_DIR / f"{stem}{suffix}"
    request = urllib.request.Request(resized_wix_url(source), headers={"User-Agent": "EmpowHER-member-import/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response, target.open("wb") as output:
        output.write(response.read())
    return as_jpeg(target), True


def download_images() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    profiles = [parse_profile(profile, HTML_DIR.is_dir()) for profile in PROFILES]
    downloaded = 0
    for profile in profiles:
        portrait, fresh = download_one(str(profile["sourcePortrait"]), str(profile["slug"]))
        downloaded += int(fresh)
        banner = None
        if profile.get("sourceBanner"):
            banner, fresh = download_one(str(profile["sourceBanner"]), f"{profile['slug']}-banner")
            downloaded += int(fresh)
        content_path = CONTENT_DIR / f"{profile['slug']}.md"
        old = content_path.read_text(encoding="utf-8")
        _, body = split_frontmatter(old)
        portrait_ref = f"../../assets/members/{portrait.name}"
        banner_ref = f"../../assets/members/{banner.name}" if banner else None
        content_path.write_text(frontmatter(profile, portrait_ref, banner_ref) + "\n\n" + body.rstrip() + "\n", encoding="utf-8")
    print(f"Downloaded {downloaded} images.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    content = subparsers.add_parser("content", help="write or refresh member Markdown from the capture")
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
