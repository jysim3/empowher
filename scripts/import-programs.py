#!/usr/bin/env python3
"""Import programme copy and gallery manifests from captured Wix pages.

``content`` and ``audit`` are offline. ``images`` is deliberately separate and
downloads the recorded Wix originals through a bounded fit URL.
"""
from __future__ import annotations

import argparse
import html
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "reference/original-site/pages"
HTML = ROOT / "reference/original-site/html"
CONTENT = ROOT / "src/content"
ASSETS = ROOT / "src/assets/galleries"
UA = "Mozilla/5.0 (compatible; EmpowHER programme importer/1.0)"

PROGRAMS = [
    ("coffee-meetup", "Coffee Meetup", "Programme", "Last Saturday Every Month", ["coffee-meetup"], "coffee-meetup"),
    ("dress-4-success", "Dress 4 Success", "Programme", "Your go-to resource for women looking dress for success and empower themselves in every aspect of their lives.", ["about-us__dress4success-info", "about-us__dress4success-workshop", "about-us__copy-of-empowher-dress-4-success"], "dress-4-success"),
    ("wellness-expo", "Empowering Wellness Expo", "Programme", "A day to connect, engage and thrive together.", ["wellnessexpo2026"], "wellness-expo"),
    ("r-u-ok-day", "R U OK? Day", "Campaign", "A safe space to connect, share and learn.", ["ruokday-2026", "ruok"], "r-u-ok-day-sydney"),
    ("r-u-ok-day-hong-kong", "R U OK? Day Hong Kong", "Campaign", "A safe space to connect, share and learn.", ["r-u-ok-day-hk-2026"], "r-u-ok-day-hong-kong"),
    ("small-business-showcase", "Small Business Showcase", "Programme", "Our mission is to create a vibrant platform that uplifts, supports, and propels female entrepreneurs to new heights.", ["empoweringshowcase", "copy-of-showcase"], "small-business-showcase"),
    ("womens-health-wellness-day", "Women's Health and Wellness Day", "Programme", "Let’s talk about menopause! Join us for an informative and fun session where we can share and learn together.", ["womens-health-wellness-day", "blank"], "womens-health-wellness-day"),
    ("biggest-morning-tea", "Biggest Morning Tea", "Campaign", "Cancer Council's Biggest Morning Tea fundraising event!", ["biggestmorningtea"], "biggest-morning-tea"),
]

GALLERIES = [
    ("coffee-meetup", "Coffee Meetup", None, ["coffee-meetup"]),
    ("dress-4-success", "Dress 4 Success", None, ["about-us__dress4success-workshop", "about-us__copy-of-empowher-dress-4-success"]),
    ("wellness-expo", "Empowering Wellness Expo", "2026", ["wellnessexpo2026"]),
    ("r-u-ok-day-sydney", "R U OK? Day Sydney", "2026", ["ruokday-2026", "ruok"]),
    ("r-u-ok-day-hong-kong", "R U OK? Day Hong Kong", "2026", ["r-u-ok-day-hk-2026"]),
    ("small-business-showcase", "Small Business Showcase", None, ["empoweringshowcase", "june-biz-showcase", "businessworkshop", "august-small-business-workshop"]),
    ("womens-health-wellness-day", "Women's Health and Wellness Day", None, ["womens-health-wellness-day"]),
    ("biggest-morning-tea", "Biggest Morning Tea", "2024", ["biggestmorningtea"]),
    ("april-2024-event", "April 2024 Event", "2024-04", ["aprilempowhernetwork"]),
]

DECORATIVE = re.compile(r"(?:facebook|instagram|logo|website|whatsapp|maccas|bosphorus|billbergia|sing song|titan|merci|balm lab|fitfood|tax store|holistic radiant|cafe botanica|team di|soul\.png|wixbanner)", re.I)

