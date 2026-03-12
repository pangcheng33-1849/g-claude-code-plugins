from __future__ import annotations

"""Overwrite/diff and patch helpers for update-doc."""

import pathlib

from .common import dedupe_strings
from .convert_ops import append_content_with_strategy
from .doc_api import (
    clear_document_children,
    delete_child_range,
    extract_text_elements_for_block,
    fetch_document_blocks,
    update_block_text_elements,
)
from .markdown_ops import (
    CALLOUT_START_MARKER,
    FILE_MARKER,
    GRID_MARKER,
    WHITEBOARD_MARKER,
    block_to_markdown,
    extract_text_from_elements,
    join_with_spacing,
    parse_heading_line,
    parse_markdown_to_descendants,
    resolve_selection_with_ellipsis,
    splice_text,
)


def build_parsed_markdown_block_context(markdown: str) -> tuple[str, list[dict[str, object]], list[str]]:
    children_id, descendants, warnings = parse_markdown_to_descendants(markdown)
    block_by_id: dict[str, dict[str, object]] = {}
    for block in descendants:
        block_id = block.get("block_id")
        if isinstance(block_id, str):
            block_by_id[block_id] = block
    ordered: list[dict[str, object]] = []
    parts: list[str] = []
    for block_index, block_id in enumerate(children_id):
        block = block_by_id.get(block_id)
        if not isinstance(block, dict):
            continue
        # Container blocks such as tables need the full block map to serialize
        # correctly; serializing descendants independently will flatten them.
        markdown_text = block_to_markdown(block, block_by_id).strip("\n")
        if not markdown_text:
            continue
        parts.append(markdown_text)
        ordered.append(
            {
                "block_index": block_index,
                "block_type": block.get("block_type"),
                "markdown": markdown_text,
            }
        )
    serialized = "\n\n".join(parts).strip() + ("\n" if parts else "")
    return serialized, ordered, warnings


def count_top_level_children(blocks: list[dict[str, object]], document_id: str) -> int:
    for block in blocks:
        if block.get("block_id") == document_id and block.get("block_type") == 1:
            children = block.get("children")
            return len(children) if isinstance(children, list) else 0
    raise SystemExit(f"page block missing for document: {document_id}")


def resolve_overwrite_diff_ranges(
    current_blocks: list[dict[str, object]],
    new_blocks: list[dict[str, object]],
) -> tuple[int, int, int, int]:
    prefix = 0
    while (
        prefix < len(current_blocks)
        and prefix < len(new_blocks)
        and current_blocks[prefix].get("block_type") == new_blocks[prefix].get("block_type")
        and current_blocks[prefix].get("markdown") == new_blocks[prefix].get("markdown")
    ):
        prefix += 1

    current_suffix = len(current_blocks)
    new_suffix = len(new_blocks)
    while (
        current_suffix > prefix
        and new_suffix > prefix
        and current_blocks[current_suffix - 1].get("block_type") == new_blocks[new_suffix - 1].get("block_type")
        and current_blocks[current_suffix - 1].get("markdown") == new_blocks[new_suffix - 1].get("markdown")
    ):
        current_suffix -= 1
        new_suffix -= 1
    return prefix, current_suffix, prefix, new_suffix


def serialize_markdown_block_slice(block_items: list[dict[str, object]]) -> str:
    markdown_parts = [str(item.get("markdown", "")).strip("\n") for item in block_items if str(item.get("markdown", "")).strip("\n")]
    return "\n\n".join(markdown_parts).strip() + ("\n" if markdown_parts else "")


