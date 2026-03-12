from __future__ import annotations

"""Markdown cleanup and Feishu-flavored extension preprocessing."""

import json
import re


CALLOUT_START_MARKER = "@@FEISHU_CALLOUT@@"
CALLOUT_END_MARKER = "@@END_FEISHU_CALLOUT@@"
GRID_MARKER = "@@FEISHU_GRID@@"
LARK_TABLE_MARKER = "@@FEISHU_LARK_TABLE@@"
WHITEBOARD_MARKER = "@@FEISHU_WHITEBOARD@@"
FILE_MARKER = "@@FEISHU_FILE@@"


def normalize_markdown(text: str, title: str | None) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    lines = normalized.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    if title and lines:
        first = lines[0].strip()
        if first == f"# {title}".strip():
            lines.pop(0)
            while lines and not lines[0].strip():
                lines.pop(0)
    cleaned: list[str] = []
    blank_run = 0
    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            blank_run += 1
            if blank_run <= 2:
                cleaned.append("")
            continue
        blank_run = 0
        cleaned.append(stripped)
    return "\n".join(cleaned).strip() + "\n"


def _build_quote_block(prefix: str, body: str) -> str:
    lines = [line.rstrip() for line in body.strip().splitlines() if line.strip()]
    if not lines:
        return f"> {prefix}".rstrip()
    quoted = [f"> {prefix}".rstrip()]
    quoted.extend(f"> {line}" for line in lines)
    return "\n".join(quoted)


