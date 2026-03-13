from __future__ import annotations

"""Convert Feishu block trees back into markdown-like text."""

from .common import CODE_LANGUAGE_MAP


def extract_text_from_elements(elements: object) -> str:
    if not isinstance(elements, list):
        return ""
    parts: list[str] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        text_run = element.get("text_run")
        if isinstance(text_run, dict):
            content = text_run.get("content")
            if isinstance(content, str):
                parts.append(content)
    return "".join(parts)


def block_to_markdown(block: dict[str, object], block_by_id: dict[str, dict[str, object]] | None = None) -> str:
    block_type = block.get("block_type")
    if block_type == 2:
        text = extract_text_from_elements(block.get("text", {}).get("elements"))
        return text.strip("\n")
    if block_type in {3, 4, 5, 6, 7, 8, 9, 10, 11}:
        level = int(block_type) - 2
        key = f"heading{level}"
        text = extract_text_from_elements(block.get(key, {}).get("elements"))
        return f"{'#' * min(level, 6)} {text}".rstrip()
    if block_type == 12:
        text = extract_text_from_elements(block.get("bullet", {}).get("elements"))
        return f"- {text}".rstrip()
    if block_type == 13:
        text = extract_text_from_elements(block.get("ordered", {}).get("elements"))
        return f"1. {text}".rstrip()
    if block_type == 14:
        code = block.get("code", {})
        text = extract_text_from_elements(code.get("elements"))
        language_id = None
        style = code.get("style")
        if isinstance(style, dict):
            language_id = style.get("language")
        language_label = ""
        for name, mapped in CODE_LANGUAGE_MAP.items():
            if mapped == language_id and len(name) > len(language_label):
                language_label = name
        return f"```{language_label}\n{text}\n```".strip()
    if block_type == 15:
        text = extract_text_from_elements(block.get("quote", {}).get("elements"))
        return "\n".join(f"> {line}" if line else ">" for line in text.splitlines() or [""])
    if block_type == 17:
        todo = block.get("todo", {})
        text = extract_text_from_elements(todo.get("elements"))
        done = False
        style = todo.get("style")
        if isinstance(style, dict):
            done = bool(style.get("done"))
        return f"- [{'x' if done else ' '}] {text}".rstrip()
    if block_type == 19:
        child_markdown: list[str] = []
        if isinstance(block_by_id, dict):
            for child_id in block.get("children", []):
                if isinstance(child_id, str) and child_id in block_by_id:
                    rendered = block_to_markdown(block_by_id[child_id], block_by_id).strip("\n")
                    if rendered:
                        child_markdown.append(rendered)
        body = "\n\n".join(child_markdown).strip()
        return f"<callout>\n{body}\n</callout>" if body else "<callout />"
    if block_type == 24:
        columns: list[str] = []
        if isinstance(block_by_id, dict):
            for child_id in block.get("children", []):
                if not isinstance(child_id, str):
                    continue
                child_block = block_by_id.get(child_id)
                if not isinstance(child_block, dict) or child_block.get("block_type") != 25:
                    continue
                column_parts: list[str] = []
                for grandchild_id in child_block.get("children", []):
                    if isinstance(grandchild_id, str) and grandchild_id in block_by_id:
                        rendered = block_to_markdown(block_by_id[grandchild_id], block_by_id).strip("\n")
                        if rendered:
                            column_parts.append(rendered)
                column_body = "\n\n".join(column_parts).strip()
                columns.append(f"<column>\n{column_body}\n</column>" if column_body else "<column />")
        body = "\n".join(columns).strip()
        return f"<grid>\n{body}\n</grid>" if body else "<grid />"
    if block_type == 31:
        if not isinstance(block_by_id, dict):
            return ""
        table = block.get("table", {})
        property_node = table.get("property", {}) if isinstance(table, dict) else {}
        column_size = property_node.get("column_size") if isinstance(property_node, dict) else None
        if not isinstance(column_size, int) or column_size <= 0:
            column_size = len(block.get("children", [])) if isinstance(block.get("children"), list) else 0
        if column_size <= 0:
            return ""
        cells: list[str] = []
        for cell_id in block.get("children", []):
            if not isinstance(cell_id, str):
                continue
            cell_block = block_by_id.get(cell_id)
            if not isinstance(cell_block, dict):
                cells.append("")
                continue
            cell_parts: list[str] = []
            for child_id in cell_block.get("children", []):
                if isinstance(child_id, str) and child_id in block_by_id:
                    rendered = block_to_markdown(block_by_id[child_id], block_by_id).strip("\n")
                    if rendered:
                        cell_parts.append(rendered)
            cells.append(" ".join(cell_parts).strip())
        rows = [cells[i : i + column_size] for i in range(0, len(cells), column_size)]
        if not rows:
            return ""
        header = rows[0]
        separator = ["---"] * len(header)
        body_rows = rows[1:]
        rendered_rows = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(separator) + " |",
        ]
        for row in body_rows:
            padded = row + [""] * max(0, len(header) - len(row))
            rendered_rows.append("| " + " | ".join(padded[: len(header)]) + " |")
        return "\n".join(rendered_rows)
    if block_type == 23:
        file_node = block.get("file", {})
        view_type = 2
        token = ""
        if isinstance(file_node, dict):
            raw_view_type = file_node.get("view_type")
            if isinstance(raw_view_type, int):
                view_type = raw_view_type
            raw_token = file_node.get("file_token") or file_node.get("token")
            if isinstance(raw_token, str):
                token = raw_token
        title = str(block.get("_g_feishu_file_title") or "").strip()
        attrs: list[str] = [f'view-type="{view_type}"']
        if title:
            attrs.append(f'title="{title}"')
        if token:
            attrs.append(f'token="{token}"')
        suffix = (" " + " ".join(attrs)) if attrs else ""
        return f"<file{suffix}/>"
    if block_type == 43:
        board = block.get("board", {})
        align_value = None
        width = None
        height = None
        token = None
        if isinstance(board, dict):
            align_map = {1: "left", 2: "center", 3: "right"}
            raw_align = board.get("align")
            if isinstance(raw_align, int):
                align_value = align_map.get(raw_align)
            raw_width = board.get("width")
            if isinstance(raw_width, int):
                width = raw_width
            raw_height = board.get("height")
            if isinstance(raw_height, int):
                height = raw_height
            raw_token = board.get("token")
            if isinstance(raw_token, str) and raw_token:
                token = raw_token
        attrs: list[str] = []
        if token:
            attrs.append(f'token="{token}"')
        if align_value:
            attrs.append(f'align="{align_value}"')
        if width:
            attrs.append(f'width="{width}"')
        if height:
            attrs.append(f'height="{height}"')
        suffix = (" " + " ".join(attrs)) if attrs else ""
        return f"<whiteboard{suffix}/>"
    if block_type == 22:
        return "---"
    return extract_text_from_elements(block.get("text", {}).get("elements"))


def blocks_to_markdown(blocks: list[dict[str, object]], document_id: str) -> str:
    page_block = None
    block_by_id: dict[str, dict[str, object]] = {}
    for block in blocks:
        block_id = block.get("block_id")
        if isinstance(block_id, str):
            block_by_id[block_id] = block
        if block_id == document_id and block.get("block_type") == 1:
            page_block = block
    if not isinstance(page_block, dict):
        return ""
    children = page_block.get("children")
    ordered_children: list[dict[str, object]] = []
    if isinstance(children, list):
        for child_id in children:
            if isinstance(child_id, str) and child_id in block_by_id:
                ordered_children.append(block_by_id[child_id])
    parts = [block_to_markdown(block, block_by_id).strip("\n") for block in ordered_children]
    return "\n\n".join(part for part in parts if part).strip() + ("\n" if parts else "")
