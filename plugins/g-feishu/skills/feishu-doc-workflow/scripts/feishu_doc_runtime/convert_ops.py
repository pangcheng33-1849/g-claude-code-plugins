from __future__ import annotations

"""Convert-driven write path and post-convert asset replacement helpers."""

import json
import pathlib

from .asset_ops import (
    load_attachment_source,
    load_image_source,
    upload_docx_file,
    upload_docx_image,
)
from .common import dedupe_strings, http_json, raise_for_lark_failure
from .doc_api import create_descendants
from .markdown_ops import (
    CALLOUT_START_MARKER,
    FILE_MARKER,
    GRID_MARKER,
    WHITEBOARD_MARKER,
    extract_markdown_image_sources,
    markdown_contains_images,
    parse_markdown_to_descendants,
)
from .whiteboard_ops import seed_created_whiteboards


def normalize_convert_blocks(data: dict[str, object]) -> tuple[list[str], dict[str, dict[str, object]]]:
    first_level = data.get("first_level_block_ids")
    if not isinstance(first_level, list) or not all(isinstance(item, str) for item in first_level):
        raise SystemExit(f"convert response missing first_level_block_ids: {data}")
    raw_blocks = data.get("blocks")
    block_map: dict[str, dict[str, object]] = {}
    if isinstance(raw_blocks, dict):
        for key, value in raw_blocks.items():
            if not isinstance(value, dict):
                continue
            normalized = json.loads(json.dumps(value, ensure_ascii=True))
            if "block_id" not in normalized:
                normalized["block_id"] = key
            block_id = normalized.get("block_id")
            if isinstance(block_id, str):
                block_map[block_id] = normalized
    elif isinstance(raw_blocks, list):
        for value in raw_blocks:
            if not isinstance(value, dict):
                continue
            normalized = json.loads(json.dumps(value, ensure_ascii=True))
            block_id = normalized.get("block_id")
            if isinstance(block_id, str):
                block_map[block_id] = normalized
    if not block_map:
        raise SystemExit(f"convert response missing blocks: {data}")
    return [item for item in first_level if item in block_map], block_map


def strip_read_only_table_fields(block: dict[str, object]) -> None:
    table = block.get("table")
    if isinstance(table, dict):
        property_node = table.get("property")
        if isinstance(property_node, dict):
            property_node.pop("merge_info", None)


def collect_convert_subtree(block_map: dict[str, dict[str, object]], root_id: str) -> list[dict[str, object]]:
    descendants: list[dict[str, object]] = []
    seen: set[str] = set()

    def walk(block_id: str) -> None:
        if block_id in seen:
            return
        block = block_map.get(block_id)
        if not isinstance(block, dict):
            return
        seen.add(block_id)
        normalized = json.loads(json.dumps(block, ensure_ascii=True))
        strip_read_only_table_fields(normalized)
        descendants.append(normalized)
        children = normalized.get("children")
        if isinstance(children, list):
            for child_id in children:
                if isinstance(child_id, str):
                    walk(child_id)

    walk(root_id)
    return descendants


def chunk_convert_payload(
    first_level_ids: list[str],
    block_map: dict[str, dict[str, object]],
    *,
    max_blocks_per_request: int = 1000,
) -> list[tuple[list[str], list[dict[str, object]]]]:
    groups: list[tuple[list[str], list[dict[str, object]]]] = []
    current_children: list[str] = []
    current_descendants: list[dict[str, object]] = []
    current_count = 0
    for root_id in first_level_ids:
        subtree = collect_convert_subtree(block_map, root_id)
        subtree_count = len(subtree)
        if subtree_count > max_blocks_per_request:
            raise SystemExit(
                f"convert subtree too large to create in one request: root={root_id} blocks={subtree_count}, limit={max_blocks_per_request}"
            )
        if current_descendants and current_count + subtree_count > max_blocks_per_request:
            groups.append((current_children, current_descendants))
            current_children = []
            current_descendants = []
            current_count = 0
        current_children.append(root_id)
        current_descendants.extend(subtree)
        current_count += subtree_count
    if current_descendants:
        groups.append((current_children, current_descendants))
    return groups


def convert_content_to_blocks(content: str, content_type: str, bearer_token: str) -> dict[str, object]:
    status, payload, text = http_json(
        "https://open.feishu.cn/open-apis/docx/v1/documents/blocks/convert",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps({"content_type": content_type, "content": content}, ensure_ascii=True).encode("utf-8"),
    )
    raise_for_lark_failure("convert content", status, payload, text)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SystemExit(f"convert response missing data: {payload}")
    return data


