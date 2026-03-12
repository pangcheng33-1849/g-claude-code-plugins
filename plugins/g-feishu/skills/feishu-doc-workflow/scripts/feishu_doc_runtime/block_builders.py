from __future__ import annotations

"""Primitive Feishu block builders used by markdown parsing and rewrite flows."""

import uuid

from .common import CODE_LANGUAGE_MAP


def make_text_elements(content: str) -> list[dict[str, object]]:
    return [{"text_run": {"content": content}}]


def make_block_id(prefix: str, counter: int) -> str:
    return f"{prefix}_{counter}_{uuid.uuid4().hex[:8]}"


def make_text_block(block_id: str, content: str) -> dict[str, object]:
    return {
        "block_id": block_id,
        "block_type": 2,
        "text": {"elements": make_text_elements(content)},
    }


def make_heading_block(block_id: str, level: int, content: str) -> dict[str, object]:
    block_type = min(max(level, 1), 9) + 2
    return {
        "block_id": block_id,
        "block_type": block_type,
        f"heading{min(max(level, 1), 9)}": {"elements": make_text_elements(content)},
    }


def make_bullet_block(block_id: str, content: str) -> dict[str, object]:
    return {
        "block_id": block_id,
        "block_type": 12,
        "bullet": {"elements": make_text_elements(content)},
    }


def make_ordered_block(block_id: str, content: str) -> dict[str, object]:
    return {
        "block_id": block_id,
        "block_type": 13,
        "ordered": {"elements": make_text_elements(content)},
    }


def make_code_block(block_id: str, content: str, language: str | None) -> dict[str, object]:
    language_id = CODE_LANGUAGE_MAP.get((language or "").strip().lower(), 1)
    return {
        "block_id": block_id,
        "block_type": 14,
        "code": {
            "elements": make_text_elements(content),
            "style": {
                "language": language_id,
                "wrap": True,
            },
        },
    }


def make_quote_block(block_id: str, content: str) -> dict[str, object]:
    return {
        "block_id": block_id,
        "block_type": 15,
        "quote": {"elements": make_text_elements(content)},
    }


def make_callout_block(block_id: str, child_id: str, callout_type: str, emoji_id: str | None = None) -> dict[str, object]:
    style_map: dict[str, tuple[int, int, int]] = {
        "info": (5, 5, 5),
        "success": (4, 4, 4),
        "warning": (3, 3, 3),
        "danger": (1, 1, 1),
        "error": (1, 1, 1),
        "tip": (7, 7, 7),
        "note": (7, 7, 7),
    }
    background_color, border_color, text_color = style_map.get(callout_type.lower(), (7, 7, 7))
    callout: dict[str, object] = {
        "background_color": background_color,
        "border_color": border_color,
        "text_color": text_color,
    }
    if emoji_id:
        callout["emoji_id"] = emoji_id
    return {
        "block_id": block_id,
        "block_type": 19,
        "children": [child_id],
        "callout": callout,
    }


def make_grid_block(block_id: str, column_ids: list[str]) -> dict[str, object]:
    return {
        "block_id": block_id,
        "block_type": 24,
        "children": column_ids,
        "grid": {
            "column_size": len(column_ids),
        },
    }


def make_grid_column_block(block_id: str, child_ids: list[str], width_ratio: int) -> dict[str, object]:
    return {
        "block_id": block_id,
        "block_type": 25,
        "children": child_ids,
        "grid_column": {
            "width_ratio": width_ratio,
        },
    }


def make_board_block(
    block_id: str,
    *,
    align: str = "center",
    width: int = 800,
    height: int = 480,
    seed_text: str | None = None,
    plantuml_code: str | None = None,
    syntax_type: int | None = None,
    style_type: int | None = None,
    diagram_type: int | None = None,
) -> dict[str, object]:
    align_map = {
        "left": 1,
        "center": 2,
        "right": 3,
    }
    board_block: dict[str, object] = {
        "block_id": block_id,
        "block_type": 43,
        "board": {
            "align": align_map.get(align.lower(), 2),
            "width": max(320, min(width, 1920)),
            "height": max(200, min(height, 1080)),
        },
    }
    if seed_text:
        board_block["_codex_whiteboard_seed_text"] = seed_text
        board_block["_codex_whiteboard_seed_kind"] = "text"
    if plantuml_code:
        board_block["_codex_whiteboard_seed_kind"] = "plantuml"
        board_block["_codex_whiteboard_plantuml_code"] = plantuml_code
        if isinstance(syntax_type, int):
            board_block["_codex_whiteboard_plantuml_syntax_type"] = syntax_type
        if isinstance(style_type, int):
            board_block["_codex_whiteboard_plantuml_style_type"] = style_type
        if isinstance(diagram_type, int):
            board_block["_codex_whiteboard_plantuml_diagram_type"] = diagram_type
    return board_block


def make_file_block(
    block_id: str,
    *,
    source: str,
    title: str | None = None,
    view_type: int = 2,
) -> dict[str, object]:
    block: dict[str, object] = {
        "block_id": block_id,
        "block_type": 23,
        "file": {
            "view_type": 1 if view_type == 1 else 2,
        },
    }
    block["_codex_file_source"] = source
    if title:
        block["_codex_file_title"] = title
    return block


def make_todo_block(block_id: str, content: str, done: bool) -> dict[str, object]:
    return {
        "block_id": block_id,
        "block_type": 17,
        "todo": {
            "elements": make_text_elements(content),
            "style": {"done": done},
        },
    }


def make_divider_block(block_id: str) -> dict[str, object]:
    return {
        "block_id": block_id,
        "block_type": 22,
        "divider": {},
    }


def make_table_block(
    block_id: str,
    cell_ids: list[str],
    row_size: int,
    column_size: int,
    *,
    header_row: bool = False,
    header_column: bool = False,
) -> dict[str, object]:
    return {
        "block_id": block_id,
        "block_type": 31,
        "children": cell_ids,
        "table": {
            "cells": cell_ids,
            "property": {
                "row_size": row_size,
                "column_size": column_size,
                "header_row": header_row,
                "header_column": header_column,
            },
        },
    }


def make_table_cell_block(block_id: str, child_ids: list[str]) -> dict[str, object]:
    return {
        "block_id": block_id,
        "block_type": 32,
        "children": child_ids,
        "table_cell": {},
    }
