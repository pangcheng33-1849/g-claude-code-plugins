from __future__ import annotations

"""Helpers for locating and normalizing markdown image references."""

import re
import urllib.parse

from .markdown_preprocess import _parse_html_attrs


def _strip_markdown_link_title(target: str) -> str:
    """Drop a trailing Markdown link title without truncating paths with spaces."""

    match = re.match(r'^(?P<dest>.+?)\s+(?P<title>"[^"]*"|\'[^\']*\'|\([^()]*\))\s*$', target)
    if match:
        return match.group("dest").strip()
    return target


def normalize_markdown_image_target(raw_target: str) -> str:
    target = raw_target.strip()
    target = _strip_markdown_link_title(target)
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if target.startswith("attachment://"):
        parsed = urllib.parse.urlparse(target)
        if parsed.netloc:
            target = urllib.parse.unquote(f"{parsed.netloc}{parsed.path}")
        else:
            target = urllib.parse.unquote(parsed.path)
    elif target.startswith("file://"):
        parsed = urllib.parse.urlparse(target)
        target = urllib.parse.unquote(parsed.path)
    elif target.startswith("@/"):
        target = target[1:]
    elif target.startswith("@") and not target.startswith("@@"):
        target = target[1:]
    return target


def mask_non_rendered_regions(markdown: str) -> str:
    masked = re.sub(
        r"```.*?```",
        lambda match: " " * (match.end() - match.start()),
        markdown,
        flags=re.DOTALL,
    )
    masked = re.sub(
        r"`[^`\n]+`",
        lambda match: " " * (match.end() - match.start()),
        masked,
    )
    return masked


def extract_markdown_image_sources(markdown: str) -> list[str]:
    searchable = mask_non_rendered_regions(markdown)
    ordered_matches: list[tuple[int, str]] = []
    for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", searchable):
        normalized = normalize_markdown_image_target(match.group(1))
        if normalized:
            ordered_matches.append((match.start(), normalized))
    for match in re.finditer(r"<(?:img|image)\b([^>]*)/?>", searchable, flags=re.IGNORECASE):
        attrs = _parse_html_attrs(match.group(1) or "")
        candidate = (
            attrs.get("src")
            or attrs.get("url")
            or attrs.get("path")
            or attrs.get("file")
            or ""
        )
        normalized = normalize_markdown_image_target(candidate)
        if normalized:
            ordered_matches.append((match.start(), normalized))
    ordered_matches.sort(key=lambda item: item[0])
    return [value for _position, value in ordered_matches]


def markdown_contains_images(markdown: str) -> bool:
    return bool(extract_markdown_image_sources(markdown))