PROGRAM_DETAILS = {
    "wellness-expo": [
        ("Date", "September 26, 2026", None), ("Time", "10AM – 4PM", None),
        ("Venue", "The Connection Event Space", None),
        ("Address", "30 Shoreline Drive, Rhodes NSW 2138", None),
        ("Entry", "Free Entry", None),
        ("Registration", "Register now", "https://www.empowhersydney.com/event-details/empowering-wellness-expo-a-fun-day-for-the-whole-family/form"),
    ],
    "r-u-ok-day": [
        ("Date", "September 5, 2026", None), ("Time", "11AM – 2PM", None),
        ("Venue", "Cafe Botanica", None), ("Address", "Shop 6, 42 Walker Street, Rhodes NSW 2138", None),
        ("Entry", "Free Admission - Ticket Required", None),
        ("Registration", "Save My Spot", "https://www.empowhersydney.com/event-details/r-u-ok-mental-health-awareness/form"),
    ],
    "r-u-ok-day-hong-kong": [
        ("Date", "15 October 2026", None), ("Time", "6:30PM – 8:30PM", None),
        ("Venue", "Soho House", None), ("Address", "33 Des Voeux Road West, Sheung Wan, Hong Kong", None),
        ("Entry", "Free Admission - Limited Seating", None),
        ("Registration", "Register now", "https://www.empowhersydney.com/event-details/r-u-ok-ok-mental-health-community-event/form"),
    ],
}

STRUCTURED_SECTIONS = {
    "wellness-expo": [{"title": "Event highlights", "items": [
        ("Live Entertainment", "Magic with David Ung. Indian classical dance and Ving Tsun Martial Arts performance.", None),
        ("Wellness Market", "Self-care essentials, candles, bakes, crystals, tarot & psychic readings.", None),
        ("Inspiring Talks", "Sharon Draper, Raymond Lo, Jess Wray and Dean De Jesus.", None),
        ("Relax & Unwind", "Fun workout and Pilates sessions.", None),
        ("Kids & Family", "Kids zone, older people's zone, games & lantern-making workshop.", None),
        ("Community & Connection", "Official welcome by City of Canada Bay Mayor Michael Megna, City of Canada Bay stalls, mindfulness facilitator, Psychologist, Counsellor, and Physiotherapist.", None),
        ("Lucky Door Draw & Raffle Draw", "Enter our lucky draw to win exciting prizes.", None),
    ]}],
    "small-business-showcase": [{"title": "Meet the showcase", "items": [
        ("Amanda Bakes", "Cake decorating/baking Cake", None), ("Petals Joy", "Flower Arrangement Workshop", None),
        ("EZI Solutionz", "Support Services", None), ("Office Society", "Business Growth", None),
        ("Balm Lab Australia", "Wellness", None), ("Holistic Radiant", "Home Natural Therapy", "https://www.instagram.com/holisticradiant/#"),
        ("Dee Designs", "Personal & Corporate Gifting", None), ("Origami Yoga", "Yoga", None),
        ("Team Di", "Fitness", None), ("Titan Sports Global", "Sports", "https://www.facebook.com/titansportsglobal3"),
        ("Merci Boutique", "Fashion", None),
    ]}],
    "r-u-ok-day": [{"title": "Event highlights", "items": [
        ("Kids and Family", "A dedicated kids zone with games, plus a dog-friendly area for the whole family.", None),
        ("Community and Connection", "Fresh refreshments, a meet and greet, guided mindfulness sessions, and a lucky draw.", None),
        ("Inspiring Talks", "Real stories. Practical insights. Stronger together — hear from our Community Voices speakers.", None),
    ]}],
    "r-u-ok-day-hong-kong": [{"title": "Event highlights", "items": [
        ("Body and Mind", "Fitness, meditation and magic", None),
        ("Community and Connection", "Mindfulness sessions and lucky draw", None),
        ("Discussion", "Beating Burnout, with Teressa Siu and Sonia Samtani", None),
        ("Speak up", "An open sharing session for attendees", None),
        ("RSVP", "Limited seating — full name registration only", None),
        ("Trigger warning", "Suicide will be discussed as part of the program", None),
    ]}],
}