def overwrite_document_with_markdown(
    document_id: str,
    markdown: str,
    bearer_token: str,
    *,
    content_type: str = "markdown",
    source_base_dir: pathlib.Path | None = None,
) -> dict[str, object]:
    if content_type != "markdown":
        deleted_children = clear_document_children(document_id, bearer_token)
        append_result = append_content_with_strategy(
            document_id,
            markdown,
            bearer_token,
            content_type=content_type,
            source_base_dir=source_base_dir,
        )
        result = {"deleted_children": deleted_children, **append_result}
        parser_warnings = append_result.get("parser_warnings")
        if isinstance(parser_warnings, list):
            result["parser_warnings"] = parser_warnings
        return result

    if CALLOUT_START_MARKER in markdown or GRID_MARKER in markdown or WHITEBOARD_MARKER in markdown or FILE_MARKER in markdown:
        current_blocks = fetch_document_blocks(document_id, bearer_token)
        current_top_level_child_count = count_top_level_children(current_blocks, document_id)
        deleted_children = clear_document_children(document_id, bearer_token)
        append_result = append_content_with_strategy(
            document_id,
            markdown,
            bearer_token,
            content_type="markdown",
            source_base_dir=source_base_dir,
        )
        result = {
            "strategy": "native_callout_parser_overwrite",
            "changed": True,
            "deleted_children": deleted_children,
            "preserved_prefix_blocks": 0,
            "preserved_suffix_blocks": 0,
            "unserializable_top_level_children": max(0, current_top_level_child_count),
            **append_result,
        }
        parser_warnings = append_result.get("parser_warnings")
        if isinstance(parser_warnings, list):
            result["parser_warnings"] = parser_warnings
        warnings = append_result.get("warnings")
        if isinstance(warnings, list):
            result["warnings"] = dedupe_strings(
                [
                    *[item for item in warnings if isinstance(item, str)],
                    "检测到原生 callout/grid/whiteboard 标记；当前 overwrite 显式走 parser 全量重写，以确保创建飞书原生块。",
                ]
            )
        else:
            result["warnings"] = [
                "检测到原生 callout/grid/whiteboard 标记；当前 overwrite 显式走 parser 全量重写，以确保创建飞书原生块。"
            ]
        return result

    current_blocks = fetch_document_blocks(document_id, bearer_token)
    current_top_level_child_count = count_top_level_children(current_blocks, document_id)
    current_markdown, current_ordered = build_top_level_block_markdown_context(current_blocks, document_id)
    new_markdown, new_ordered, parser_warnings = build_parsed_markdown_block_context(markdown)

    if current_markdown == new_markdown:
        result: dict[str, object] = {
            "strategy": "top_level_diff_overwrite",
            "changed": False,
            "deleted_children": 0,
            "created_children": 0,
            "created_blocks": 0,
            "preserved_prefix_blocks": len(current_ordered),
            "preserved_suffix_blocks": 0,
            "unserializable_top_level_children": max(0, current_top_level_child_count - len(current_ordered)),
        }
        if parser_warnings:
            result["parser_warnings"] = parser_warnings
        return result

    current_replace_start, current_replace_end, new_replace_start, new_replace_end = resolve_overwrite_diff_ranges(
        current_ordered,
        new_ordered,
    )

    deleted_children = 0
    delete_result: dict[str, object] = {}
    if current_replace_end > current_replace_start:
        delete_result = delete_child_range(
            document_id,
            document_id,
            current_replace_start,
            current_replace_end,
            bearer_token,
        )
        deleted_children = current_replace_end - current_replace_start

    new_middle_markdown = serialize_markdown_block_slice(new_ordered[new_replace_start:new_replace_end])
    append_result: dict[str, object] = {
        "strategy": "empty",
        "created_children": 0,
        "created_blocks": 0,
        "warnings": [],
    }
    if new_middle_markdown.strip():
        append_result = append_content_with_strategy(
            document_id,
            new_middle_markdown,
            bearer_token,
            content_type="markdown",
            index=current_replace_start,
            source_base_dir=source_base_dir,
        )

    result = {
        "changed": True,
        "delete_result": delete_result,
        "deleted_children": deleted_children,
        "replace_range": {
            "current_start_index": current_replace_start,
            "current_end_index": current_replace_end,
            "new_start_index": new_replace_start,
            "new_end_index": new_replace_end,
        },
        "preserved_prefix_blocks": current_replace_start,
        "preserved_suffix_blocks": len(current_ordered) - current_replace_end,
        "unserializable_top_level_children": max(0, current_top_level_child_count - len(current_ordered)),
        **append_result,
    }
    result["strategy"] = "top_level_diff_overwrite"
    if isinstance(append_result.get("strategy"), str):
        result["write_strategy"] = str(append_result["strategy"])
    if parser_warnings:
        result["parser_warnings"] = parser_warnings
    return result


def append_document_with_markdown(
    document_id: str,
    markdown: str,
    bearer_token: str,
    *,
    content_type: str = "markdown",
    source_base_dir: pathlib.Path | None = None,
) -> dict[str, object]:
    append_result = append_content_with_strategy(
        document_id,
        markdown,
        bearer_token,
        content_type=content_type,
        source_base_dir=source_base_dir,
    )
    parser_warnings = append_result.get("parser_warnings")
    result = {"appended": True, **append_result}
    if isinstance(parser_warnings, list):
        result["parser_warnings"] = parser_warnings
    return result


