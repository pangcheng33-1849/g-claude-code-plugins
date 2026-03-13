from __future__ import annotations

"""Parse markdown text into GFeishu descendant blocks."""

import json
import re

from .block_builders import (
    make_block_id,
    make_board_block,
    make_bullet_block,
    make_callout_block,
    make_code_block,
    make_divider_block,
    make_file_block,
    make_grid_block,
    make_grid_column_block,
    make_heading_block,
    make_ordered_block,
    make_quote_block,
    make_table_block,
    make_table_cell_block,
    make_text_block,
    make_todo_block,
)
from .markdown_preprocess import (
    CALLOUT_END_MARKER,
    CALLOUT_START_MARKER,
    FILE_MARKER,
    GRID_MARKER,
    LARK_TABLE_MARKER,
    WHITEBOARD_MARKER,
    preprocess_lark_flavored_markdown,
)


def parse_markdown_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if "|" not in stripped:
        return None
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    cells = [cell.strip() for cell in stripped.split("|")]
    if len(cells) < 2:
        return None
    return cells


def is_markdown_table_separator(line: str, expected_columns: int) -> bool:
    cells = parse_markdown_table_row(line)
    if not cells or len(cells) != expected_columns:
        return False
    for cell in cells:
        compact = cell.replace(":", "").replace("-", "").replace(" ", "")
        if compact:
            return False
        if "-" not in cell:
            return False
    return True


