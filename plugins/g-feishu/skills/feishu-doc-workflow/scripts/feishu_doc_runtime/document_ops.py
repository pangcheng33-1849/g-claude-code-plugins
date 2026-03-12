from __future__ import annotations

"""Compatibility facade for legacy document runtime imports.

This module intentionally re-exports public functions from the smaller runtime
modules so existing callers can keep importing from ``document_ops`` while the
implementation stays split by domain.
"""

from .common import extract_ref
from .comment_ops import (
    create_document_comment,
    list_document_comments,
    parse_comment_elements_argument,
)
from .doc_api import (
    clear_document_children,
    create_descendants,
    create_document,
    delete_child_range,
    extract_document_title,
    extract_raw_content,
    extract_text_elements_for_block,
    fetch_document_blocks,
    fetch_raw_content,
    get_page_block,
    list_documents,
    move_document_to_wiki,
    resolve_bearer_token,
    update_block_text_elements,
    update_document_title,
)
from .import_ops import (
    create_export_task,
    create_import_task,
    decode_import_extra,
    infer_file_extension,
    poll_async_task,
    poll_import_task,
    upload_import_source_file,
)
from .convert_ops import (
    append_content_with_strategy,
    append_converted_content,
    chunk_convert_payload,
    collect_convert_subtree,
    convert_content_to_blocks,
    normalize_convert_blocks,
    seed_created_files,
    strip_read_only_table_fields,
)
from .patch_ops import (
    append_document_with_markdown,
    apply_inline_selection_to_block_markdown,
    apply_selection_to_partial_block_range,
    build_parsed_markdown_block_context,
    build_top_level_block_markdown_context,
    count_top_level_children,
    overwrite_document_with_markdown,
    patch_document_by_ellipsis_selection,
    patch_document_by_partial_block_range,
    patch_document_section_by_title,
    patch_document_within_single_block_selection,
    resolve_block_aligned_selection_ranges,
    resolve_inline_block_selection_ranges,
    resolve_overwrite_diff_ranges,
    resolve_partial_block_selection_ranges,
    resolve_top_level_title_section,
    serialize_markdown_block_slice,
)
from .permission_ops import (
    grant_permission_member,
    remove_permission_member,
    transfer_permission_owner,
    update_permission_member,
)
from .whiteboard_ops import (
    create_whiteboard_code_seed,
    create_whiteboard_text_seed,
    seed_created_whiteboards,
)

__all__ = [
    "append_content_with_strategy",
    "append_converted_content",
    "append_document_with_markdown",
    "apply_inline_selection_to_block_markdown",
    "apply_selection_to_partial_block_range",
    "build_api_plan",
    "build_parsed_markdown_block_context",
    "build_top_level_block_markdown_context",
    "chunk_convert_payload",
    "clear_document_children",
    "collect_convert_subtree",
    "convert_content_to_blocks",
    "count_top_level_children",
    "create_descendants",
    "create_document",
    "create_document_comment",
    "create_export_task",
    "create_import_task",
    "create_whiteboard_code_seed",
    "create_whiteboard_text_seed",
    "decode_import_extra",
    "delete_child_range",
    "extract_document_title",
    "extract_raw_content",
    "extract_text_elements_for_block",
    "fetch_document_blocks",
    "fetch_raw_content",
    "get_page_block",
    "grant_permission_member",
    "infer_file_extension",
    "list_document_comments",
    "list_documents",
    "move_document_to_wiki",
    "normalize_convert_blocks",
    "overwrite_document_with_markdown",
    "parse_comment_elements_argument",
    "patch_document_by_ellipsis_selection",
    "patch_document_by_partial_block_range",
    "patch_document_section_by_title",
    "patch_document_within_single_block_selection",
    "poll_async_task",
    "poll_import_task",
    "remove_permission_member",
    "resolve_bearer_token",
    "resolve_block_aligned_selection_ranges",
    "resolve_inline_block_selection_ranges",
    "resolve_overwrite_diff_ranges",
    "resolve_partial_block_selection_ranges",
    "resolve_top_level_title_section",
    "seed_created_files",
    "seed_created_whiteboards",
    "serialize_markdown_block_slice",
    "strip_read_only_table_fields",
    "transfer_permission_owner",
    "update_block_text_elements",
    "update_document_title",
    "update_permission_member",
    "upload_import_source_file",
]