def _parse_html_attrs(raw_attrs: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for key, value in re.findall(r'([A-Za-z0-9_-]+)\s*=\s*"([^"]*)"', raw_attrs):
        attrs[key.lower()] = value
    return attrs


def _parse_loose_attrs(raw_attrs: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for key, quoted_double, quoted_single, bare in re.findall(
        r'([A-Za-z0-9_-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))',
        raw_attrs,
    ):
        value = quoted_double or quoted_single or bare
        attrs[key.lower()] = value
    return attrs


def preprocess_lark_flavored_markdown(markdown: str) -> tuple[str, list[str]]:
    transformed = markdown
    warnings: list[str] = []

    def replace_image_tag(match: re.Match[str]) -> str:
        attrs = _parse_html_attrs(match.group(1) or "")
        source = (
            attrs.get("src")
            or attrs.get("url")
            or attrs.get("path")
            or attrs.get("file")
            or ""
        ).strip()
        if not source:
            warnings.append("检测到 <image>/<img>，但缺少 src/url/path 属性，已忽略。")
            return ""
        alt = (attrs.get("alt") or attrs.get("title") or "").strip()
        warnings.append("检测到 <image>/<img>。standalone 当前会把它转换为图片输入协议，并在写入飞书后补图。")
        return f"![{alt}]({source})"

    transformed = re.sub(
        r"<(?:image|img)\b([^>]*)/?>",
        replace_image_tag,
        transformed,
        flags=re.IGNORECASE,
    )

    def file_marker(attrs: dict[str, str]) -> str:
        source = (
            attrs.get("src")
            or attrs.get("url")
            or attrs.get("path")
            or attrs.get("file")
            or ""
        ).strip()
        title = (attrs.get("title") or attrs.get("name") or attrs.get("label") or "").strip()
        view_type_raw = (attrs.get("view-type") or attrs.get("view_type") or "2").strip()
        try:
            view_type = int(view_type_raw)
        except ValueError:
            view_type = 2
        return f"{FILE_MARKER}{json.dumps({'source': source, 'title': title, 'view_type': view_type}, ensure_ascii=True)}"

    def replace_file_tag(match: re.Match[str]) -> str:
        attrs = _parse_html_attrs(match.group(1) or "")
        source = (
            attrs.get("src")
            or attrs.get("url")
            or attrs.get("path")
            or attrs.get("file")
            or ""
        ).strip()
        if not source:
            warnings.append("检测到 <file>，但缺少 src/url/path/file 属性，已忽略。")
            return ""
        warnings.append("检测到 <file>。standalone 当前会尝试创建原生附件块，并在写入飞书后补传文件。")
        return file_marker(attrs)

    transformed = re.sub(
        r"<file\b([^>]*)/?>",
        replace_file_tag,
        transformed,
        flags=re.IGNORECASE,
    )

    def callout_marker(attrs: dict[str, str], body: str) -> str:
        payload = {
            "type": (attrs.get("type") or "info").strip().lower(),
            "title": (attrs.get("title") or "").strip(),
            "emoji": (attrs.get("emoji") or attrs.get("emoji_id") or "").strip(),
        }
        return f"{CALLOUT_START_MARKER}{json.dumps(payload, ensure_ascii=True)}\n{body.strip()}\n{CALLOUT_END_MARKER}"

    def replace_html_callout(match: re.Match[str]) -> str:
        attrs = _parse_html_attrs(match.group(1) or "")
        body = match.group(2) or ""
        warnings.append("检测到 <callout>。standalone 当前会尝试创建原生高亮块；复杂嵌套内容会保守写成单个子文本块。")
        return callout_marker(attrs, body)

    transformed = re.sub(
        r"<callout\b([^>]*)>(.*?)</callout>",
        replace_html_callout,
        transformed,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def replace_fenced_callout(match: re.Match[str]) -> str:
        header = (match.group(1) or "").strip()
        body = match.group(2) or ""
        attrs: dict[str, str] = {}
        type_match = re.search(r"type\s*=\s*([A-Za-z0-9_-]+)", header)
        title_match = re.search(r'title\s*=\s*"([^"]+)"', header)
        emoji_match = re.search(r'emoji(?:_id)?\s*=\s*"([^"]+)"', header)
        if type_match:
            attrs["type"] = type_match.group(1)
        if title_match:
            attrs["title"] = title_match.group(1)
        if emoji_match:
            attrs["emoji"] = emoji_match.group(1)
        warnings.append("检测到 :::callout。standalone 当前会尝试创建原生高亮块；复杂嵌套内容会保守写成单个子文本块。")
        return callout_marker(attrs, body)

    transformed = re.sub(
        r":::callout([^\n]*)\n(.*?)\n:::",
        replace_fenced_callout,
        transformed,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def replace_grid(match: re.Match[str]) -> str:
        body = match.group(1) or ""
        columns = re.findall(r"<column\b([^>]*)>(.*?)</column>", body, flags=re.IGNORECASE | re.DOTALL)
        if not columns:
            warnings.append("检测到 <grid>，但未识别到可解析的 <column>。内容会按普通文本写入。")
            return body
        normalized_columns: list[dict[str, object]] = []
        for index, (raw_attrs, raw_content) in enumerate(columns, start=1):
            attrs = _parse_html_attrs(raw_attrs or "")
            title = (attrs.get("title") or "").strip()
            width_raw = (attrs.get("width") or attrs.get("width_ratio") or "").strip()
            width_ratio: int | None = None
            if width_raw:
                try:
                    width_ratio = int(width_raw.rstrip("%"))
                except ValueError:
                    width_ratio = None
            normalized_columns.append(
                {
                    "title": title,
                    "content": raw_content.strip(),
                    "width_ratio": width_ratio,
                    "index": index,
                }
            )
        warnings.append("检测到 <grid>/<column>。standalone 当前会尝试创建原生分栏块；复杂嵌套内容会保守写成列内单个文本块。")
        return f"{GRID_MARKER}{json.dumps({'columns': normalized_columns}, ensure_ascii=True)}"

    transformed = re.sub(
        r"<grid\b[^>]*>(.*?)</grid>",
        replace_grid,
        transformed,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def lark_table_marker(attrs: dict[str, str], rows: list[list[str]]) -> str:
        def as_bool(value: str | None) -> bool:
            return (value or "").strip().lower() in {"1", "true", "yes", "on"}

        payload = {
            "header_row": as_bool(attrs.get("header-row") or attrs.get("header_row")),
            "header_column": as_bool(attrs.get("header-column") or attrs.get("header_column")),
            "rows": rows,
        }
        return f"{LARK_TABLE_MARKER}{json.dumps(payload, ensure_ascii=True)}"

    def replace_lark_table(match: re.Match[str]) -> str:
        attrs = _parse_html_attrs(match.group(1) or "")
        body = match.group(2) or ""
        row_matches = re.findall(r"<row\b[^>]*>(.*?)</row>", body, flags=re.IGNORECASE | re.DOTALL)
        rows: list[list[str]] = []
        for row_html in row_matches:
            cell_matches = re.findall(r"<cell\b[^>]*>(.*?)</cell>", row_html, flags=re.IGNORECASE | re.DOTALL)
            normalized_cells = [re.sub(r"</?[^>]+>", "", cell).strip() for cell in cell_matches]
            if normalized_cells:
                rows.append(normalized_cells)
        if not rows:
            warnings.append("检测到 <lark-table>，但未识别到有效的 <row>/<cell>。内容会按普通文本写入。")
            return body
        column_size = len(rows[0])
        if any(len(row) != column_size for row in rows):
            warnings.append("检测到 <lark-table> 的行列数不一致。内容会按普通文本写入。")
            return body
        warnings.append("检测到 <lark-table>。standalone 当前会尝试创建飞书原生表格块；复杂特性如 merge_info 仍未支持。")
        return lark_table_marker(attrs, rows)

    transformed = re.sub(
        r"<lark-table\b([^>]*)>(.*?)</lark-table>",
        replace_lark_table,
        transformed,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def whiteboard_marker(attrs: dict[str, str], body: str) -> str:
        normalized: dict[str, object] = {
            "align": (attrs.get("align") or "center").strip().lower(),
            "width": (attrs.get("width") or "800").strip(),
            "height": (attrs.get("height") or "480").strip(),
            "seed_text": body.strip(),
        }
        return f"{WHITEBOARD_MARKER}{json.dumps(normalized, ensure_ascii=True)}"

    def whiteboard_code_marker(kind: str, attrs: dict[str, str], body: str) -> str:
        normalized: dict[str, object] = {
            "align": (attrs.get("align") or "center").strip().lower(),
            "width": (attrs.get("width") or "900").strip(),
            "height": (attrs.get("height") or "520").strip(),
            "seed_kind": kind,
            "diagram_code": body.strip(),
        }
        for source_key, target_key in (
            ("syntax-type", "syntax_type"),
            ("syntax_type", "syntax_type"),
            ("style-type", "style_type"),
            ("style_type", "style_type"),
            ("diagram-type", "diagram_type"),
            ("diagram_type", "diagram_type"),
        ):
            raw_value = (attrs.get(source_key) or "").strip()
            if not raw_value:
                continue
            try:
                normalized[target_key] = int(raw_value)
            except ValueError:
                continue
        if "syntax_type" not in normalized:
            normalized["syntax_type"] = 1 if kind == "plantuml" else 2
        return f"{WHITEBOARD_MARKER}{json.dumps(normalized, ensure_ascii=True)}"

    def replace_html_whiteboard(match: re.Match[str]) -> str:
        attrs = _parse_html_attrs(match.group(1) or "")
        body = match.group(2) or ""
        if attrs.get("token"):
            warnings.append("检测到 <whiteboard token=\"...\">。token 属性是只读的，standalone 创建时会忽略它。")
        warnings.append("检测到 <whiteboard>。standalone 当前会尝试创建原生白板块；标签体里的纯文本会作为初始 text_shape 写入白板。")
        return whiteboard_marker(attrs, body)

    transformed = re.sub(
        r"<whiteboard\b([^>]*)>(.*?)</whiteboard>",
        replace_html_whiteboard,
        transformed,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def replace_self_closing_whiteboard(match: re.Match[str]) -> str:
        attrs = _parse_html_attrs(match.group(1) or "")
        if attrs.get("token"):
            warnings.append("检测到 <whiteboard token=\"...\" />。token 属性是只读的，standalone 创建时会忽略它。")
        warnings.append("检测到 <whiteboard />。standalone 当前会尝试创建原生白板块。")
        return whiteboard_marker(attrs, "")

    transformed = re.sub(
        r"<whiteboard\b([^>]*)/>",
        replace_self_closing_whiteboard,
        transformed,
        flags=re.IGNORECASE,
    )

    def replace_fenced_plantuml(match: re.Match[str]) -> str:
        raw_attrs = (match.group(1) or "").strip()
        body = match.group(2) or ""
        attrs = _parse_loose_attrs(raw_attrs)
        warnings.append("检测到 ```plantuml```。standalone 当前会尝试创建原生白板，并调用 PlantUML 节点接口写入图形。")
        return whiteboard_code_marker("plantuml", attrs, body)

    transformed = re.sub(
        r"```plantuml([^\n]*)\n(.*?)\n```",
        replace_fenced_plantuml,
        transformed,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def replace_fenced_mermaid(match: re.Match[str]) -> str:
        raw_attrs = (match.group(1) or "").strip()
        body = match.group(2) or ""
        attrs = _parse_loose_attrs(raw_attrs)
        warnings.append("检测到 ```mermaid```。standalone 当前会尝试创建原生白板，并调用解析画板语法接口写入 Mermaid 图形。")
        return whiteboard_code_marker("mermaid", attrs, body)

    transformed = re.sub(
        r"```mermaid([^\n]*)\n(.*?)\n```",
        replace_fenced_mermaid,
        transformed,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return transformed, list(dict.fromkeys(warnings))