def parse_markdown_to_descendants(markdown: str) -> tuple[list[str], list[dict[str, object]], list[str]]:
    preprocessed, preprocess_warnings = preprocess_lark_flavored_markdown(markdown)
    normalized = preprocessed.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not normalized.strip():
        return [], [], preprocess_warnings

    lines = normalized.split("\n")
    children_id: list[str] = []
    descendants: list[dict[str, object]] = []
    warnings: list[str] = list(preprocess_warnings)
    paragraph_buffer: list[str] = []
    counter = 0

    if "<callout" in normalized or "<grid" in normalized or "<lark-table" in normalized or "<whiteboard" in normalized:
        warnings.append("检测到飞书扩展标签。standalone create/update 会按当前已支持的原生块能力尽量转换，未支持的标签会保守降级或保留。")

    def next_id(prefix: str) -> str:
        nonlocal counter
        counter += 1
        return make_block_id(prefix, counter)

    def append_block(block: dict[str, object]) -> None:
        children_id.append(str(block["block_id"]))
        descendants.append(block)

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if not paragraph_buffer:
            return
        append_block(make_text_block(next_id("text"), "\n".join(paragraph_buffer)))
        paragraph_buffer = []

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        if stripped.startswith(CALLOUT_START_MARKER):
            flush_paragraph()
            raw_payload = stripped[len(CALLOUT_START_MARKER) :]
            try:
                payload = json.loads(raw_payload) if raw_payload else {}
            except json.JSONDecodeError:
                payload = {}
                warnings.append("callout 标记解析失败，已降级为普通段落。")
            index += 1
            body_lines: list[str] = []
            while index < len(lines) and lines[index].strip() != CALLOUT_END_MARKER:
                body_lines.append(lines[index].rstrip())
                index += 1
            if index < len(lines) and lines[index].strip() == CALLOUT_END_MARKER:
                index += 1
            title = str(payload.get("title") or "").strip()
            body_text = "\n".join(body_lines).strip()
            callout_parts = [part for part in [title, body_text] if part]
            if not callout_parts:
                continue
            callout_id = next_id("callout")
            text_id = next_id("callout_text")
            append_block(
                make_callout_block(
                    callout_id,
                    text_id,
                    str(payload.get("type") or "info"),
                    str(payload.get("emoji") or "").strip() or None,
                )
            )
            descendants.append(make_text_block(text_id, "\n".join(callout_parts)))
            continue

        if stripped.startswith(GRID_MARKER):
            flush_paragraph()
            raw_payload = stripped[len(GRID_MARKER) :]
            try:
                payload = json.loads(raw_payload) if raw_payload else {}
            except json.JSONDecodeError:
                payload = {}
                warnings.append("grid 标记解析失败，已降级为普通段落。")
            columns = payload.get("columns")
            if not isinstance(columns, list) or not columns:
                warnings.append("grid 标记缺少列定义，已跳过。")
                index += 1
                continue
            normalized_columns: list[dict[str, object]] = [item for item in columns if isinstance(item, dict)]
            if not normalized_columns:
                warnings.append("grid 标记列定义为空，已跳过。")
                index += 1
                continue
            grid_id = next_id("grid")
            column_ids: list[str] = []
            column_descendants: list[dict[str, object]] = []
            default_width = max(1, round(100 / max(1, len(normalized_columns))))
            remaining = 100
            for column_index, column_payload in enumerate(normalized_columns, start=1):
                column_id = next_id("grid_column")
                text_id = next_id("grid_text")
                title = str(column_payload.get("title") or "").strip()
                content = str(column_payload.get("content") or "").strip()
                body_parts = [part for part in [title, content] if part]
                if not body_parts:
                    body_parts = [f"分栏 {column_index}"]
                if isinstance(column_payload.get("width_ratio"), int):
                    width_ratio = max(1, int(column_payload["width_ratio"]))
                elif column_index == len(normalized_columns):
                    width_ratio = max(1, remaining)
                else:
                    width_ratio = default_width
                remaining = max(1, remaining - width_ratio)
                column_ids.append(column_id)
                column_descendants.append(make_grid_column_block(column_id, [text_id], width_ratio))
                column_descendants.append(make_text_block(text_id, "\n".join(body_parts)))
            append_block(make_grid_block(grid_id, column_ids))
            descendants.extend(column_descendants)
            index += 1
            continue

        if stripped.startswith(LARK_TABLE_MARKER):
            flush_paragraph()
            raw_payload = stripped[len(LARK_TABLE_MARKER) :]
            try:
                payload = json.loads(raw_payload) if raw_payload else {}
            except json.JSONDecodeError:
                payload = {}
                warnings.append("lark-table 标记解析失败，已跳过。")
            rows = payload.get("rows")
            if not isinstance(rows, list) or not rows:
                warnings.append("lark-table 标记缺少有效 rows，已跳过。")
                index += 1
                continue
            normalized_rows: list[list[str]] = []
            column_size: int | None = None
            valid = True
            for row in rows:
                if not isinstance(row, list) or not row:
                    valid = False
                    break
                normalized_row = [str(cell).strip() for cell in row]
                if column_size is None:
                    column_size = len(normalized_row)
                elif len(normalized_row) != column_size:
                    valid = False
                    break
                normalized_rows.append(normalized_row)
            if not valid or not normalized_rows or not column_size:
                warnings.append("lark-table 行列定义无效，已跳过。")
                index += 1
                continue
            table_id = next_id("lark_table")
            cell_ids: list[str] = []
            cell_descendants: list[dict[str, object]] = []
            for row in normalized_rows:
                for cell_text in row:
                    cell_id = next_id("table_cell")
                    text_id = next_id("table_text")
                    cell_ids.append(cell_id)
                    cell_descendants.append(make_table_cell_block(cell_id, [text_id]))
                    cell_descendants.append(make_text_block(text_id, cell_text))
            append_block(
                make_table_block(
                    table_id,
                    cell_ids,
                    len(normalized_rows),
                    column_size,
                    header_row=bool(payload.get("header_row")),
                    header_column=bool(payload.get("header_column")),
                )
            )
            descendants.extend(cell_descendants)
            index += 1
            continue

        if stripped.startswith(WHITEBOARD_MARKER):
            flush_paragraph()
            raw_payload = stripped[len(WHITEBOARD_MARKER) :]
            try:
                payload = json.loads(raw_payload) if raw_payload else {}
            except json.JSONDecodeError:
                payload = {}
                warnings.append("whiteboard 标记解析失败，已跳过。")
            align = str(payload.get("align") or "center").strip().lower()
            try:
                width = int(str(payload.get("width") or "800").strip())
            except ValueError:
                width = 800
            try:
                height = int(str(payload.get("height") or "480").strip())
            except ValueError:
                height = 480
            seed_text = str(payload.get("seed_text") or "").strip()
            diagram_code = str(payload.get("diagram_code") or payload.get("plantuml_code") or "").strip()
            seed_kind = str(payload.get("seed_kind") or ("plantuml" if diagram_code else "text")).strip().lower()
            syntax_type_raw = payload.get("syntax_type")
            style_type_raw = payload.get("style_type")
            diagram_type_raw = payload.get("diagram_type")
            append_block(
                make_board_block(
                    next_id("whiteboard"),
                    align=align,
                    width=width,
                    height=height,
                    seed_text=seed_text or None,
                    plantuml_code=diagram_code or None,
                    syntax_type=syntax_type_raw if isinstance(syntax_type_raw, int) else 1,
                    style_type=style_type_raw if isinstance(style_type_raw, int) else None,
                    diagram_type=diagram_type_raw if isinstance(diagram_type_raw, int) else None,
                )
            )
            if seed_kind == "mermaid" and descendants:
                descendants[-1]["_g_feishu_whiteboard_seed_kind"] = "mermaid"
            index += 1
            continue

        if stripped.startswith(FILE_MARKER):
            flush_paragraph()
            raw_payload = stripped[len(FILE_MARKER) :]
            try:
                payload = json.loads(raw_payload) if raw_payload else {}
            except json.JSONDecodeError:
                payload = {}
                warnings.append("file 标记解析失败，已跳过。")
            source = str(payload.get("source") or "").strip()
            if not source:
                warnings.append("file 标记缺少 source，已跳过。")
                index += 1
                continue
            title = str(payload.get("title") or "").strip()
            raw_view_type = payload.get("view_type")
            view_type = int(raw_view_type) if isinstance(raw_view_type, int) else 2
            append_block(make_file_block(next_id("file"), source=source, title=title or None, view_type=view_type))
            index += 1
            continue

        table_header = parse_markdown_table_row(line)
        if table_header and index + 1 < len(lines) and is_markdown_table_separator(lines[index + 1], len(table_header)):
            flush_paragraph()
            rows: list[list[str]] = [table_header]
            index += 2
            while index < len(lines):
                maybe_row = parse_markdown_table_row(lines[index])
                if not maybe_row or len(maybe_row) != len(table_header):
                    break
                rows.append(maybe_row)
                index += 1
            table_id = next_id("table")
            cell_ids: list[str] = []
            cell_descendants: list[dict[str, object]] = []
            for row in rows:
                for cell_text in row:
                    cell_id = next_id("table_cell")
                    text_id = next_id("table_text")
                    cell_ids.append(cell_id)
                    cell_descendants.append(make_table_cell_block(cell_id, [text_id]))
                    cell_descendants.append(make_text_block(text_id, cell_text))
            append_block(make_table_block(table_id, cell_ids, len(rows), len(table_header)))
            descendants.extend(cell_descendants)
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            append_block(make_heading_block(next_id("heading"), level, heading_match.group(2).strip()))
            index += 1
            continue

        html_heading_match = re.match(r"^<h([7-9])>(.*?)</h\1>$", stripped, re.IGNORECASE)
        if html_heading_match:
            flush_paragraph()
            append_block(make_heading_block(next_id("heading"), int(html_heading_match.group(1)), html_heading_match.group(2).strip()))
            index += 1
            continue

        if stripped in {"---", "***", "___"}:
            flush_paragraph()
            append_block(make_divider_block(next_id("divider")))
            index += 1
            continue

        todo_match = re.match(r"^[-*+]\s+\[([ xX])\]\s+(.*)$", stripped)
        if todo_match:
            flush_paragraph()
            append_block(make_todo_block(next_id("todo"), todo_match.group(2).strip(), todo_match.group(1).lower() == "x"))
            index += 1
            continue

        bullet_match = re.match(r"^[-*+]\s+(.*)$", stripped)
        if bullet_match:
            flush_paragraph()
            append_block(make_bullet_block(next_id("bullet"), bullet_match.group(1).strip()))
            index += 1
            continue

        ordered_match = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ordered_match:
            flush_paragraph()
            append_block(make_ordered_block(next_id("ordered"), ordered_match.group(1).strip()))
            index += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            quote_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_lines.append(re.sub(r"^>\s?", "", lines[index].strip()))
                index += 1
            append_block(make_quote_block(next_id("quote"), "\n".join(quote_lines)))
            continue

        code_fence = re.match(r"^```([A-Za-z0-9_+-]*)\s*$", stripped)
        if code_fence:
            flush_paragraph()
            language = code_fence.group(1) or None
            index += 1
            code_lines: list[str] = []
            while index < len(lines) and not re.match(r"^```\s*$", lines[index].strip()):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines) and re.match(r"^```\s*$", lines[index].strip()):
                index += 1
            append_block(make_code_block(next_id("code"), "\n".join(code_lines), language))
            continue

        paragraph_buffer.append(line.rstrip())
        index += 1

    flush_paragraph()
    return children_id, descendants, warnings
