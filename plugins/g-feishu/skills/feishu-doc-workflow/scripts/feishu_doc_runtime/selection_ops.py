from __future__ import annotations

"""Selection matching and markdown splice helpers for update-doc."""

import pathlib
import re

from .common import TEMP_ELLIPSIS_MARKER


def selection_pattern_parts(selection: str) -> tuple[str, str] | None:
    masked = selection.replace("\\.\\.\\.", TEMP_ELLIPSIS_MARKER)
    if "..." not in masked:
        return None
    start, end = masked.split("...", 1)
    return start.replace(TEMP_ELLIPSIS_MARKER, "..."), end.replace(TEMP_ELLIPSIS_MARKER, "...")


def find_all_literal_occurrences(text: str, needle: str) -> list[tuple[int, int]]:
    results: list[tuple[int, int]] = []
    if not needle:
        return results
    start = 0
    while True:
        index = text.find(needle, start)
        if index < 0:
            break
        results.append((index, index + len(needle)))
        start = index + len(needle)
    return results


def find_all_ellipsis_occurrences(text: str, start_text: str, end_text: str) -> list[tuple[int, int]]:
    if not start_text and not end_text:
        return []
    if start_text and end_text:
        pattern = re.compile(re.escape(start_text) + r".*?" + re.escape(end_text), re.DOTALL)
    elif start_text:
        pattern = re.compile(re.escape(start_text) + r".*$", re.DOTALL)
    else:
        pattern = re.compile(r"^.*?" + re.escape(end_text), re.DOTALL)
    return [(match.start(), match.end()) for match in pattern.finditer(text)]


def resolve_selection_with_ellipsis(text: str, selection: str, *, allow_multiple: bool) -> tuple[list[tuple[int, int]], str]:
    parts = selection_pattern_parts(selection)
    if parts is None:
        literal = selection.replace("\\.\\.\\.", "...")
        matches = find_all_literal_occurrences(text, literal)
        mode = "literal"
    else:
        matches = find_all_ellipsis_occurrences(text, parts[0], parts[1])
        mode = "ellipsis"
    if not matches:
        raise SystemExit(f"selection not found: {selection}")
    if not allow_multiple and len(matches) != 1:
        raise SystemExit(f"selection is not unique: {selection}")
    return matches, mode


def parse_heading_line(line: str) -> tuple[int, str] | None:
    stripped = line.strip()
    standard = re.match(r"^(#{1,9})\s+(.*)$", stripped)
    if standard:
        return len(standard.group(1)), standard.group(2).strip()
    html_heading = re.match(r"^<h([7-9])>(.*?)</h\\1>$", stripped, re.IGNORECASE)
    if html_heading:
        return int(html_heading.group(1)), html_heading.group(2).strip()
    return None


def resolve_selection_by_title(text: str, selection: str) -> tuple[int, int]:
    requested = selection.strip()
    requested_heading = parse_heading_line(requested)
    requested_level = requested_heading[0] if requested_heading else None
    requested_title = requested_heading[1] if requested_heading else requested.lstrip("#").strip()

    lines = text.splitlines(keepends=True)
    line_starts: list[int] = []
    offset = 0
    for line in lines:
        line_starts.append(offset)
        offset += len(line)

    matches: list[tuple[int, int, int]] = []
    for line_index, line in enumerate(lines):
        parsed = parse_heading_line(line)
        if not parsed:
            continue
        level, title = parsed
        if title != requested_title:
            continue
        if requested_level is not None and level != requested_level:
            continue
        end_line_index = len(lines)
        for next_index in range(line_index + 1, len(lines)):
            next_heading = parse_heading_line(lines[next_index])
            if next_heading and next_heading[0] <= level:
                end_line_index = next_index
                break
        start_offset = line_starts[line_index]
        end_offset = offset if end_line_index == len(lines) else line_starts[end_line_index]
        matches.append((start_offset, end_offset, level))

    if not matches:
        raise SystemExit(f"title selection not found: {selection}")
    if len(matches) != 1:
        raise SystemExit(f"title selection is not unique: {selection}")
    start_offset, end_offset, _level = matches[0]
    return start_offset, end_offset


def splice_text(base: str, start: int, end: int, replacement: str) -> str:
    return base[:start] + replacement + base[end:]


def join_with_spacing(prefix: str, middle: str, suffix: str) -> str:
    pieces: list[str] = []
    if prefix:
        pieces.append(prefix.rstrip("\n"))
    if middle:
        pieces.append(middle.strip("\n"))
    if suffix:
        pieces.append(suffix.lstrip("\n"))
    return "\n\n".join(piece for piece in pieces if piece).strip("\n") + "\n"


def compute_updated_markdown(
    *,
    current_markdown: str,
    mode: str,
    markdown: str | None,
    selection_with_ellipsis: str | None,
    selection_by_title: str | None,
) -> tuple[str, dict[str, object]]:
    details: dict[str, object] = {"mode": mode}
    normalized_markdown = markdown if markdown is not None else ""

    if mode == "overwrite":
        return normalized_markdown, details

    if mode == "append":
        result = join_with_spacing(current_markdown, normalized_markdown, "")
        return result, details

    if selection_by_title:
        start, end = resolve_selection_by_title(current_markdown, selection_by_title)
        details["selection_mode"] = "title"
        details["selection"] = selection_by_title
    elif selection_with_ellipsis:
        allow_multiple = mode == "replace_all"
        matches, selection_mode = resolve_selection_with_ellipsis(
            current_markdown,
            selection_with_ellipsis,
            allow_multiple=allow_multiple,
        )
        details["selection_mode"] = selection_mode
        details["selection"] = selection_with_ellipsis
        if mode == "replace_all":
            result = current_markdown
            replace_count = 0
            for match_start, match_end in reversed(matches):
                result = splice_text(result, match_start, match_end, normalized_markdown)
                replace_count += 1
            details["replace_count"] = replace_count
            return result, details
        start, end = matches[0]
    else:
        raise SystemExit("selection is required for this mode")

    selected = current_markdown[start:end]
    details["selected_preview"] = selected[:160]

    if mode == "replace_range":
        return splice_text(current_markdown, start, end, normalized_markdown), details
    if mode == "insert_before":
        replacement = join_with_spacing("", normalized_markdown, selected).rstrip("\n")
        return splice_text(current_markdown, start, end, replacement), details
    if mode == "insert_after":
        replacement = join_with_spacing(selected, normalized_markdown, "").rstrip("\n")
        return splice_text(current_markdown, start, end, replacement), details
    if mode == "delete_range":
        return splice_text(current_markdown, start, end, ""), details
    raise SystemExit(f"unsupported update mode: {mode}")


def load_markdown_argument(markdown: str | None, markdown_file: str | None) -> str | None:
    if markdown is not None and markdown_file:
        raise SystemExit("provide only one of --markdown or --markdown-file")
    if markdown_file:
        return pathlib.Path(markdown_file).read_text(encoding="utf-8")
    return markdown
