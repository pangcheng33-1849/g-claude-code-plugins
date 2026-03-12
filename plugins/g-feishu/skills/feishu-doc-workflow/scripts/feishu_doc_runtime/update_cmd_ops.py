from __future__ import annotations

"""Update-doc command implementation."""

import argparse
import json
import pathlib

from .command_aux_ops import (
    build_direct_write_decision,
    build_update_preservation_strategy,
    raise_with_auth_fallback_guidance,
)
from .common import build_doc_url, build_web_link_notice, extract_ref, print_json, resolve_target_for_api
from .document_ops import (
    append_document_with_markdown,
    extract_document_title,
    extract_raw_content,
    fetch_document_blocks,
    fetch_raw_content,
    overwrite_document_with_markdown,
    patch_document_by_ellipsis_selection,
    patch_document_by_partial_block_range,
    patch_document_section_by_title,
    patch_document_within_single_block_selection,
    resolve_bearer_token,
    update_document_title,
)
from .markdown_ops import (
    blocks_to_markdown,
    compute_updated_markdown,
    load_markdown_argument,
    normalize_markdown,
    preprocess_lark_flavored_markdown,
)


def cmd_update_doc(args: argparse.Namespace) -> None:
    target = extract_ref(args.ref)
    markdown_source = load_markdown_argument(args.markdown, args.markdown_file)
    source_base_dir = pathlib.Path(args.markdown_file).resolve().parent if args.markdown_file else None
    require_markdown = args.mode != "delete_range"
    if require_markdown and (markdown_source is None or not markdown_source.strip()):
        raise SystemExit(f"--markdown or --markdown-file is required for mode={args.mode}")
    selection_required = args.mode in {"replace_range", "replace_all", "insert_before", "insert_after", "delete_range"}
    if selection_required:
        has_ellipsis = bool(args.selection_with_ellipsis)
        has_title = bool(args.selection_by_title)
        if (has_ellipsis and has_title) or (not has_ellipsis and not has_title):
            raise SystemExit(
                "--selection-with-ellipsis and --selection-by-title must be mutually exclusive and one is required for this mode"
            )
    if args.mode == "replace_all" and args.selection_by_title:
        raise SystemExit("mode=replace_all currently requires --selection-with-ellipsis")

    bearer_token, auth_mode = resolve_bearer_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
    )
    try:
        resolved_target = resolve_target_for_api(target, bearer_token)
        document_id = str(resolved_target.get("resolved_document_id") or target["document_id"])
        current_blocks = fetch_document_blocks(document_id, bearer_token)
        page_block = None
        for block in current_blocks:
            if block.get("block_id") == document_id and block.get("block_type") == 1:
                page_block = block
                break
        if not isinstance(page_block, dict):
            raise SystemExit(f"page block missing for document: {document_id}")
        current_title = extract_document_title(page_block)
        normalized_markdown = (
            normalize_markdown(markdown_source or "", args.new_title or current_title) if markdown_source is not None else ""
        )
        syntax_warnings: list[str] = []
        if normalized_markdown:
            normalized_markdown, syntax_warnings = preprocess_lark_flavored_markdown(normalized_markdown)
        routing_decision = build_direct_write_decision(
            operation="append" if args.mode == "append" else "update",
            markdown_arg=args.markdown,
            markdown_file=args.markdown_file,
            content_type="markdown",
        )
        warnings: list[str] = []
        update_engine = "whole_document_rewrite"
        title_patch_modes = {"insert_before", "insert_after", "replace_range", "delete_range"}
        selection_patch_modes = title_patch_modes | {"replace_all"}

        if args.mode == "append":
            update_details = {"mode": args.mode, "patch_strategy": "append_blocks"}
            overwrite_result = append_document_with_markdown(
                document_id,
                normalized_markdown,
                bearer_token,
                content_type="markdown",
                source_base_dir=source_base_dir,
            )
            update_engine = "append_blocks"
        elif args.mode == "overwrite":
            update_details = {"mode": args.mode, "patch_strategy": "top_level_diff_overwrite"}
            overwrite_result = overwrite_document_with_markdown(
                document_id,
                normalized_markdown,
                bearer_token,
                content_type="markdown",
                source_base_dir=source_base_dir,
            )
            update_engine = "whole_document_overwrite"
            warnings.extend(
                [
                    "standalone update-doc 当前在 overwrite 模式下优先做顶层块级 diff，只替换发生变化的顶层块范围。",
                    "未变化的前后缀顶层块会被保留；被替换范围内的评论、块元数据和嵌入媒体仍可能丢失。",
                ]
            )
        elif args.selection_by_title and args.mode in title_patch_modes:
            update_details = {
                "mode": args.mode,
                "selection_mode": "title",
                "selection": args.selection_by_title,
                "patch_strategy": "block_patch_by_title",
            }
            overwrite_result = patch_document_section_by_title(
                document_id,
                current_blocks,
                args.selection_by_title,
                args.mode,
                normalized_markdown,
                bearer_token,
                source_base_dir=source_base_dir,
            )
            update_engine = "block_patch_by_title"
        elif args.selection_with_ellipsis and args.mode in selection_patch_modes:
            ellipsis_patch_result = patch_document_by_ellipsis_selection(
                document_id,
                current_blocks,
                args.selection_with_ellipsis,
                args.mode,
                normalized_markdown,
                bearer_token,
                source_base_dir=source_base_dir,
            )
            if ellipsis_patch_result is not None:
                update_details = {
                    "mode": args.mode,
                    "selection_mode": "ellipsis",
                    "selection": args.selection_with_ellipsis,
                    "patch_strategy": "block_patch_by_selection",
                }
                overwrite_result = ellipsis_patch_result
                update_engine = "block_patch_by_selection"
            else:
                inline_patch_result = patch_document_within_single_block_selection(
                    document_id,
                    current_blocks,
                    args.selection_with_ellipsis,
                    args.mode,
                    normalized_markdown,
                    bearer_token,
                    source_base_dir=source_base_dir,
                )
                if inline_patch_result is not None:
                    update_details = {
                        "mode": args.mode,
                        "selection_mode": "ellipsis",
                        "selection": args.selection_with_ellipsis,
                        "patch_strategy": "block_patch_within_single_block",
                    }
                    overwrite_result = inline_patch_result
                    update_engine = "block_patch_within_single_block"
                else:
                    partial_patch_result = None
                    if args.mode in {"replace_range", "replace_all", "insert_before", "insert_after", "delete_range"}:
                        partial_patch_result = patch_document_by_partial_block_range(
                            document_id,
                            current_blocks,
                            args.selection_with_ellipsis,
                            args.mode,
                            normalized_markdown,
                            bearer_token,
                            source_base_dir=source_base_dir,
                        )
                    if partial_patch_result is not None:
                        update_details = {
                            "mode": args.mode,
                            "selection_mode": "ellipsis",
                            "selection": args.selection_with_ellipsis,
                            "patch_strategy": "block_patch_by_partial_selection_range",
                        }
                        overwrite_result = partial_patch_result
                        update_engine = "block_patch_by_partial_selection_range"
                    else:
                        raise SystemExit(
                            "selection 已命中，但当前结构无法安全收敛为局部 patch。"
                            "为避免静默整文重建并导致评论、块元数据或嵌入媒体丢失，本次已停止执行。"
                            "请改用更精确的标题 / selection，或显式使用 --mode overwrite。"
                        )
        else:
            current_markdown = blocks_to_markdown(current_blocks, document_id)
            if not current_markdown.strip():
                current_markdown = extract_raw_content(fetch_raw_content(document_id, bearer_token))
            updated_markdown, update_details = compute_updated_markdown(
                current_markdown=current_markdown,
                mode=args.mode,
                markdown=normalized_markdown,
                selection_with_ellipsis=args.selection_with_ellipsis,
                selection_by_title=args.selection_by_title,
            )
            overwrite_result = overwrite_document_with_markdown(
                document_id,
                updated_markdown,
                bearer_token,
                content_type="markdown",
                source_base_dir=source_base_dir,
            )
            warnings.extend(
                [
                    "当前模式未命中更细粒度的局部 patch，因此会回退到 overwrite 的顶层 diff 替换。",
                    "未变化的前后缀顶层块会被保留；被替换范围内的评论、块元数据和嵌入媒体仍可能丢失。",
                ]
            )
            update_engine = "whole_document_overwrite"

        title_update_result: dict[str, object] = {}
        if args.new_title:
            title_update_result = update_document_title(document_id, args.new_title, bearer_token)
        parser_warnings = overwrite_result.get("parser_warnings")
        write_warnings = overwrite_result.get("warnings")
        if isinstance(parser_warnings, list):
            warnings.extend(item for item in parser_warnings if isinstance(item, str))
        if isinstance(write_warnings, list):
            warnings.extend(item for item in write_warnings if isinstance(item, str))
        if update_engine == "block_patch_by_title":
            warnings.append("当前块级 patch 仅覆盖 --selection-by-title 的 insert_before / insert_after / replace_range / delete_range。")
        if update_engine == "block_patch_by_selection":
            warnings.append("当前 selection-with-ellipsis 的块级 patch 仅在匹配结果对齐到顶层块边界时生效。")
        if update_engine == "block_patch_within_single_block":
            warnings.append("当前 selection-with-ellipsis 的单块 patch 会优先尝试 `update_text_elements`；如果替换后不再适合单块文本，则只重建该单个顶层块。")
        if update_engine == "block_patch_by_partial_selection_range":
            warnings.append("当前 selection-with-ellipsis 的局部范围 patch 覆盖 replace_range / replace_all / insert_before / insert_after / delete_range，并且会替换命中区间所在的顶层块范围。")
        decision_warnings = routing_decision.get("warnings")
        if isinstance(decision_warnings, list):
            warnings.extend(item for item in decision_warnings if isinstance(item, str))
        warnings.extend(syntax_warnings)

        result = {
            "success": True,
            "auth_mode": auth_mode,
            "routing_decision": routing_decision,
            "doc_id": document_id,
            "doc_url": build_doc_url(document_id),
            "mode": args.mode,
            "update_engine": update_engine,
            "resolved_target": resolved_target,
            "current_title": current_title,
            "new_title": args.new_title,
            "update_details": update_details,
            "overwrite_result": overwrite_result,
            "preservation_strategy": build_update_preservation_strategy(update_engine, overwrite_result),
            "title_update_result": title_update_result,
            "warnings": list(dict.fromkeys(warnings)),
        }
        if not result["doc_url"]:
            result["web_link_notice"] = build_web_link_notice(resource_kind="document")
        image_failures = overwrite_result.get("image_failures")
        if isinstance(image_failures, list) and image_failures:
            result["image_failures"] = image_failures
        if args.output:
            pathlib.Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
            result["output"] = args.output
        print_json(result)
    except SystemExit as exc:
        raise_with_auth_fallback_guidance(exc, auth_mode)