def resolve_top_level_title_section(
    blocks: list[dict[str, object]],
    document_id: str,
    selection_by_title: str,
) -> dict[str, object]:
    page_block = None
    block_by_id: dict[str, dict[str, object]] = {}
    for block in blocks:
        block_id = block.get("block_id")
        if isinstance(block_id, str):
            block_by_id[block_id] = block
        if block_id == document_id and block.get("block_type") == 1:
            page_block = block
    if not isinstance(page_block, dict):
        raise SystemExit(f"page block missing for document: {document_id}")

    children = page_block.get("children")
    if not isinstance(children, list):
        raise SystemExit(f"page block children missing for document: {document_id}")

    requested = selection_by_title.strip()
    requested_heading = parse_heading_line(requested)
    requested_level = requested_heading[0] if requested_heading else None
    requested_title = requested_heading[1] if requested_heading else requested.lstrip("#").strip()

    ordered_children: list[tuple[int, str, dict[str, object]]] = []
    for index, child_id in enumerate(children):
        if not isinstance(child_id, str):
            continue
        child_block = block_by_id.get(child_id)
        if isinstance(child_block, dict):
            ordered_children.append((index, child_id, child_block))

    matches: list[dict[str, object]] = []
    for ordered_index, child_id, child_block in ordered_children:
        block_type = child_block.get("block_type")
        if not isinstance(block_type, int) or block_type < 3 or block_type > 11:
            continue
        level = block_type - 2
        key = f"heading{level}"
        heading_text = extract_text_from_elements(child_block.get(key, {}).get("elements"))
        if heading_text != requested_title:
            continue
        if requested_level is not None and level != requested_level:
            continue
        end_index = len(children)
        for next_index, _next_child_id, next_child_block in ordered_children:
            if next_index <= ordered_index:
                continue
            next_type = next_child_block.get("block_type")
            if isinstance(next_type, int) and 3 <= next_type <= 11 and (next_type - 2) <= level:
                end_index = next_index
                break
        matches.append(
            {
                "title": heading_text,
                "level": level,
                "start_index": ordered_index,
                "end_index": end_index,
                "child_block_id": child_id,
            }
        )

    if not matches:
        raise SystemExit(f"title selection not found in top-level blocks: {selection_by_title}")
    if len(matches) != 1:
        raise SystemExit(f"title selection is not unique in top-level blocks: {selection_by_title}")
    return matches[0]


def patch_document_section_by_title(
    document_id: str,
    blocks: list[dict[str, object]],
    selection_by_title: str,
    mode: str,
    markdown: str | None,
    bearer_token: str,
    *,
    source_base_dir: pathlib.Path | None = None,
) -> dict[str, object]:
    section = resolve_top_level_title_section(blocks, document_id, selection_by_title)
    start_index = int(section["start_index"])
    end_index = int(section["end_index"])
    result: dict[str, object] = {
        "strategy": "block_patch_by_title",
        "selection_mode": "title",
        "selection": selection_by_title,
        "section": section,
    }

    if mode == "insert_before":
        append_result = append_content_with_strategy(
            document_id,
            markdown or "",
            bearer_token,
            content_type="markdown",
            index=start_index,
            source_base_dir=source_base_dir,
        )
        result["operation"] = "insert_before"
        result["append_result"] = append_result
        return result

    if mode == "insert_after":
        append_result = append_content_with_strategy(
            document_id,
            markdown or "",
            bearer_token,
            content_type="markdown",
            index=end_index,
            source_base_dir=source_base_dir,
        )
        result["operation"] = "insert_after"
        result["append_result"] = append_result
        return result

    if mode == "delete_range":
        delete_result = delete_child_range(document_id, document_id, start_index, end_index, bearer_token)
        result["operation"] = "delete_range"
        result["delete_result"] = delete_result
        result["deleted_children"] = end_index - start_index
        return result

    if mode == "replace_range":
        delete_result = delete_child_range(document_id, document_id, start_index, end_index, bearer_token)
        append_result = append_content_with_strategy(
            document_id,
            markdown or "",
            bearer_token,
            content_type="markdown",
            index=start_index,
            source_base_dir=source_base_dir,
        )
        result["operation"] = "replace_range"
        result["delete_result"] = delete_result
        result["deleted_children"] = end_index - start_index
        result["append_result"] = append_result
        return result

    raise SystemExit(f"mode does not support title-based block patch: {mode}")