def build_api_plan(operation: str, ref: str | None, title: str | None, markdown_file: str | None, token_type: str) -> dict[str, object]:
    target = extract_ref(ref) if ref else None
    steps: list[dict[str, object]] = []
    inputs_needed: list[str] = []
    aliases: list[str] = []

    if operation in {"read", "export"}:
        if not target:
            inputs_needed.append("doc URL or token")
        else:
            steps.append({"step": "Resolve the actual document token", "details": target})
            aliases.extend(["docx_v1_document_rawContent", "docs_v1_content_get"])
            steps.append(
                {
                    "step": "Fetch document content",
                    "preferred_aliases": aliases,
                    "http_candidates": [
                        f"GET /open-apis/docx/v1/documents/{target['document_id']}/raw_content",
                        "GET /open-apis/docs/v1/content/get",
                    ],
                }
            )
    elif operation == "create":
        if not title:
            inputs_needed.append("document title")
        steps.append(
            {
                "step": "Create the target document",
                "preferred_aliases": ["docx_v1_document_create"],
                "http_candidates": ["POST /open-apis/docx/v1/documents"],
            }
        )
        if markdown_file:
            steps.append(
                {
                    "step": "优先调用 convert 把 Markdown/HTML 转成 blocks，再写入文档；convert 失败时再回退到 standalone parser",
                    "preferred_aliases": ["docx_v1_document_convert", "docx_v1_documentBlockDescendant_create"],
                    "inputs": {"markdown_file": markdown_file},
                    "http_candidates": [
                        "POST /open-apis/docx/v1/documents/blocks/convert",
                        "POST /open-apis/docx/v1/documents/:document_id/blocks/:block_id/descendant",
                    ],
                }
            )
    elif operation == "append":
        if not target:
            inputs_needed.append("document token")
        steps.append(
            {
                "step": "Append converted blocks directly to the end of the document without clearing existing top-level children",
                "preferred_aliases": [
                    "docx_v1_document_convert",
                    "docx_v1_documentBlockDescendant_create",
                ],
                "http_candidates": [
                    "POST /open-apis/docx/v1/documents/blocks/convert",
                    "POST /open-apis/docx/v1/documents/:document_id/blocks/:block_id/descendant",
                ],
            }
        )
    elif operation == "update":
        if not target:
            inputs_needed.append("document token")
        steps.append(
            {
                "step": "优先使用标题 section / selection 的局部块级 patch；overwrite 优先使用顶层 diff 覆盖；无法安全局部 patch 时显式报错而不是静默整文重建",
                "preferred_aliases": [
                    "docx_v1_documentBlock_list",
                    "docx_v1_document_convert",
                    "docx_v1_documentBlockDescendant_create",
                    "docx_v1_documentBlock_patch",
                ],
                "http_candidates": [
                    "GET /open-apis/docx/v1/documents/:document_id/blocks",
                    "POST /open-apis/docx/v1/documents/blocks/convert",
                    "DELETE /open-apis/docx/v1/documents/:document_id/blocks/:block_id/children/batch_delete",
                    "POST /open-apis/docx/v1/documents/:document_id/blocks/:block_id/descendant",
                    "PATCH /open-apis/docx/v1/documents/:document_id/blocks/:block_id",
                ],
                "warning": "standalone update-doc 会优先做局部 patch 或顶层 diff overwrite；如果 selection 无法安全局部 patch，会直接报错，避免静默整文重建。",
            }
        )
    elif operation == "import":
        steps.extend(
            [
                {
                    "step": "Upload the local source file for import",
                    "preferred_aliases": ["drive_v1_media_uploadAll"],
                    "http_candidates": ["POST /open-apis/drive/v1/medias/upload_all"],
                },
                {
                    "step": "Create an import task",
                    "preferred_aliases": ["drive_v1_importTask_create"],
                    "http_candidates": ["POST /open-apis/drive/v1/import_tasks"],
                },
                {
                    "step": "Poll the import task result until success or failure",
                    "preferred_aliases": ["drive_v1_importTask_get"],
                    "http_candidates": ["GET /open-apis/drive/v1/import_tasks/:ticket"],
                },
            ]
        )

    return {
        "operation": operation,
        "target": target,
        "required_token_type": token_type,
        "title": title,
        "markdown_file": markdown_file,
        "inputs_needed": inputs_needed,
        "steps": steps,
    }