WELLNESS_VENDOR_NAMES = [
    "Bloom Naturals", "EmpowHER Sydney Inc", "Soul Earth Therapies", "StellarLuna", "Yumi Candle",
    "Fort Healthcare", "Mikayla Vibes", "Strive Motion", "Team Di", "The Conscious Project",
    "Wonderlab", "Yang Ving Tsun Academy", "Canada Bay Council", "Canada Bay Council",
    "Canada Bay Council", "Daggie Dog", "Henry's Dog Toy Swap Meet", "David Ung Magician",
    "Nritya Dhrupadi Music And Dance Research Centre", "Yang Ving Tsun Academy", "Barre Junction",
    "Fit Foodtopia", "Sapoi & Co",
]

def captured(name: str) -> str:
    text = (PAGES / f"{name}.md").read_text(encoding="utf-8")
    match = re.search(r"\n## Content\n\n(.*?)(?=\n## Images\n|\Z)", text, re.S)
    return match.group(1).strip() if match else ""

def image_rows(name: str) -> list[tuple[str, str]]:
    text = (PAGES / f"{name}.md").read_text(encoding="utf-8")
    block = text.partition("\n## Images\n")[2]
    return [(m.group(1), (m.group(2) or "").strip()) for m in re.finditer(r"^- (https?://\S+?)(?: — alt: (.*))?$", block, re.M)]

def words(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text))

def sentence_case_heading(value: str) -> str:
    letters = re.sub(r"[^A-Za-z]", "", value)
    if not letters or letters != letters.upper():
        return value
    lowered = value.lower().capitalize()
    replacements = ((r"\bEmpowher\b", "EmpowHER"), (r"\bR u ok\?", "R U OK?"),
                    (r"\bHong kong\b", "Hong Kong"), (r"\bNsw\b", "NSW"),
                    (r"\bWellness expo\b", "Wellness Expo"), (r"\bNlp\b", "NLP"),
                    (r"\bTedx\b", "TEDx"), (r"\bRsvp\b", "RSVP"))
    for pattern, new in replacements:
        lowered = re.sub(pattern, new, lowered, flags=re.I)
    return lowered

def clean_body(text: str, title: str, lede: str = "") -> str:
    lines = []
    for line in text.splitlines():
        if re.fullmatch(r"\s*(?:top|bottom) of page\s*", line, re.I):
            continue
        if re.fullmatch(r"\s*\(field:.*\)\s*", line, re.I):
            continue
        if re.fullmatch(r"\s*To play, press and hold the enter key\. To stop, release the enter key\.\s*", line, re.I):
            continue
        line = re.sub(r"^[✨•]+\s*", "- ", line)
        line = re.sub(r"\*\*", "", line)
        heading = re.match(r"^(#{2,6})\s+(.+)$", line)
        if heading:
            marks, value = heading.groups()
            value = sentence_case_heading(value.strip())
            value = value.replace("EmpowHer", "EmpowHER").replace("R U OK? day", "R U OK? Day")
            is_question = value.rstrip().endswith("?")
            false_heading = (value.rstrip().endswith((".", "!")) or "," in value or len(value) > 70 or value.lower().startswith("thank you for ")) and not is_question
            line = value if false_heading else f"{marks} {value}"
        lines.append(line.rstrip())
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    repeats = [title, lede]
    for repeated in repeats:
        if repeated:
            body = re.sub(rf"^(?:#+\s+)?{re.escape(repeated.rstrip('.'))}\.?\s*\n+", "", body, flags=re.I)
    return body

