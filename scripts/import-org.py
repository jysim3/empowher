#!/usr/bin/env python3
"""Import organisation-page content from the captured Wix site.

Run ``content`` offline to build the content collections. Run ``images`` later,
with network access, to fetch and normalise the recorded Wix assets.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "reference/original-site/pages"
HTML = ROOT / "reference/original-site/html"
CONTENT = ROOT / "src/content"
ASSETS = ROOT / "src/assets/org"
UA = "Mozilla/5.0 (compatible; EmpowHER content importer/1.0)"


class CaptureHTML(HTMLParser):
    """Collect visible HTML and JSON scripts from a raw Wix capture."""

    def __init__(self) -> None:
        super().__init__()
        self.visible: list[str] = []
        self.scripts: list[str] = []
        self._hidden = 0
        self._script: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._hidden += 1
        if tag == "script":
            self._script = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._script is not None:
            self.scripts.append("".join(self._script))
            self._script = None
        if tag in {"script", "style", "noscript"} and self._hidden:
            self._hidden -= 1

    def handle_data(self, data: str) -> None:
        if self._script is not None:
            self._script.append(data)
        elif not self._hidden and data.strip():
            self.visible.append(" ".join(data.split()))


def html_capture(name: str) -> CaptureHTML:
    path = HTML / f"{name}.html"
    if not path.is_file():
        raise FileNotFoundError(f"Raw Wix HTML is missing: {path}")
    parsed = CaptureHTML()
    parsed.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parsed


def find_rich_values(value: object, needle: str, decoded_depth: int = 0) -> list[object]:
    """Find Wix JSON objects containing page copy, including encoded JSON strings."""

    matches: list[object] = []
    if isinstance(value, dict):
        if needle.casefold() in json.dumps(value, ensure_ascii=False).casefold():
            matches.append(value)
        for child in value.values():
            matches.extend(find_rich_values(child, needle, decoded_depth))
    elif isinstance(value, list):
        for child in value:
            matches.extend(find_rich_values(child, needle, decoded_depth))
    elif isinstance(value, str) and decoded_depth < 2:
        candidate = html.unescape(value).strip()
        if candidate.startswith(("{", "[")):
            try:
                matches.extend(find_rich_values(json.loads(candidate), needle, decoded_depth + 1))
            except json.JSONDecodeError:
                pass
    return matches


def raw_html_contains(name: str, sample: str) -> bool:
    parsed = html_capture(name)
    haystacks = [" ".join(parsed.visible)]
    for script in parsed.scripts:
        try:
            decoded = json.loads(script)
        except json.JSONDecodeError:
            continue
        if find_rich_values(decoded, sample):
            return True
    normal = lambda value: re.sub(r"\W+", " ", value, flags=re.UNICODE).casefold().strip()
    return normal(sample) in normal(" ".join(haystacks))


def word_count(value: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", value, re.UNICODE))


def prose_sample(value: str) -> str:
    candidates = [
        line.strip("#* -") for line in value.splitlines()
        if len(re.findall(r"\b[\w’'-]+\b", line, re.UNICODE)) >= 8
    ]
    words = re.findall(r"\b[\w’'-]+\b", candidates[0] if candidates else value)
    return " ".join(words[:12])


def capture(name: str) -> str:
    path = PAGES / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Captured page is missing: {path}")
    text = path.read_text(encoding="utf-8")
    match = re.search(r"\n## Content\n\n(.*?)(?=\n## Images\n|\Z)", text, re.S)
    return match.group(1).strip() if match else ""


def images(name: str) -> list[tuple[str, str]]:
    text = (PAGES / f"{name}.md").read_text(encoding="utf-8")
    block = text.partition("\n## Images\n")[2]
    return [(m.group(1), (m.group(2) or "").strip()) for m in re.finditer(
        r"^- (https?://\S+?)(?: — alt: (.*))?$", block, re.M)]


def yaml(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.casefold())).strip("-")


def write(relative: str, text: str, force: bool, preserve_media: bool = True) -> bool:
    path = CONTENT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    text = text.rstrip() + "\n"
    if path.exists() and preserve_media:
        existing = path.read_text(encoding="utf-8")
        local_media = re.findall(r'^(image|logo|photo):\s*("[^\n]+")$', existing, re.M)
        if local_media:
            additions = "".join(f"{field}: {value}\n" for field, value in local_media)
            text = re.sub(r"^---\n", f"---\n{additions}", text, count=1)
    if path.exists() and not force:
        return False
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    return True


def page_file(title: str, lede: str, body: str, source: str, source_image: str | None = None) -> str:
    fields = ["---", f"title: {yaml(title)}", f"lede: {yaml(lede)}", f"sourceUrl: {yaml(source)}"]
    if source_image:
        fields.append(f"sourceImage: {yaml(source_image)}")
    return "\n".join(fields + ["---", "", body.strip()])


def clean_page_body(body: str, lede: str = "") -> str:
    """Remove capture UI markers and exact duplicate introductory copy."""
    lines = [line for line in body.splitlines() if not re.fullmatch(r"\s*\(field:.*\)\s*", line, re.I)]
    body = "\n".join(lines)
    body = re.sub(r"(?m)^The Full Story\s*$\n?", "", body)
    if lede:
        body = re.sub(rf"\A\s*{re.escape(lede)}\s*(?:\n+|\Z)", "", body, count=1)
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def import_pages(force: bool) -> int:
    specs = {
        "about": ("About EmpowHER Sydney", "A safe space for women to meet and find support.", "about-us", "https://www.empowhersydney.com/about-us"),
        "contact": ("Contact", "Feel free share your story.", "contactus", "https://www.empowhersydney.com/contactus"),
        "sponsors-intro": ("Sponsor us", "Impactful Change | Brand Visibility | Corporate Social Responsibility | Networking and Collaboration | Customised Benefits", "sponsors", "https://www.empowhersydney.com/sponsors"),
        "womens-health": ("Women's Health Information", "Resources to help you better understand your body, health, and overall wellness.", "womenshealth", "https://www.empowhersydney.com/womenshealth"),
        "get-involved": ("Get Involved", "There are many ways to make an impact.", "forms", "https://www.empowhersydney.com/forms"),
        "volunteer-intro": ("Join Us as a Volunteer", "Our vibrant community of volunteers is at the heart of everything we do.", "volunteer", "https://www.empowhersydney.com/volunteer"),
    }
    count = 0
    for filename, (title, lede, source_name, url) in specs.items():
        body = capture(source_name)
        body = re.sub(r"^##+\s+.*?\n+", "", body, count=1)
        body = clean_page_body(body, lede)
        if source_name == "about-us":
            body = re.sub(r"^##\s+About\s*\n+", "", body)
        if source_name == "contactus":
            body = body.split("\n\nEmail", 1)[0].strip()
        if source_name == "volunteer":
            body = body.split("\n\n##### 1) About you", 1)[0]
        if source_name == "forms":
            body = body.split("\n\nJoin as a Volunteer", 1)[0].strip()
        if source_name == "sponsors":
            body = re.sub(r"(?m)^(?:EMPOWHER OFFICIAL PARTNERS|####### EMPOWHER GOLD MEMBER|####### EMPOWHER BRONZE SPONSORS)\s*$\n?", "", body).strip()
        source_image = images(source_name)[0][0] if images(source_name) else None
        count += write(f"pages/{filename}.md", page_file(title, lede, body, url, source_image), force)
    committee_image = next((url for url, alt in images("our-team") if alt == "Committee"), None)
    committee_body = (
        "At EmpowHer Sydney Inc. Non Profit Association, we are dedicated to empowering women, "
        "fostering gender equality, and creating a supportive environment for women to thrive. "
        "Join us in breaking barriers, inspiring change, and creating a brighter future for women "
        "everywhere. Together, we can make a difference."
    )
    count += write(
        "pages/committee.md",
        page_file(
            "Official 2026/2027 EmpowHER Committee Members",
            "Welcome to our Empowering Women Team!",
            committee_body,
            "https://www.empowhersydney.com/our-team",
            committee_image,
        ),
        force,
    )
    return count


COMMITTEE = [
    ("Anniewho", "Chairwoman"), ("Sharon Zhang", "Vice Chairwoman"),
    ("Diane Lyons", "Secretary"), ("Nini Lim", "Treasurer"),
    ("Vincenza Visciano", "Committee Member"), ("Jacqueline Lo", "Committee Member"),
]


def import_committee(force: bool) -> int:
    count = 0
    for order, (name, role) in enumerate(COMMITTEE, 1):
        lines = ["---", f"name: {yaml(name)}", f"role: {yaml(role)}", f"order: {order}"]
        lines += ["---"]
        count += write(f"committee/{order:02d}-{slug(name)}.md", "\n".join(lines), force, preserve_media=False)
    return count


SPEAKERS = [
 ("Sonia Samtani", "Clinical Hypnotherapist, NLP Trainer and TEDx Speaker", "Hong Kong"),
 ("Teressa Siu", "International Wellness Speaker, Educator and Former TV Journalist", "Hong Kong"),
 ("Jess Wray", "Exercise Physiologist", ""), ("Sharon Draper", "Psychologist", ""),
 ("Judy Nanavan", "Nutritionist and Metabolic Balance Coach", ""),
 ("Dr Mani Manoharan", "Consultant Endocrinologist", ""),
 ("Tara Commerford", "Non Executive Director, Former GoDaddy MD, Founding team LinkedIn Australia", ""),
 ("Emma McMillan", "National Manager – Client Relationship Services & Senior Consultant Psychologist", ""),
 ("Senior Constable Lisa Latu", "Crime Prevention Officer, Burwood Police Area Command", ""),
 ("Nelly Sinha", "Multicultural Community Liaison Officer", ""),
 ("Stephanie Di Pasqua", "Liberal Member for Drummoyne", ""),
 ("Sally Sitou", "Elected to the House of Representatives for Reid", ""),
 ("Saskia Vromans", "Place Manager Rhodes, City of Canada Bay", ""),
 ("Jennifer Dixon", "Rhodes Resident", ""), ("Minki Bae", "Founder of Merci Boutique", ""),
 ("Sharon Zhang", "Founder of Cafe Botanica", ""), ("Rachel WingMan", "Founder of Wondelab Wellness", ""),
 ("Julie-Anne Whitfield", "Workplace Program Manager", ""), ("Cecile Sy", "Change Manager", ""),
 ("Rhonda Lin", "Counsellor", ""),
]


def fuller_bios() -> dict[str, str]:
    text = capture("our-speakers")
    names = [name.replace("Senior Constable ", "") for name, _, _ in SPEAKERS]
    result: dict[str, str] = {}
    for name in names:
        match = re.search(rf"^{re.escape(name)}\n\n", text, re.M)
        if match:
            endpoints = []
            for other_name, other_title, _ in SPEAKERS:
                other_name = other_name.replace("Senior Constable ", "")
                for marker in (other_name, other_title.split(",", 1)[0]):
                    found = re.search(rf"^({re.escape(marker)})\n", text[match.end():], re.M)
                    if marker != name and found:
                        endpoints.append(found.start())
            body = text[match.end():match.end() + min(endpoints)] if endpoints else text[match.end():]
            paras = [p for p in body.split("\n\n") if len(p.split()) > 12]
            if paras:
                result[name] = "\n\n".join(paras)
    # The capture publishes Lisa's rank on a separate line and appends "MP" to
    # Sally's name, so those two records need their literal published markers.
    lisa = re.search(r"^Senior Constable Lisa Latu\n\n(.*?)(?=\n\nMulticultural Community Liaison Officer)", text, re.M | re.S)
    if lisa: result["Lisa Latu"] = lisa.group(1).strip()
    sally = re.search(r"^Sally Sitou MP\n\n(.*?)(?=\n\nNon Executive Director)", text, re.M | re.S)
    if sally: result["Sally Sitou"] = sally.group(1).strip()
    if "Stephanie Di Pasqua" in result:
        result["Stephanie Di Pasqua"] = result["Stephanie Di Pasqua"].split("\n\nMy husband Rui", 1)[0]
    return result


def import_speakers(force: bool) -> int:
    bios = fuller_bios()
    image_map = {alt.casefold(): url for url, alt in images("empowher-speakers") if alt}
    count = 0
    for order, (name, title, location) in enumerate(SPEAKERS, 1):
        key = name.replace("Senior Constable ", "")
        source = next((url for alt, url in image_map.items() if key.split()[-1].casefold() in alt or key.split()[0].casefold() in alt), None)
        lines = ["---", f"name: {yaml(name)}", f"title: {yaml(title)}", f"order: {order}"]
        if location: lines.append(f"location: {yaml(location)}")
        if source: lines += [f"sourceImage: {yaml(source)}", f"photoAlt: {yaml(name)}"]
        lines += ["---", "", bios.get(key, "")]
        count += write(f"speakers/{order:02d}-{slug(name)}.md", "\n".join(lines), force)
    return count


SPONSOR_NAMES = {
 "Botanica.png": "Cafe Botanica", "MaccasrhoesSponsorlogo.png": "McDonald's Rhodes",
 "BB Logo.jpg": "BB", "Lillys": "Lillys", "DOMOMOTTOGROUPLOGO.png": "Domo Motto Group",
 "Daggiedog.png": "Daggie Dog", "DavidUngLogo.jpg": "David Ung", "VingTsunLogo_BW.png": "Ving Tsun",
 "OutlineRed3.5cmFitFoodtopiaCookie_Label.png": "Fit Foodtopia", "SoulBodylogo.jpg": "Soul Body",
 "SIPHOUR_Logo 1280 x 1280.png": "Sip Hour", "BloomNaturals.png": "Bloom Naturals",
 "StellarLuna Colour Logo_(3000px) .png": "Stellar Luna", "Yumi Candle 5cm x 5cm - Jacqueline Lo.png": "Yumi Candle",
 "YuLiang": "Yu Liang", "Bendigo.jpg": "Bendigo Bank", "artofliving.png": "Art of Living",
 "Sonialogo.png": "Sonia", "GZL-LOGO-BLACK-PRINT.png": "GZL", "mattlogo.png": "Matt",
}


def import_sponsors(force: bool) -> int:
    count = 0
    order = 0
    for url, alt in images("sponsors"):
        name = SPONSOR_NAMES.get(alt)
        if not name: continue
        order += 1
        text = "\n".join(["---", f"name: {yaml(name)}", f"order: {order}", f"sourceImage: {yaml(url)}", f"logoAlt: {yaml(name)}", "---"])
        count += write(f"sponsors/{order:02d}-{slug(name)}.md", text, force)
    return count


def import_faq(force: bool) -> int:
    text = capture("faq")
    parts = re.split(r"^####\s+", text, flags=re.M)[1:]
    count = 0
    for order, part in enumerate(parts, 1):
        question, _, answer = part.partition("\n")
        answer = answer.strip()
        if question.strip() == "EmpowHER Sydney Inc. Membership":
            category = "Membership"
        elif order in {11, 12, 13, 14, 15}:
            category = "Volunteer"
        else:
            category = "General"
        fm = "\n".join([
            "---",
            f"question: {yaml(question.strip())}",
            f"category: {yaml(category)}",
            f"order: {order}",
            "---",
            "",
            answer,
        ])
        count += write(f"faq/{order:02d}-{slug(question)}.md", fm, force)
    return count


def import_hotlines(force: bool) -> int:
    text = capture("helphotline")
    service_names = [
        "WDVCAS",
        "NSW Domestic Violence Line 24/7",
        "Wesley Mission (Homelessness Service)",
        "Elder abuse phone line",
        "Law Access NSW",
        "Beyond Blue 24/7",
        "Suicide Call Back Service 24/7",
        "QLife LGBTIQ+ 3pm - 12am",
        "Counselling with RG",
        "1800 RESPECT 24/7",
        "Link2home",
        "Legal Aid NSW",
        "Lifeline 24/7",
        "Mental Health Line 24/7",
        "Kids Helpline 24/7",
        "13 YARN 24/7",
    ]
    phone_re = re.compile(
        r"(?:1800(?:\s?[A-Z]+|(?:\s?\d){6,})|1300(?:\s?\d){6}|"
        r"13\s?\d{2}\s?\d{2}|0\d{3}(?:\s?\d){6})",
        re.I,
    )
    starts: list[tuple[int, str, int]] = []
    for order, name in enumerate(service_names, 1):
        marker = f"[{name}]" if name == "Lifeline 24/7" else name
        match = re.search(rf"^{re.escape(marker)}(?:\([^\n]+\))?\s*$", text, re.M)
        if not match:
            raise ValueError(f"missing hotline service marker: {name}")
        starts.append((match.start(), name, order))
    starts.sort()
    count = 0
    for index, (position, name, order) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(text)
        block = text[position:end].strip()
        phones = phone_re.findall(block)
        if not phones:
            raise ValueError(f"missing phone number for hotline service: {name}")
        link_match = re.search(r"\[[^]]+\]\((https?://[^)]+)\)", block)
        paragraphs = block.split("\n\n")
        description_parts = []
        for paragraph in paragraphs[1:]:
            if phone_re.search(paragraph) or paragraph in {"Call/Text"}:
                continue
            if paragraph.startswith("[") and "](http" in paragraph:
                continue
            description_parts.append(paragraph)
        description = " ".join(description_parts).strip()
        hours_match = re.search(r"(?:24/7|3pm - 12am|Mon to Fri 9am - 5pm)", block)
        lines = [
            "---",
            f"name: {yaml(name)}",
            f"order: {order}",
            "phoneNumbers:",
            *[f"  - {yaml(phone)}" for phone in phones],
        ]
        if description:
            lines.append(f"description: {yaml(description)}")
        if hours_match:
            lines.append(f"hours: {yaml(hours_match.group(0))}")
        if link_match:
            lines.append(f"link: {yaml(link_match.group(1))}")
        lines.append("---")
        count += write(
            f"hotlines/{order:02d}-{slug(name)}.md",
            "\n".join(lines),
            force,
        )
    return count


def content_command(force: bool) -> None:
    if not HTML.is_dir():
        raise SystemExit(f"Raw Wix HTML is missing: {HTML}. Restore reference/original-site/html/ before importing.")
    source_names = [
        "about-us", "our-team", "our-speakers", "empowher-speakers",
        "sponsors", "faq", "contactus", "helphotline", "womenshealth",
        "forms", "volunteer",
    ]
    for source_name in source_names:
        sample = prose_sample(capture(source_name))
        if sample and not raw_html_contains(source_name, sample):
            raise ValueError(
                f"Markdown content for {source_name} was not found in raw HTML"
            )
    counts = {
        "pages": import_pages(force),
        "committee": import_committee(force),
        "speakers": import_speakers(force),
        "sponsors": import_sponsors(force),
        "faq": import_faq(force),
        "hotlines": import_hotlines(force),
    }
    print("Wrote " + ", ".join(f"{value} {key}" for key, value in counts.items()) + f" ({sum(counts.values())} files total).")


def audit_command() -> None:
    source_names = [
        "about-us", "our-team", "our-speakers", "empowher-speakers",
        "sponsors", "faq", "contactus", "helphotline", "womenshealth",
        "forms", "volunteer",
    ]
    for name in source_names:
        markdown = capture(name)
        parsed = html_capture(name)
        visible = " ".join(parsed.visible)
        sample = prose_sample(markdown)
        matched = raw_html_contains(name, sample) if sample else False
        print(
            f"{name}: markdown={word_count(markdown)}; "
            f"html-visible={word_count(visible)}; matched={'yes' if matched else 'no'}"
        )
    faq_files = sorted((CONTENT / "faq").glob("*.md"))
    categories = {
        re.search(r'^category: "([^"]+)"', path.read_text(encoding="utf-8"), re.M).group(1)
        for path in faq_files
    }
    print(f"faq: categories={len(categories)}; questions={len(faq_files)}")


def download(url: str, target: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as response:
        data = response.read()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.write_bytes(data); temporary.replace(target)


def images_command(force: bool) -> None:
    try:
        from PIL import Image
    except ImportError:
        Image = None
    written = 0
    for folder in ("committee", "speakers", "sponsors", "pages"):
        for path in sorted((CONTENT / folder).glob("*.md")):
            text = path.read_text(encoding="utf-8")
            match = re.search(r'^sourceImage: "([^"]+)"', text, re.M)
            if not match: continue
            url = match.group(1); logo = folder == "sponsors"
            ext = ".png" if logo and urlparse(url).path.lower().endswith(".png") else ".jpg"
            target = ASSETS / folder / f"{path.stem}{ext}"
            if target.exists() and not force: continue
            # Wix resize addresses end with the original file name.
            filename = Path(urlparse(url).path).name
            wix_url = url + ("/v1/fit/w_400,h_400,q_85/" if logo else "/v1/fit/w_1200,h_1600,q_82/") + filename
            download(wix_url, target)
            if ext == ".jpg" and Image:
                with Image.open(target) as image:
                    image.convert("RGB").save(target, "JPEG", quality=88, optimize=True)
            field = "image" if folder == "pages" else ("logo" if logo else "photo")
            relative = f"../../assets/org/{folder}/{target.name}"
            text = re.sub(r"^---\n", f"---\n{field}: {yaml(relative)}\n", text, count=1)
            path.write_text(text, encoding="utf-8"); written += 1
    print(f"Downloaded {written} images.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    content_parser = sub.add_parser("content", help="generate content collections from local captures")
    content_parser.add_argument("--force", action="store_true", help="replace existing generated content")
    image_parser = sub.add_parser("images", help="download images recorded by the content import")
    image_parser.add_argument("--force", action="store_true", help="replace existing downloaded assets")
    sub.add_parser("audit", help="compare normalized Markdown and raw HTML capture content")
    args = parser.parse_args()
    if args.command == "content":
        content_command(args.force)
    elif args.command == "images":
        images_command(args.force)
    else:
        audit_command()


if __name__ == "__main__": main()