def build_top_level_block_markdown_context(
    blocks: list[dict[str, object]],
    document_id: str,
) -> tuple[str, list[dict[str, object]]]:
    page_block = None
    block_by_id: dict[str, dict[str, object]] = {}
    for block in blocks:
        block_id = block.get("block_id")
        if isinstance(block_id, str):
            block_by_id[block_id] = block
        if block_id == document_id and block.get("block_type") == 1:
            page_block = block
    if not isinstance(page_block, dict):
        raise SystemExit(f"page block missing for document: {document_id}")
    children = page_block.get("children")
    if not isinstance(children, list):
        children = []

    ordered: list[dict[str, object]] = []
    parts: list[str] = []
    for child_index, child_id in enumerate(children):
        if not isinstance(child_id, str):
            continue
        block = block_by_id.get(child_id)
        if not isinstance(block, dict):
            continue
        markdown = block_to_markdown(block).strip("\n")
        if not markdown:
            continue
        parts.append(markdown)
        ordered.append(
            {
                "child_index": child_index,
                "block_id": child_id,
                "block_type": block.get("block_type"),
                "markdown": markdown,
            }
        )

    current_markdown = "\n\n".join(parts).strip() + ("\n" if parts else "")
    offset = 0
    for index, item in enumerate(ordered):
        markdown = str(item["markdown"])
        start_offset = offset
        end_offset = start_offset + len(markdown)
        trailing_end_offset = end_offset + (2 if index < len(ordered) - 1 else 1)
        item["start_offset"] = start_offset
        item["end_offset"] = end_offset
        item["trailing_end_offset"] = trailing_end_offset
        offset = trailing_end_offset
    return current_markdown, ordered


def resolve_block_aligned_selection_ranges(
    blocks: list[dict[str, object]],
    document_id: str,
    selection_with_ellipsis: str,
    *,
    allow_multiple: bool,
) -> dict[str, object] | None:
    current_markdown, ordered = build_top_level_block_markdown_context(blocks, document_id)
    matches, selection_mode = resolve_selection_with_ellipsis(
        current_markdown,
        selection_with_ellipsis,
        allow_multiple=allow_multiple,
    )
    resolved_ranges: list[dict[str, object]] = []
    for match_start, match_end in matches:
        start_item = next((item for item in ordered if item.get("start_offset") == match_start), None)
        end_item = next(
            (
                item
                for item in ordered
                if match_end in {item.get("end_offset"), item.get("trailing_end_offset")}
            ),
            None,
        )
        if not isinstance(start_item, dict) or not isinstance(end_item, dict):
            return None
        start_index = int(start_item["child_index"])
        end_index = int(end_item["child_index"]) + 1
        if start_index >= end_index:
            return None
        resolved_ranges.append(
            {
                "start_index": start_index,
                "end_index": end_index,
                "match_start": match_start,
                "match_end": match_end,
            }
        )
    return {
        "selection_mode": selection_mode,
        "current_markdown": current_markdown,
        "ranges": resolved_ranges,
    }