def seed_created_files(
    descendants: list[dict[str, object]],
    create_result: dict[str, object],
    document_id: str,
    bearer_token: str,
    source_base_dir: pathlib.Path | None,
) -> list[dict[str, object]]:
    temp_seed_map: dict[str, dict[str, object]] = {}
    for block in descendants:
        block_id = block.get("block_id")
        source = block.get("_g_feishu_file_source")
        title = block.get("_g_feishu_file_title")
        if isinstance(block_id, str) and isinstance(source, str) and source.strip():
            temp_seed_map[block_id] = {
                "source": source.strip(),
                "title": str(title or "").strip(),
            }
    if not temp_seed_map:
        return []

    temp_to_real: dict[str, str] = {}
    relations = create_result.get("block_id_relations")
    if isinstance(relations, list):
        for relation in relations:
            if not isinstance(relation, dict):
                continue
            temp_id = relation.get("temporary_block_id")
            real_id = relation.get("block_id")
            if isinstance(temp_id, str) and isinstance(real_id, str):
                temp_to_real[temp_id] = real_id

    results: list[dict[str, object]] = []
    for temp_id, payload in temp_seed_map.items():
        real_id = temp_to_real.get(temp_id)
        if not real_id:
            results.append({"temporary_block_id": temp_id, "status": "skipped", "reason": "missing_block_relation"})
            continue
        try:
            file_bytes, file_name, content_type = load_attachment_source(str(payload["source"]), source_base_dir)
            upload_result = upload_docx_file(
                document_id,
                real_id,
                file_bytes,
                str(payload.get("title") or file_name or pathlib.Path(str(payload["source"])).name),
                content_type,
                bearer_token,
            )
            results.append(
                {
                    "temporary_block_id": temp_id,
                    "block_id": real_id,
                    "status": "uploaded",
                    "source": payload["source"],
                    "file_name": file_name,
                    **upload_result,
                }
            )
        except SystemExit as exc:
            results.append(
                {
                    "temporary_block_id": temp_id,
                    "block_id": real_id,
                    "status": "failed",
                    "source": payload["source"],
                    "error": str(exc),
                }
            )
    return results


def append_converted_content(
    document_id: str,
    content: str,
    bearer_token: str,
    *,
    content_type: str = "markdown",
    index: int | None = None,
    source_base_dir: pathlib.Path | None = None,
) -> dict[str, object]:
    convert_data = convert_content_to_blocks(content, content_type, bearer_token)
    first_level_ids, block_map = normalize_convert_blocks(convert_data)
    groups = chunk_convert_payload(first_level_ids, block_map)
    create_results: list[dict[str, object]] = []
    created_children = 0
    created_blocks = 0
    current_index = index
    image_temp_ids: list[str] = []
    for children_id, descendants in groups:
        image_temp_ids.extend(
            str(block["block_id"])
            for block in descendants
            if block.get("block_type") == 27 and isinstance(block.get("block_id"), str)
        )
        create_results.append(
            create_descendants(
                document_id,
                document_id,
                children_id,
                descendants,
                bearer_token,
                index=current_index,
            )
        )
        created_children += len(children_id)
        created_blocks += len(descendants)
        if current_index is not None:
            current_index += len(children_id)
    warnings: list[str] = []
    image_upload_results: list[dict[str, object]] = []
    image_failures: list[dict[str, object]] = []
    if content_type in {"markdown", "html"} and markdown_contains_images(content):
        image_sources = extract_markdown_image_sources(content)
        relation_map: dict[str, str] = {}
        for create_result in create_results:
            relations = create_result.get("block_id_relations")
            if not isinstance(relations, list):
                continue
            for relation in relations:
                if not isinstance(relation, dict):
                    continue
                temp_id = relation.get("temporary_block_id")
                real_id = relation.get("block_id")
                if isinstance(temp_id, str) and isinstance(real_id, str):
                    relation_map[temp_id] = real_id
        if len(image_sources) != len(image_temp_ids):
            failure = {
                "source": None,
                "temporary_block_id": None,
                "block_id": None,
                "stage": "image_count_mismatch",
                "reason": f"内容里的图片数量与 convert 产出的 image block 数量不一致: sources={len(image_sources)}, blocks={len(image_temp_ids)}",
                "next_step": "检查 Markdown / HTML 里的图片写法，确认 convert 是否为每张图都创建了 image block；必要时减少复杂嵌套或拆分文档重试。",
            }
            warnings.append(f"{failure['reason']}。未匹配到的图片需要人工检查。")
            image_failures.append(failure)
        for source, temp_id in zip(image_sources, image_temp_ids):
            real_block_id = relation_map.get(temp_id)
            if not real_block_id:
                failure = {
                    "source": source,
                    "temporary_block_id": temp_id,
                    "block_id": None,
                    "stage": "image_block_mapping",
                    "reason": "图片块映射缺失，无法将 convert 产出的临时 image block 对应到真实 block_id",
                    "next_step": "优先检查文档写入结果中的 block_id_relations；如果 convert 产出的图片块和原始图片数量不一致，建议简化图片输入或拆分写入。",
                }
                warnings.append(f"图片块映射缺失，无法补图: source={source}, temp_block_id={temp_id}")
                image_failures.append(failure)
                continue
            try:
                image_bytes, file_name, content_type_hint = load_image_source(source, source_base_dir)
            except SystemExit as exc:
                failure = {
                    "source": source,
                    "temporary_block_id": temp_id,
                    "block_id": real_block_id,
                    "stage": "image_source_load",
                    "reason": str(exc),
                    "next_step": "检查图片源是否存在且当前环境可访问；本地文件请确认路径正确，远程 URL 请确认可直连访问，必要时改用本地文件或 data URL。",
                }
                warnings.append(f"图片补传失败: source={source}, block_id={real_block_id}, error={exc}")
                image_failures.append(failure)
                continue
            try:
                upload_result = upload_docx_image(
                    document_id,
                    real_block_id,
                    image_bytes,
                    file_name,
                    content_type_hint,
                    bearer_token,
                )
                image_upload_results.append(
                    {
                        "source": source,
                        "temporary_block_id": temp_id,
                        "block_id": real_block_id,
                        **upload_result,
                    }
                )
            except SystemExit as exc:
                failure = {
                    "source": source,
                    "temporary_block_id": temp_id,
                    "block_id": real_block_id,
                    "stage": "replace_image",
                    "reason": str(exc),
                    "next_step": "确认当前身份具备 docs:document.media:upload 和文档写权限；如果 upload 成功但 replace_image 失败，建议先读取文档确认 block 是否存在，再用更简单的图片源重试。",
                }
                warnings.append(f"图片补传失败: source={source}, block_id={real_block_id}, error={exc}")
                image_failures.append(failure)
    return {
        "strategy": "convert",
        "convert_first_level_block_ids": first_level_ids,
        "create_results": create_results,
        "created_children": created_children,
        "created_blocks": created_blocks,
        "warnings": warnings,
        "image_upload_results": image_upload_results,
        "image_failures": image_failures,
    }