class VisibleHTML(HTMLParser):
    """Collect rendered text while ignoring non-visible HTML containers."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.text: list[str] = []
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1
    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.hidden:
            self.hidden -= 1
    def handle_data(self, data: str) -> None:
        if not self.hidden and data.strip():
            self.text.append(data)

def raw_html_verification(name: str, body: str) -> str:
    """Verify representative imported prose against visible or embedded raw HTML."""
    raw = (HTML / f"{name}.html").read_text(encoding="utf-8", errors="replace")
    parsed = VisibleHTML()
    parsed.feed(raw)
    prose = next((line for line in body.splitlines() if words(line) >= 8), "")
    if not prose:
        return "HTML checked (no long prose sample)"
    normal = lambda value: re.sub(r"\W+", " ", html.unescape(value), flags=re.UNICODE).casefold().strip()
    needle = normal(prose)
    return "HTML verified" if needle in normal(" ".join(parsed.text)) or needle in normal(raw) else "HTML differs"

def yaml(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'

def source_url(name: str) -> str:
    return f"https://www.empowhersydney.com/{name}"

ROUTES = {
    "coffee-meetup": "/programs/coffee-meetup",
    "about-us__dress4success-info": "/programs/dress-4-success",
    "wellnessexpo2026": "/programs/wellness-expo",
    "ruokday-2026": "/programs/r-u-ok-day",
    "ruok": "/programs/r-u-ok-day",
    "r-u-ok-day-hk-2026": "/programs/r-u-ok-day-hong-kong",
    "empoweringshowcase": "/programs/small-business-showcase",
    "womens-health-wellness-day": "/programs/womens-health-wellness-day",
    "biggestmorningtea": "/programs/biggest-morning-tea",
    "event-list": "/events", "whatson": "/events", "pricing-plans/list": "/membership",
    "empowher-magazine": "/magazine", "about-us": "/about", "contactus": "/contact",
}

def rewrite_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc not in {"empowhersydney.com", "www.empowhersydney.com"}:
        return url
    path = parsed.path.strip("/")
    if path.endswith("/form"):
        return url
    if path.startswith("event-details/"):
        event = path.split("/", 1)[1]
        if (CONTENT / "events" / f"{event}.md").is_file():
            return f"/events/{event}"
    return ROUTES.get(path, url)

def selected_photos(names: list[str], title: str) -> tuple[list[dict[str, str]], int, list[str]]:
    found = 0
    skipped: list[str] = []
    chosen: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name in names:
        for url, alt in image_rows(name):
            found += 1
            key = url.split("/v1/", 1)[0]
            if key in seen:
                skipped.append("exact duplicate")
                continue
            seen.add(key)
            if DECORATIVE.search(alt) or DECORATIVE.search(url):
                skipped.append("decorative/logo")
                continue
            chosen.append((url, alt))
    total = len(chosen)
    result = []
    for number, (url, alt) in enumerate(chosen, 1):
        descriptive = alt if alt and not re.search(r"\.(?:jpe?g|png)$|^[0-9a-f-]{12,}$|^image\d*", alt, re.I) else ""
        result.append({"source": url, "alt": descriptive or f"{title} photo {number} of {total}"})
    return result, found, skipped

def write(path: Path, text: str, force: bool) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = text.rstrip() + "\n"
    if path.exists() and not force:
        return False
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    return True

def extract_schedule(slug: str, body: str) -> tuple[str, list[tuple[str, str]]]:
    if slug == "wellness-expo":
        match = re.search(r"(?s)### Program schedule.*?\n\n(?P<rows>9:45 AM\n.*?)(?=\n### Wellness market)", body, re.I)
        if not match:
            return body, []
        lines = [line.strip() for line in match.group("rows").splitlines() if line.strip()]
        starts = [i for i, line in enumerate(lines) if re.fullmatch(r"\d{1,2}:\d{2} [AP]M", line)]
        rows = []
        for position, start in enumerate(starts):
            end = starts[position + 1] if position + 1 < len(starts) else len(lines)
            content = lines[start + 1:end]
            rows.append((lines[start], " — ".join(content)))
        body = body[:match.start()] + "Program details are subject to change without notice.\n\n" + body[match.end():]
        return body, rows
    if slug == "r-u-ok-day-hong-kong":
        match = re.search(r"(?s)## Event Schedule \|.*?\n\n.*?Program may change without prior notice\.\n\n(?P<rows>###### 6:20pm.*?###### Ends)(?=\n\n### Hong Kong community voices)", body, re.I)
        if not match:
            return body, []
        lines = [re.sub(r"^######\s+", "", line).strip() for line in match.group("rows").splitlines() if line.strip()]
        starts = [i for i, line in enumerate(lines) if re.fullmatch(r"\d{1,2}:\d{2}(?:am|pm)", line, re.I)]
        rows = []
        for position, start in enumerate(starts):
            end = starts[position + 1] if position + 1 < len(starts) else len(lines)
            rows.append((lines[start], " — ".join(lines[start + 1:end])))
        body = body[:match.start()] + "Program may change without prior notice.\n\n" + body[match.end():]
        return body, rows
    return body, []

def extract_structured_sections(slug: str, body: str) -> tuple[str, list[dict]]:
    sections: list[dict] = []
    if slug == "r-u-ok-day":
        match = re.search(r"(?s)### Community voices\n.*?(?=\n### Bring your furry friend)", body, re.I)
        if match:
            sections.append({"title": "Community voices", "items": [
                ("Sharon Draper", "Psychologist — Beating Burnout", None),
                ("Raymond Lo", "Physiotherapist — Childhood cancer - a father and daughter journey", None),
                ("Dean De Jesus", "CEO of Daggle Dog — How a Dog Heals: A CEO's Journey — Back to Balance", None),
            ]})
            body = body[:match.start()] + body[match.end():]
    elif slug == "r-u-ok-day-hong-kong":
        match = re.search(r"(?s)### Hong Kong community voices\n.*?(?=\n## 感覺不好也沒關係)", body, re.I)
        if match:
            block = match.group(0)
            profiles = []
            specs = [
                ("Anniewho", "Connect", "Founder, EmpowHER Sydney — Executive Producer and Founder, Anniewho Productions", "Engage"),
                ("Matthew Owen", "Engage", "Illusionist — Sleight of Hand Artist", "Thrive"),
                ("Teressa Siu", "Thrive", "International Wellness Speaker — Educator and Former TV Journalist", "Learn"),
                ("Sonia Samtani", "Learn", "Clinical Hypnotherapist — NLP Trainer — TEDx Speaker", "Event highlights"),
            ]
            for name, theme, roles, next_theme in specs:
                start = re.search(rf"### {re.escape(theme)}\n", block, re.I)
                end = re.search(rf"### {re.escape(next_theme)}\n", block[start.end():], re.I) if start and next_theme else None
                segment = block[start.end():start.end() + end.start()] if start and end else block[start.end():] if start else ""
                paragraphs = [re.sub(r"^###\s+", "", part.strip()) for part in re.split(r"\n\n+", segment) if part.strip()]
                bio = " ".join(part for part in paragraphs if not re.fullmatch(r"Anniewho|Matthew|Owen|Teressa|Siu|Sonia|Samtani|Founder, EmpowHER Sydney|Executive Producer and Founder, Anniewho Productions|Illusionist|Sleight of Hand Artist|International Wellness Speaker|Educator and Former TV Journalist|Clinical Hypnotherapist|NLP Trainer|TEDx Speaker", part, re.I))
                profiles.append((name, f"{theme} — {roles}. {bio}".strip(), None))
            sections.append({"title": "Hong Kong community voices", "items": profiles})
            body = body[:match.start()] + body[match.end():]
    elif slug == "wellness-expo":
        speakers = re.search(r"(?s)### Inspiring talks\n.*?(?=\n### What's on)", body, re.I)
        if speakers:
            sections.append({"title": "Meet our speakers", "items": [
                ("Sharon Draper", "Psychologist", "https://www.sharondraper.com.au/"),
                ("Raymond Lo", "Physiotherapist", "https://forthealthcare.com.au/"),
                ("Dean De Jesus", "CEO of Daggie Dog", "https://www.daggiedogtreats.com.au/"),
                ("Jess Wray", "Exercise Physiologist", "https://strivemotion.com.au/"),
            ]})
            body = body[:speakers.start()] + body[speakers.end():]
        vendors = re.search(r"(?s)### Wellness market\n.*?\nBloom Naturals\n\n(?P<rows>.*?)(?=\nWin a prize,)", body, re.I)
        if vendors:
            rows_text = "Bloom Naturals\n\n" + vendors.group("rows")
            cursor = 0
            items = []
            for index, name in enumerate(WELLNESS_VENDOR_NAMES):
                name_match = re.search(rf"(?m)^{re.escape(name)}$", rows_text[cursor:])
                if not name_match:
                    continue
                description_start = cursor + name_match.end()
                if index + 1 < len(WELLNESS_VENDOR_NAMES):
                    next_match = re.search(rf"(?m)^{re.escape(WELLNESS_VENDOR_NAMES[index + 1])}$", rows_text[description_start:])
                    description_end = description_start + next_match.start() if next_match else len(rows_text)
                else:
                    description_end = len(rows_text)
                description = " ".join(line.strip() for line in rows_text[description_start:description_end].splitlines() if line.strip())
                if name == "EmpowHER Sydney Inc" and description.startswith("Handmade Gift of Love. Info desk"):
                    description = "Handmade Gift of Love. Info desk"
                items.append((name, description, None))
                cursor = description_end
            sections.append({"title": "Wellness market", "items": items})
            body = body[:vendors.start()] + body[vendors.end():]
    return body, sections

def remove_structured_copy(slug: str, body: str) -> str:
    if slug == "coffee-meetup":
        return ""
    if slug == "wellness-expo":
        body = re.sub(r"(?s)^.*?(?=### Event recap)", "", body)
        body = re.sub(r"(?s)### Event highlights\n.*?(?=\n### (?:Inspiring talks|What's on))", "", body)
    elif slug == "r-u-ok-day":
        body = re.sub(r"(?is)^## Community Mental Health Day.*?(?=\n(?:### )?Together,)", "", body)
        body = re.sub(r"(?is)### Event highlights\n.*?(?=\n### Bring your furry friend)", "", body)
    elif slug == "r-u-ok-day-hong-kong":
        body = re.sub(r"(?is)^## Community Mental Health Day.*?(?=\n### What is R U OK\? Day)", "一個讓每個人都能安心交流、分享與學習的空間\n\n", body)
        body = re.sub(r"(?is)### Event highlights\n.*?(?=\n## 感覺不好也沒關係)", "", body)
    elif slug == "small-business-showcase":
        body = re.sub(r"(?s)### Meet The Showcase\n.*?(?=\nThere may be no better way)", "", body)
    elif slug == "dress-4-success":
        body = re.sub(r"(?is)^(?:## EmpowHER\n+)?## Dress 4 Success Information\n+", "", body)
        body = re.sub(r"(?im)^### Dress 4 Success Information\n+", "", body)
    elif slug == "womens-health-wellness-day":
        body = re.sub(r"(?im)^### Women's Health & Wellness Day\n+", "", body)
    body = re.sub(r"(?m)^#{7}\s+.*(?:\n+|$)", "", body)
    # Unedited Wix template sentence left on a gallery block: never content.
    body = re.sub(r"(?m)^There may be no better way to communicate what we do than through images\..*(?:\n+|$)", "", body)
    # Headings that only labelled a logo strip have nothing under them once the
    # logos are skipped. Named explicitly: a heading followed by a heading is often
    # a real title and subtitle, so this is not a general rule.
    if slug == "small-business-showcase":
        body = re.sub(
            r"(?m)^#{2,6} (?:EmpowHER Showcase Sponsors|Proudly supported by|Catering|Sponsored by|"
            r"Entertainment sponsored by|Lucky draw sponsored by|Official Partners)[ \t]*(?:\n+|\Z)", "", body)
    body = body.rstrip() + "\n"
    return re.sub(r"\n{3,}", "\n\n", body).strip()

def programme_content(slug: str, title: str, lede: str, names: list[str]) -> tuple[str, list[tuple[str, str]], list[dict]]:
    primary = captured(names[0])
    body = clean_body(primary, title, lede)
    if slug == "dress-4-success":
        body = clean_body(captured("about-us__dress4success-info"), "Dress 4 Success Information", lede)
    if slug == "small-business-showcase":
        body = clean_body(captured("empoweringshowcase"), "EmpowHer Small Business", lede)
    if slug == "biggest-morning-tea" and words(body) < 20:
        desc = re.search(r"^- description: (.*?)(?=\n- og:image:)", (PAGES / "biggestmorningtea.md").read_text(), re.S)
        body = (desc.group(1).strip() + "\n\n" + body) if desc else body
    body, schedule = extract_schedule(slug, body)
    body, extracted_sections = extract_structured_sections(slug, body)
    body = remove_structured_copy(slug, body)
    body = body.replace("### sIU", "### Siu").replace("### We showed up in sydney", "### We showed up in Sydney")
    body = re.sub(r"(?<=\()https?://[^)]+", lambda match: rewrite_url(match.group(0)), body)
    return body, schedule, [*STRUCTURED_SECTIONS.get(slug, []), *extracted_sections]

def programme_body(slug: str, title: str, names: list[str]) -> str:
    lede = next(item[3] for item in PROGRAMS if item[0] == slug)
    return programme_content(slug, title, lede, names)[0]

def import_content(force: bool) -> int:
    changed = 0
    for order, (slug, title, label, lede, names, gallery) in enumerate(PROGRAMS, 1):
        body, schedule, structured_sections = programme_content(slug, title, lede, names)
        fields = ["---", f"title: {yaml(title)}", f"label: {yaml(label)}", f"lede: {yaml(lede)}", f"order: {order}", "sourceUrls:"]
        fields += [f"  - {yaml(source_url(name))}" for name in names]
        fields += [f"gallery: {yaml(gallery)}"]
        if slug in PROGRAM_DETAILS:
            fields.append("details:")
            for label_name, value, url in PROGRAM_DETAILS[slug]:
                fields += [f"  - label: {yaml(label_name)}", f"    value: {yaml(value)}"]
                if url:
                    fields.append(f"    url: {yaml(rewrite_url(url))}")
        if structured_sections:
            fields.append("structuredSections:")
            for section in structured_sections:
                fields += [f"  - title: {yaml(section['title'])}", "    items:"]
                for name, description, url in section["items"]:
                    fields += [f"      - name: {yaml(name)}", f"        description: {yaml(description)}"]
                    if url:
                        fields.append(f"        url: {yaml(url)}")
        if schedule:
            fields.append("schedule:")
            for time, description in schedule:
                fields += [f"  - time: {yaml(time)}", f"    description: {yaml(description)}"]
        fields += ["---", "", body]
        changed += write(CONTENT / "programs" / f"{slug}.md", "\n".join(fields), force)
    for order, (slug, title, date, names) in enumerate(GALLERIES, 1):
        photos, _, _ = selected_photos(names, title)
        fields = ["---", f"title: {yaml(title)}", f"order: {order}"]
        if date:
            fields.append(f"date: {yaml(date)}")
        fields.append("sourceUrls:")
        fields += [f"  - {yaml(source_url(name))}" for name in names]
        existing_images = {}
        gallery_path = CONTENT / "galleries" / f"{slug}.md"
        if gallery_path.exists():
            current = gallery_path.read_text(encoding="utf-8")
            for match in re.finditer(r'^  - sourceImage: "([^"]+)"\n(?:    image: "([^"]+)"\n)?', current, re.M):
                if match.group(2):
                    existing_images[match.group(1)] = match.group(2)
        fields.append("photos:")
        for photo in photos:
            fields.append(f"  - sourceImage: {yaml(photo['source'])}")
            if photo["source"] in existing_images:
                fields.append(f"    image: {yaml(existing_images[photo['source']])}")
            fields.append(f"    alt: {yaml(photo['alt'])}")
        fields += ["---"]
        changed += write(CONTENT / "galleries" / f"{slug}.md", "\n".join(fields), force)
    return changed

def wix_fit(url: str) -> str:
    base = url.split("/v1/", 1)[0]
    filename = urlparse(base).path.rsplit("/", 1)[-1]
    # The host converts to the format named by the trailing file name. Ask for
    # JPEG when the original is a format Pillow may not read (one photo is AVIF).
    stem, dot, ext = filename.rpartition(".")
    if dot and ext.lower() in {"avif", "webp", "heic", "heif"}:
        filename = f"{stem}.jpg"
    return f"{base}/v1/fit/w_1000,h_1000,q_80/{quote(filename)}"

def import_images(force: bool) -> int:
    try:
        from PIL import Image
    except ImportError:
        Image = None
    count = 0
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", UA)]
    for slug, title, _, names in GALLERIES:
        photos, _, _ = selected_photos(names, title)
        target_dir = ASSETS / slug
        target_dir.mkdir(parents=True, exist_ok=True)
        content_path = CONTENT / "galleries" / f"{slug}.md"
        current = content_path.read_text(encoding="utf-8")
        # Which file each source photo was saved as last time. A numbered file is
        # reused only for the same source, so a changed photo order cannot attach
        # an old file to a different photo.
        saved = dict(re.findall(r'^  - sourceImage: "([^"]+)"\n(?:    (?!image:)[^\n]*\n)*    image: "[^"]*/([^"/]+)"', current, flags=re.M))
        text = re.sub(r"^    image: .*\n", "", current, flags=re.M)
        for number, photo in enumerate(photos, 1):
            original_ext = Path(urlparse(photo["source"].split("/v1/", 1)[0]).path).suffix.lower()
            extension = ".jpg" if Image or original_ext not in {".png", ".webp"} else original_ext
            destination = target_dir / f"{number:03d}{extension}"
            if force or not destination.exists() or saved.get(photo["source"]) != destination.name:
                request = urllib.request.Request(wix_fit(photo["source"]))
                temporary = destination.with_suffix(".download")
                with opener.open(request, timeout=45) as response:
                    temporary.write_bytes(response.read())
                temporary.replace(destination)
                if destination.suffix == ".jpg" and Image:
                    try:
                        with Image.open(destination) as image:
                            image.convert("RGB").save(destination, "JPEG", quality=80, optimize=True)
                    except Exception:
                        # Never leave an unreadable file that later runs would treat as done.
                        destination.unlink(missing_ok=True)
                        raise
                count += 1
            marker = f"  - sourceImage: {yaml(photo['source'])}\n"
            replacement = marker + f"    image: {yaml('../../assets/galleries/' + slug + '/' + destination.name)}\n"
            text = text.replace(marker, replacement)
        content_path.write_text(text, encoding="utf-8")
    return count

def audit() -> None:
    print("PROGRAMMES")
    for slug, title, _, _, names, _ in PROGRAMS:
        body = programme_body(slug, title, names)
        md_words = sum(words(captured(name)) for name in names)
        states = [raw_html_verification(name, body if index == 0 else captured(name)) for index, name in enumerate(names)]
        html_state = ", ".join(f"{name}: {state}" for name, state in zip(names, states))
        print(f"{slug}\t{'+'.join(names)} ({html_state})\t{md_words}\t{words(body)}")
    print("GALLERIES")
    total = 0
    for slug, title, _, names in GALLERIES:
        photos, found, skipped = selected_photos(names, title)
        total += len(photos)
        reasons = ", ".join(f"{reason}: {skipped.count(reason)}" for reason in sorted(set(skipped))) or "none"
        print(f"{slug}\t{found}\t{len(photos)}\t{len(skipped)}\t{reasons}")
    print(f"TOTAL\t{total} photos\testimated {total * 250_000} bytes")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("content", "images", "audit"))
    parser.add_argument("--force", action="store_true", help="replace generated files or downloaded images")
    args = parser.parse_args()
    if args.command == "content":
        print(f"Wrote {import_content(args.force)} files")
    elif args.command == "images":
        print(f"Downloaded {import_images(args.force)} images")
    else:
        audit()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