def patch_document_by_ellipsis_selection(
    document_id: str,
    blocks: list[dict[str, object]],
    selection_with_ellipsis: str,
    mode: str,
    markdown: str | None,
    bearer_token: str,
    *,
    source_base_dir: pathlib.Path | None = None,
) -> dict[str, object] | None:
    alignment = resolve_block_aligned_selection_ranges(
        blocks,
        document_id,
        selection_with_ellipsis,
        allow_multiple=(mode == "replace_all"),
    )
    if alignment is None:
        return None

    ranges = list(alignment["ranges"])
    result: dict[str, object] = {
        "strategy": "block_patch_by_selection",
        "selection_mode": alignment["selection_mode"],
        "selection": selection_with_ellipsis,
        "ranges": ranges,
    }

    if mode in {"insert_before", "insert_after", "delete_range", "replace_range"}:
        target = ranges[0]
        start_index = int(target["start_index"])
        end_index = int(target["end_index"])
        if mode == "insert_before":
            append_result = append_content_with_strategy(
                document_id,
                markdown or "",
                bearer_token,
                content_type="markdown",
                index=start_index,
                source_base_dir=source_base_dir,
            )
            result["operation"] = "insert_before"
            result["append_result"] = append_result
            return result
        if mode == "insert_after":
            append_result = append_content_with_strategy(
                document_id,
                markdown or "",
                bearer_token,
                content_type="markdown",
                index=end_index,
                source_base_dir=source_base_dir,
            )
            result["operation"] = "insert_after"
            result["append_result"] = append_result
            return result
        if mode == "delete_range":
            delete_result = delete_child_range(document_id, document_id, start_index, end_index, bearer_token)
            result["operation"] = "delete_range"
            result["delete_result"] = delete_result
            result["deleted_children"] = end_index - start_index
            return result
        if mode == "replace_range":
            delete_result = delete_child_range(document_id, document_id, start_index, end_index, bearer_token)
            append_result = append_content_with_strategy(
                document_id,
                markdown or "",
                bearer_token,
                content_type="markdown",
                index=start_index,
                source_base_dir=source_base_dir,
            )
            result["operation"] = "replace_range"
            result["delete_result"] = delete_result
            result["deleted_children"] = end_index - start_index
            result["append_result"] = append_result
            return result

    if mode == "replace_all":
        operations: list[dict[str, object]] = []
        for target in reversed(ranges):
            start_index = int(target["start_index"])
            end_index = int(target["end_index"])
            delete_result = delete_child_range(document_id, document_id, start_index, end_index, bearer_token)
            append_result = append_content_with_strategy(
                document_id,
                markdown or "",
                bearer_token,
                content_type="markdown",
                index=start_index,
                source_base_dir=source_base_dir,
            )
            operations.append(
                {
                    "start_index": start_index,
                    "end_index": end_index,
                    "deleted_children": end_index - start_index,
                    "delete_result": delete_result,
                    "append_result": append_result,
                }
            )
        result["operation"] = "replace_all"
        result["replace_count"] = len(ranges)
        result["operations"] = list(reversed(operations))
        return result

    raise SystemExit(f"mode does not support ellipsis-based block patch: {mode}")


def resolve_inline_block_selection_ranges(
    blocks: list[dict[str, object]],
    document_id: str,
    selection_with_ellipsis: str,
    *,
    allow_multiple: bool,
) -> dict[str, object] | None:
    current_markdown, ordered = build_top_level_block_markdown_context(blocks, document_id)
    matches, selection_mode = resolve_selection_with_ellipsis(
        current_markdown,
        selection_with_ellipsis,
        allow_multiple=allow_multiple,
    )
    grouped: dict[int, dict[str, object]] = {}
    for match_start, match_end in matches:
        block_item = next(
            (
                item
                for item in ordered
                if int(item["start_offset"]) <= match_start <= match_end <= int(item["end_offset"])
            ),
            None,
        )
        if not isinstance(block_item, dict):
            return None
        child_index = int(block_item["child_index"])
        entry = grouped.setdefault(
            child_index,
            {
                "child_index": child_index,
                "block_id": str(block_item["block_id"]),
                "block_type": block_item.get("block_type"),
                "markdown": str(block_item["markdown"]),
                "matches": [],
            },
        )
        entry["matches"].append(
            {
                "match_start": match_start,
                "match_end": match_end,
                "local_start": match_start - int(block_item["start_offset"]),
                "local_end": match_end - int(block_item["start_offset"]),
            }
        )
    return {
        "selection_mode": selection_mode,
        "current_markdown": current_markdown,
        "blocks": [grouped[index] for index in sorted(grouped.keys())],
    }


def apply_inline_selection_to_block_markdown(
    *,
    block_markdown: str,
    mode: str,
    markdown: str | None,
    matches: list[dict[str, object]],
) -> tuple[str, dict[str, object]]:
    normalized_markdown = markdown if markdown is not None else ""
    details: dict[str, object] = {"mode": mode}
    if mode == "replace_all":
        result = block_markdown
        replace_count = 0
        for match in reversed(matches):
            result = splice_text(result, int(match["local_start"]), int(match["local_end"]), normalized_markdown)
            replace_count += 1
        details["replace_count"] = replace_count
        return result, details

    match = matches[0]
    start = int(match["local_start"])
    end = int(match["local_end"])
    selected = block_markdown[start:end]
    details["selected_preview"] = selected[:160]
    if mode == "replace_range":
        return splice_text(block_markdown, start, end, normalized_markdown), details
    if mode == "insert_before":
        replacement = join_with_spacing("", normalized_markdown, selected).rstrip("\n")
        return splice_text(block_markdown, start, end, replacement), details
    if mode == "insert_after":
        replacement = join_with_spacing(selected, normalized_markdown, "").rstrip("\n")
        return splice_text(block_markdown, start, end, replacement), details
    if mode == "delete_range":
        return splice_text(block_markdown, start, end, ""), details
    raise SystemExit(f"mode does not support inline block patch: {mode}")