def append_content_with_strategy(
    document_id: str,
    content: str,
    bearer_token: str,
    *,
    content_type: str = "markdown",
    index: int | None = None,
    source_base_dir: pathlib.Path | None = None,
) -> dict[str, object]:
    if not content.strip():
        return {
            "strategy": "empty",
            "created_children": 0,
            "created_blocks": 0,
            "warnings": [],
        }
    if FILE_MARKER in content:
        raise SystemExit(
            "standalone 当前不支持把 <file .../> 直接写成飞书原生附件块。"
            " 如果你的目标是把现有文件整体放进飞书文档，请优先改用 import-doc；"
            " 如果只是读取现有文档里的附件，fetch-content --include-media 已支持下载与摘要。"
        )
    prefer_parser = content_type == "markdown" and (
        CALLOUT_START_MARKER in content or GRID_MARKER in content or WHITEBOARD_MARKER in content or FILE_MARKER in content
    )
    try:
        if prefer_parser:
            raise SystemExit("检测到原生 callout/grid/whiteboard 标记，优先使用 standalone parser 创建飞书原生块。")
        return append_converted_content(
            document_id,
            content,
            bearer_token,
            content_type=content_type,
            index=index,
            source_base_dir=source_base_dir,
        )
    except SystemExit as exc:
        if content_type != "markdown":
            raise
        children_id, descendants, parser_warnings = parse_markdown_to_descendants(content)
        created_data: dict[str, object] | None = None
        whiteboard_seed_results: list[dict[str, object]] = []
        file_seed_results: list[dict[str, object]] = []
        if children_id and descendants:
            created_data = create_descendants(document_id, document_id, children_id, descendants, bearer_token, index=index)
            whiteboard_seed_results = seed_created_whiteboards(descendants, created_data, bearer_token)
            file_seed_results = seed_created_files(descendants, created_data, document_id, bearer_token, source_base_dir)
            if whiteboard_seed_results:
                created_data["whiteboard_seed_results"] = whiteboard_seed_results
            if file_seed_results:
                created_data["file_seed_results"] = file_seed_results
        return {
            "strategy": "parser_fallback",
            "created_children": len(children_id),
            "created_blocks": len(descendants),
            "parser_warnings": parser_warnings,
            "convert_failure": str(exc),
            "create_results": [created_data] if created_data else [],
            "whiteboard_seed_results": whiteboard_seed_results,
            "file_seed_results": file_seed_results if created_data else [],
            "warnings": dedupe_strings([f"convert 失败，已回退到 standalone parser: {exc}", *parser_warnings]),
        }
