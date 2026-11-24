#!/usr/bin/env python3
"""Refresh metadata and optional PDF covers for hosted resource entries."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "src" / "content" / "resources"
DOWNLOADS = ROOT / "public"
COVERS = ROOT / "src" / "assets" / "resources"
MANAGED_KEYS = ("fileType", "fileSize", "pages", "cover", "coverAlt")


def split_document(path: Path) -> tuple[list[str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path.relative_to(ROOT)} has no YAML frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError(f"{path.relative_to(ROOT)} has unclosed YAML frontmatter")
    return text[4:end].splitlines(), text[end + 4 :]


def scalar(lines: list[str], key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.*?)\s*$")
    for line in lines:
        match = pattern.match(line)
        if match:
            value = match.group(1)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value
    return None


def set_scalar(lines: list[str], key: str, value: str | int) -> list[str]:
    rendered = str(value) if isinstance(value, int) else f'"{value.replace(chr(34), chr(92) + chr(34))}"'
    replacement = f"{key}: {rendered}"
    for index, line in enumerate(lines):
        if re.match(rf"^{re.escape(key)}:\s*", line):
            return [*lines[:index], replacement, *lines[index + 1 :]]
    return [*lines, replacement]


def file_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def pdf_pages(path: Path) -> int | None:
    if shutil.which("pdfinfo"):
        result = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
            if match:
                return int(match.group(1))
    try:
        data = path.read_bytes()
    except OSError:
        return None
    counts = [int(value) for value in re.findall(rb"/Count\s+(\d+)", data)]
    return max(counts, default=0) or None


def render_cover(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    stem = destination.with_suffix("")
    result = subprocess.run(
        ["pdftoppm", "-f", "1", "-singlefile", "-scale-to-x", "600", "-scale-to-y", "-1", "-jpeg", str(source), str(stem)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftoppm failed for {source.relative_to(ROOT)}: {result.stderr.strip()}")


def expected_metadata(path: Path, lines: list[str]) -> tuple[dict[str, str | int], Path | None]:
    relative_file = scalar(lines, "file")
    if not relative_file:
        return {}, None
    if relative_file.startswith("/") or ".." in Path(relative_file).parts or not relative_file.startswith("downloads/"):
        raise ValueError(f"{path.relative_to(ROOT)} has an unsafe hosted file path: {relative_file}")
    source = DOWNLOADS / relative_file
    if not source.is_file():
        raise FileNotFoundError(f"{path.relative_to(ROOT)} references missing public/{relative_file}")
    suffix = source.suffix.removeprefix(".").upper() or "FILE"
    metadata: dict[str, str | int] = {"fileType": suffix, "fileSize": file_size(source.stat().st_size)}
    if suffix == "PDF":
        pages = pdf_pages(source)
        if pages:
            metadata["pages"] = pages
    cover_destination = None
    if suffix == "PDF" and not scalar(lines, "cover") and shutil.which("pdftoppm"):
        cover_destination = COVERS / f"{path.stem}.jpg"
        metadata["cover"] = f"../../assets/resources/{path.stem}.jpg"
        metadata["coverAlt"] = f"Cover of {scalar(lines, 'title') or path.stem}"
    return metadata, cover_destination


def process(path: Path, check: bool) -> list[str]:
    lines, body = split_document(path)
    expected, cover_destination = expected_metadata(path, lines)
    if not expected:
        return []
    stale = [key for key, value in expected.items() if scalar(lines, key) != str(value)]
    # A page count the script wrote earlier is wrong once the file is no longer a
    # PDF (or its pages can no longer be read): drop it rather than show a stale one.
    obsolete = [key for key in ("pages",) if key not in expected and scalar(lines, key)]
    stale += [f"obsolete {key}" for key in obsolete]
    existing_cover = scalar(lines, "cover")
    if existing_cover and existing_cover.startswith("../../assets/resources/"):
        cover_path = (path.parent / existing_cover).resolve()
        if not cover_path.is_file():
            stale.append("cover file")
            if shutil.which("pdftoppm"):
                cover_destination = cover_path
    if not stale:
        return []
    if check:
        return [f"{path.relative_to(ROOT)}: stale {', '.join(dict.fromkeys(stale))}"]
    if cover_destination:
        source = DOWNLOADS / scalar(lines, "file")
        render_cover(source, cover_destination)
    for key, value in expected.items():
        lines = set_scalar(lines, key, value)
    lines = [line for line in lines if not any(line.startswith(f"{key}:") for key in obsolete)]
    path.write_text("---\n" + "\n".join(lines) + "\n---" + body, encoding="utf-8")
    return [f"updated {path.relative_to(ROOT)}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report missing files or stale metadata without writing")
    args = parser.parse_args()
    messages: list[str] = []
    failed = False
    for path in sorted(CONTENT.glob("*.md")):
        try:
            messages.extend(process(path, args.check))
        except (FileNotFoundError, RuntimeError, ValueError) as error:
            messages.append(str(error))
            failed = True
    for message in messages:
        print(message, file=sys.stderr if args.check or failed else sys.stdout)
    if failed or (args.check and messages):
        return 1
    if args.check:
        print(f"Resource metadata is current ({len(list(CONTENT.glob('*.md')))} entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