def patch_document_within_single_block_selection(
    document_id: str,
    blocks: list[dict[str, object]],
    selection_with_ellipsis: str,
    mode: str,
    markdown: str | None,
    bearer_token: str,
    *,
    source_base_dir: pathlib.Path | None = None,
) -> dict[str, object] | None:
    inline_markdown = markdown
    if inline_markdown is not None:
        inline_markdown = inline_markdown.strip("\n")

    inline_ranges = resolve_inline_block_selection_ranges(
        blocks,
        document_id,
        selection_with_ellipsis,
        allow_multiple=(mode == "replace_all"),
    )
    if inline_ranges is None:
        return None

    block_entries = list(inline_ranges["blocks"])
    if not block_entries:
        return None

    operations: list[dict[str, object]] = []
    block_by_id = {
        str(block["block_id"]): block
        for block in blocks
        if isinstance(block, dict) and isinstance(block.get("block_id"), str)
    }
    for block_entry in reversed(block_entries):
        child_index = int(block_entry["child_index"])
        block_markdown = str(block_entry["markdown"])
        block_id = str(block_entry["block_id"])
        original_block = block_by_id.get(block_id)
        updated_markdown, block_details = apply_inline_selection_to_block_markdown(
            block_markdown=block_markdown,
            mode=mode,
            markdown=inline_markdown,
            matches=list(block_entry["matches"]),
        )
        if updated_markdown.strip() and isinstance(original_block, dict) and "\n" not in updated_markdown.strip("\n"):
            children_id, descendants, parser_warnings = parse_markdown_to_descendants(updated_markdown)
            if len(children_id) == 1 and len(descendants) == 1 and descendants[0].get("block_type") == original_block.get("block_type"):
                replacement_elements = extract_text_elements_for_block(descendants[0])
                if isinstance(replacement_elements, list):
                    try:
                        update_result = update_block_text_elements(document_id, block_id, replacement_elements, bearer_token)
                        operations.append(
                            {
                                "child_index": child_index,
                                "block_id": block_id,
                                "block_type": block_entry.get("block_type"),
                                "match_count": len(block_entry["matches"]),
                                "block_details": block_details,
                                "patch_method": "update_text_elements",
                                "update_result": update_result,
                                "parser_warnings": parser_warnings,
                            }
                        )
                        continue
                    except SystemExit:
                        pass

        delete_result = delete_child_range(document_id, document_id, child_index, child_index + 1, bearer_token)
        append_result = append_content_with_strategy(
            document_id,
            updated_markdown,
            bearer_token,
            content_type="markdown",
            index=child_index,
            source_base_dir=source_base_dir,
        )
        operations.append(
            {
                "child_index": child_index,
                "block_id": block_id,
                "block_type": block_entry.get("block_type"),
                "match_count": len(block_entry["matches"]),
                "block_details": block_details,
                "patch_method": "delete_and_recreate",
                "delete_result": delete_result,
                "append_result": append_result,
            }
        )

    result: dict[str, object] = {
        "strategy": "block_patch_within_single_block",
        "selection_mode": inline_ranges["selection_mode"],
        "selection": selection_with_ellipsis,
        "operation": mode,
        "operations": list(reversed(operations)),
        "patched_block_count": len(block_entries),
    }
    if mode == "replace_all":
        result["replace_count"] = sum(len(entry["matches"]) for entry in block_entries)
    return result


def resolve_partial_block_selection_ranges(
    blocks: list[dict[str, object]],
    document_id: str,
    selection_with_ellipsis: str,
    *,
    allow_multiple: bool,
) -> dict[str, object] | None:
    current_markdown, ordered = build_top_level_block_markdown_context(blocks, document_id)
    matches, selection_mode = resolve_selection_with_ellipsis(
        current_markdown,
        selection_with_ellipsis,
        allow_multiple=allow_multiple,
    )
    ranges: list[dict[str, object]] = []
    for match_start, match_end in matches:
        start_item = next(
            (
                item
                for item in ordered
                if int(item["start_offset"]) <= match_start < int(item["end_offset"])
            ),
            None,
        )
        end_item = next(
            (
                item
                for item in ordered
                if int(item["start_offset"]) < match_end <= int(item["end_offset"])
            ),
            None,
        )
        if not isinstance(start_item, dict) or not isinstance(end_item, dict):
            return None
        start_index = int(start_item["child_index"])
        end_index = int(end_item["child_index"])
        if start_index == end_index:
            return None
        range_start_offset = int(start_item["start_offset"])
        range_end_offset = int(end_item["end_offset"])
        range_markdown = current_markdown[range_start_offset:range_end_offset]
        ranges.append(
            {
                "start_index": start_index,
                "end_index": end_index + 1,
                "range_markdown": range_markdown,
                "local_start": match_start - range_start_offset,
                "local_end": match_end - range_start_offset,
                "range_preview": range_markdown[:240],
            }
        )
    return {
        "selection_mode": selection_mode,
        "current_markdown": current_markdown,
        "ranges": ranges,
    }


def apply_selection_to_partial_block_range(
    *,
    range_markdown: str,
    mode: str,
    markdown: str | None,
    local_start: int,
    local_end: int,
) -> tuple[str, dict[str, object]]:
    normalized_markdown = markdown if markdown is not None else ""
    selected = range_markdown[local_start:local_end]
    details: dict[str, object] = {
        "mode": mode,
        "selected_preview": selected[:160],
    }
    if mode == "replace_range":
        return splice_text(range_markdown, local_start, local_end, normalized_markdown), details
    if mode == "insert_before":
        replacement = join_with_spacing("", normalized_markdown, selected).rstrip("\n")
        return splice_text(range_markdown, local_start, local_end, replacement), details
    if mode == "insert_after":
        replacement = join_with_spacing(selected, normalized_markdown, "").rstrip("\n")
        return splice_text(range_markdown, local_start, local_end, replacement), details
    if mode == "delete_range":
        return splice_text(range_markdown, local_start, local_end, ""), details
    raise SystemExit(f"mode does not support partial block range patch: {mode}")


def patch_document_by_partial_block_range(
    document_id: str,
    blocks: list[dict[str, object]],
    selection_with_ellipsis: str,
    mode: str,
    markdown: str | None,
    bearer_token: str,
    *,
    source_base_dir: pathlib.Path | None = None,
) -> dict[str, object] | None:
    partial_ranges = resolve_partial_block_selection_ranges(
        blocks,
        document_id,
        selection_with_ellipsis,
        allow_multiple=(mode == "replace_all"),
    )
    if partial_ranges is None:
        return None
    ranges = list(partial_ranges["ranges"])
    operations: list[dict[str, object]] = []
    for partial_range in reversed(ranges):
        updated_range_markdown, range_details = apply_selection_to_partial_block_range(
            range_markdown=str(partial_range["range_markdown"]),
            mode="replace_range" if mode == "replace_all" else mode,
            markdown=markdown,
            local_start=int(partial_range["local_start"]),
            local_end=int(partial_range["local_end"]),
        )
        start_index = int(partial_range["start_index"])
        end_index = int(partial_range["end_index"])
        delete_result = delete_child_range(document_id, document_id, start_index, end_index, bearer_token)
        append_result: dict[str, object] = {}
        if updated_range_markdown.strip():
            append_result = append_content_with_strategy(
                document_id,
                updated_range_markdown,
                bearer_token,
                content_type="markdown",
                index=start_index,
                source_base_dir=source_base_dir,
            )
        operations.append(
            {
                "start_index": start_index,
                "end_index": end_index,
                "deleted_children": end_index - start_index,
                "range_details": range_details,
                "delete_result": delete_result,
                "append_result": append_result,
            }
        )
    result: dict[str, object] = {
        "strategy": "block_patch_by_partial_selection_range",
        "selection_mode": partial_ranges["selection_mode"],
        "selection": selection_with_ellipsis,
        "operation": mode,
        "operations": list(reversed(operations)),
    }
    if mode == "replace_all":
        result["replace_count"] = len(ranges)
    return result
