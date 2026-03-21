from __future__ import annotations

"""Low-risk read/share/comment commands and shared command helpers."""

import argparse
import json
import pathlib

from .common import (
    build_wiki_url,
    extract_ref,
    fetch_wiki_node,
    print_json,
    resolve_contact_email,
    resolve_user_open_id_by_query,
    resolve_target_for_api,
)
from .document_ops import (
    build_api_plan,
    create_document_comment,
    extract_raw_content,
    fetch_document_blocks,
    fetch_raw_content,
    grant_permission_member,
    list_document_comments,
    list_documents,
    parse_comment_elements_argument,
    remove_permission_member,
    resolve_bearer_token,
    transfer_permission_owner,
    update_permission_member,
)
from .markdown_ops import normalize_markdown
from .media_ops import (
    build_failure_hints,
    build_image_manifest,
    collect_media_refs,
    download_media_file,
    download_whiteboard_as_image,
    export_docx_and_extract_images,
    merge_exported_images,
    order_and_dedupe_downloaded_media,
    summarize_downloaded_media,
)


TENANT_PERMISSION_NEEDLES = (
    "403",
    "forbidden",
    "no permission",
    "unauthorized",
    "permission denied",
    "1069902",
    "1069914",
    "1770032",
    "2890005",
)


def build_direct_write_decision(
    *,
    operation: str,
    markdown_arg: str | None,
    markdown_file: str | None,
    content_type: str = "markdown",
) -> dict[str, object]:
    content_source = "empty_document"
    reason = "当前请求只创建空文档，不写入正文内容。"
    warnings: list[str] = []
    recommended_alternative: str | None = None
    if markdown_file:
        content_source = "local_text_file"
        reason = "当前请求会先读取本地文本文件，再按直接文本写入方式创建或更新飞书文档。"
        recommended_alternative = "import-doc"
        warnings.append("如果你的目标是把现有文件整体导入飞书并保留文件导入语义，应改用 import-doc。")
    elif markdown_arg:
        content_source = "inline_text"
        reason = "当前请求会把命令行传入的文本直接写入飞书文档。"
    return {
        "workflow_kind": "direct_text_write",
        "operation": operation,
        "preferred_entrypoint": "update-doc" if operation in {"update", "append"} else f"{operation}-doc",
        "content_source": content_source,
        "content_type": content_type,
        "execution_engine": "append_blocks" if operation == "append" else "create_convert_then_descendant",
        "fallbacks": ["parser_fallback"],
        "reason": reason,
        "recommended_alternative": recommended_alternative,
        "warnings": warnings,
    }


def build_import_decision(*, input_file: pathlib.Path, file_extension: str, target_type: str) -> dict[str, object]:
    return {
        "workflow_kind": "file_import",
        "operation": "import",
        "preferred_entrypoint": "import-doc",
        "content_source": "local_file",
        "input_file": str(input_file),
        "file_extension": file_extension,
        "target_type": target_type,
        "execution_engine": "drive_import_task",
        "fallbacks": [],
        "reason": "当前请求会把现有本地文件整体导入飞书，不会按直接文本写入的方式拆块创建。",
    }


def build_plan_routing_decision(operation: str, markdown_file: str | None) -> dict[str, object]:
    if operation == "import":
        return {
            "workflow_kind": "file_import",
            "preferred_entrypoint": "import-doc",
            "reason": "导入现有文件时优先走 import_tasks。",
        }
    if operation in {"create", "append", "update"}:
        return build_direct_write_decision(
            operation="append" if operation == "append" else operation,
            markdown_arg=None,
            markdown_file=markdown_file,
        )
    return {
        "workflow_kind": "read_or_export",
        "preferred_entrypoint": operation,
        "reason": "读取和导出不涉及“文件导入”与“直接文本写入”的决策分流。",
    }


def build_user_token_fallback_hint() -> str:
    return (
        "当前调用看起来是应用身份（tenant/app）权限不足。请先切换到 feishu-auth-and-scopes，"
        "获取或刷新 user token，再通过 --user-access-token 重试当前文档命令。"
    )


def build_update_preservation_strategy(update_engine: str, overwrite_result: dict[str, object]) -> dict[str, object]:
    if update_engine == "append_blocks":
        return {
            "granularity": "append_only",
            "existing_top_level_blocks_preserved": True,
            "affected_scope": "仅新增块",
            "risk_level": "low",
        }
    if update_engine == "whole_document_overwrite":
        return {
            "granularity": "top_level_diff_overwrite",
            "existing_top_level_blocks_preserved": True,
            "preserved_prefix_blocks": int(overwrite_result.get("preserved_prefix_blocks") or 0),
            "preserved_suffix_blocks": int(overwrite_result.get("preserved_suffix_blocks") or 0),
            "affected_scope": "仅替换 diff 命中的顶层块范围",
            "risk_level": "medium",
            "notes": [
                "未变化的前后缀顶层块会被保留。",
                "被替换范围内的评论、块元数据和嵌入媒体仍可能丢失。",
            ],
        }
    if update_engine in {
        "block_patch_by_title",
        "block_patch_by_selection",
        "block_patch_within_single_block",
        "block_patch_by_partial_selection_range",
    }:
        operations = overwrite_result.get("operations")
        recreated_blocks = 0
        text_element_updates = 0
        if isinstance(operations, list):
            for item in operations:
                if not isinstance(item, dict):
                    continue
                patch_method = item.get("patch_method")
                if patch_method == "delete_and_recreate":
                    recreated_blocks += 1
                elif patch_method == "update_text_elements":
                    text_element_updates += 1
        return {
            "granularity": update_engine,
            "existing_top_level_blocks_preserved": True,
            "affected_scope": "仅命中的标题 section / selection 范围",
            "risk_level": "low" if recreated_blocks == 0 else "medium",
            "text_element_updates": text_element_updates,
            "delete_and_recreate_blocks": recreated_blocks,
            "notes": (
                ["命中范围外的顶层块会保留。"]
                + (
                    ["命中范围内有块通过 delete_and_recreate 更新，对这些块的评论、块元数据和嵌入媒体仍可能丢失。"]
                    if recreated_blocks
                    else ["命中范围主要通过块级 patch / text elements 更新，保留性更好。"]
                )
            ),
        }
    return {
        "granularity": update_engine,
        "existing_top_level_blocks_preserved": False,
        "affected_scope": "未知",
        "risk_level": "high",
    }


def should_suggest_user_token_fallback(error_text: str, auth_mode: str) -> bool:
    lowered = error_text.lower()
    if "tenant" not in auth_mode.lower():
        return False
    return any(needle in lowered for needle in TENANT_PERMISSION_NEEDLES)


def raise_with_auth_fallback_guidance(exc: SystemExit, auth_mode: str) -> None:
    message = str(exc)
    if should_suggest_user_token_fallback(message, auth_mode):
        raise SystemExit(f"{message}\n\n{build_user_token_fallback_hint()}")
    raise exc


def parse_optional_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise SystemExit(f"invalid boolean value: {value!r}; expected true/false")


def resolve_comment_bearer_token(args: argparse.Namespace) -> tuple[str, str]:
    if args.use_tenant_token or args.tenant_access_token:
        return resolve_bearer_token(
            user_access_token=args.user_access_token,
            tenant_access_token=args.tenant_access_token,
            use_tenant_token=args.use_tenant_token,
        )
    if args.user_access_token:
        return resolve_bearer_token(
            user_access_token=args.user_access_token,
            tenant_access_token=None,
            use_tenant_token=False,
        )
    # Comments default to tenant token; require explicit --tenant-access-token
    return resolve_bearer_token(
        user_access_token=None,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=True,
    )


def should_auto_grant_default_access(auth_mode: str) -> bool:
    return "tenant" in auth_mode.lower()


def cmd_extract_ref(args: argparse.Namespace) -> None:
    print_json(extract_ref(args.ref))


def cmd_normalize_markdown(args: argparse.Namespace) -> None:
    content = pathlib.Path(args.input).read_text(encoding="utf-8")
    normalized = normalize_markdown(content, args.title)
    if args.output:
        pathlib.Path(args.output).write_text(normalized, encoding="utf-8")
    else:
        print(normalized, end="")


def cmd_api_plan(args: argparse.Namespace) -> None:
    plan = build_api_plan(args.operation, args.ref, args.title, args.markdown_file, args.token_type)
    plan["routing_decision"] = build_plan_routing_decision(args.operation, args.markdown_file)
    print_json(plan)


def cmd_fetch_content(args: argparse.Namespace) -> None:
    target = extract_ref(args.ref)
    bearer_token, auth_mode = resolve_bearer_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
    )
    try:
        resolved_target = resolve_target_for_api(target, bearer_token)
        document_id = str(resolved_target.get("resolved_document_id") or target["document_id"])
        document_kind = str(resolved_target.get("resolved_kind") or target["kind"] or "docx")

        blocks: list[dict[str, object]] = []
        media_refs: list[dict[str, object]] = []
        downloaded_media: list[dict[str, object]] = []
        export_docx_path: pathlib.Path | None = None
        media_warnings: list[str] = []
        media_failures: list[dict[str, object]] = []
        permission_hints: list[str] = []

        if args.include_media or args.save_blocks:
            blocks = fetch_document_blocks(document_id, bearer_token)
            media_refs = collect_media_refs(blocks)
            if args.images_only:
                media_refs = [item for item in media_refs if item.get("kind") == "image"]
            if args.media_dir:
                media_dir = pathlib.Path(args.media_dir)
            elif args.output:
                media_dir = pathlib.Path(args.output).with_suffix("")
                media_dir = media_dir.parent / f"{media_dir.name}_assets"
            else:
                media_dir = pathlib.Path.cwd() / f"{document_id}_assets"
            media_dir.mkdir(parents=True, exist_ok=True)
            if args.include_media and media_refs:
                unresolved_export_refs: list[dict[str, object]] = []
                image_refs = [item for item in media_refs if item.get("kind") == "image"]
                for media_ref in image_refs:
                    token = media_ref.get("token")
                    if not isinstance(token, str):
                        continue
                    try:
                        downloaded_media.append(download_media_file(token, bearer_token, media_dir, "image"))
                        media_ref["download_status"] = "downloaded_directly"
                    except SystemExit as inner_exc:
                        failure_text = f"image {token} download failed: {inner_exc}"
                        media_warnings.append(failure_text)
                        media_failures.append(
                            {
                                "token": token,
                                "kind": "image",
                                "stage": "direct_download",
                                "reason": str(inner_exc),
                                "next_step": "优先改用 user token 重试；如果仍失败，再回退导出 docx 抽取图片快照。",
                            }
                        )
                        permission_hints.extend(
                            build_failure_hints(
                                failure_text,
                                operation="image_download",
                                auth_mode=auth_mode,
                                target_kind=document_kind,
                            )
                        )
                        media_ref["download_status"] = "download_failed"
                        media_ref["reason"] = str(inner_exc)
                        unresolved_export_refs.append(media_ref)

                if not args.images_only:
                    for media_ref in media_refs:
                        token = media_ref.get("token")
                        kind = str(media_ref.get("kind") or "media")
                        if not isinstance(token, str):
                            continue
                        if kind == "image":
                            continue
                        try:
                            if kind == "whiteboard":
                                downloaded_media.append(download_whiteboard_as_image(token, bearer_token, media_dir))
                            else:
                                downloaded_media.append(download_media_file(token, bearer_token, media_dir, kind))
                            media_ref["download_status"] = "downloaded_directly"
                        except SystemExit as exc:
                            failure_text = f"{kind} {token} download failed: {exc}"
                            media_warnings.append(failure_text)
                            media_failures.append(
                                {
                                    "token": token,
                                    "kind": kind,
                                    "stage": "direct_download",
                                    "reason": str(exc),
                                    "next_step": (
                                        "改用 user token 重试白板下载。"
                                        if kind == "whiteboard"
                                        else "改用 user token 重试附件直下；如果仍失败，保留附件元信息并在总结里说明。"
                                        if kind == "file"
                                        else "改用 user token 重试。"
                                    ),
                                }
                            )
                            media_ref["download_status"] = "download_failed"
                            media_ref["reason"] = str(exc)
                            unresolved_export_refs.append(media_ref)
                            permission_hints.extend(
                                build_failure_hints(
                                    str(exc),
                                    operation=(
                                        "whiteboard_download"
                                        if kind == "whiteboard"
                                        else "file_download" if kind == "file" else "image_download"
                                    ),
                                    auth_mode=auth_mode,
                                    target_kind=document_kind,
                                )
                            )

                if unresolved_export_refs:
                    try:
                        exported_media, export_docx_path = export_docx_and_extract_images(
                            document_id,
                            bearer_token,
                            media_dir,
                            file_type=document_kind,
                        )
                        merged_media, still_unmatched = merge_exported_images(
                            exported_media,
                            downloaded_media,
                            unresolved_export_refs,
                        )
                        downloaded_media.extend(merged_media)
                        for media_ref in still_unmatched:
                            _ = media_ref
                        for media_ref in unresolved_export_refs:
                            if media_ref.get("download_status") != "exported_from_docx_fallback":
                                media_ref["reason"] = "已尝试白板/媒体直下与导出 docx 抽取，但仍未找到可对应的导出快照。"
                    except SystemExit as exc:
                        failure_text = str(exc)
                        media_warnings.append(failure_text)
                        media_failures.append(
                            {
                                "kind": "export",
                                "stage": "export_fallback",
                                "reason": str(exc),
                                "next_step": "检查导出权限、token 类型和目标 token 类型；若只是图片缺失，优先保留正文与已下载媒体。",
                            }
                        )
                        permission_hints.extend(
                            build_failure_hints(
                                failure_text,
                                operation="export",
                                auth_mode=auth_mode,
                                target_kind=document_kind,
                            )
                        )
            if args.save_blocks:
                pathlib.Path(args.save_blocks).write_text(json.dumps(blocks, ensure_ascii=True, indent=2), encoding="utf-8")

        response = fetch_raw_content(document_id, bearer_token)
        content = extract_raw_content(response)
        result = {
            "ref": args.ref,
            "target": target,
            "resolved_target": resolved_target,
            "auth_mode": auth_mode,
            "content_length": len(content),
            "content": content,
        }
        if blocks:
            result["block_count"] = len(blocks)
        if media_refs:
            result["media_refs"] = media_refs
        if downloaded_media:
            downloaded_media = order_and_dedupe_downloaded_media(downloaded_media, media_refs)
            media_summary = summarize_downloaded_media(downloaded_media)
            result["downloaded_media"] = downloaded_media
            result["media_summary"] = media_summary
            result["image_understanding"] = media_summary["image_understanding"]
            if media_summary.get("attachment_count"):
                result["attachment_summary"] = {
                    "attachment_count": media_summary["attachment_count"],
                    "attachments": media_summary["attachments"],
                    "next_step": media_summary["attachment_next_step"],
                }
        if export_docx_path:
            result["export_docx_path"] = str(export_docx_path)
        if media_warnings:
            result["media_warnings"] = media_warnings
        if media_failures:
            result["media_failures"] = media_failures
        if permission_hints:
            result["permission_hints"] = list(dict.fromkeys(permission_hints))
        if media_refs and not downloaded_media:
            result["browser_capture_fallback_recommended"] = True
        if args.save_image_manifest:
            image_manifest = build_image_manifest(
                document_id,
                downloaded_media,
                export_docx_path=export_docx_path,
                warnings=media_warnings,
            )
            if permission_hints:
                image_manifest["permission_hints"] = list(dict.fromkeys(permission_hints))
            pathlib.Path(args.save_image_manifest).write_text(
                json.dumps(image_manifest, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
            result["image_manifest"] = args.save_image_manifest
        if args.output:
            pathlib.Path(args.output).write_text(content, encoding="utf-8")
            result["output"] = args.output
        print_json(result)
    except SystemExit as exc:
        raise_with_auth_fallback_guidance(exc, auth_mode)


def resolve_permission_target(args: argparse.Namespace, bearer_token: str) -> tuple[str, str, dict[str, object]]:
    target = extract_ref(args.ref)
    doc_type = args.type
    if not doc_type:
        doc_type = "wiki" if target.get("kind") == "wiki" else "docx"
    if doc_type == "wiki":
        token = str(target.get("token") or "")
        if not token:
            raise SystemExit("wiki ref missing token")
        return token, doc_type, target
    resolved_target = resolve_target_for_api(target, bearer_token)
    token = str(resolved_target.get("resolved_document_id") or target.get("document_id") or target.get("token") or "")
    if not token:
        raise SystemExit("could not resolve document token for permission operation")
    return token, doc_type, resolved_target


def resolve_member_id(
    member_id: str | None,
    member_type: str,
    *,
    grant_email: str | None = None,
    member_query: str | None = None,
    bearer_token: str | None = None,
) -> str | None:
    if member_id is not None and member_id.strip():
        return member_id.strip()
    if member_type == "email":
        return resolve_contact_email(grant_email)
    if member_type == "openid":
        if member_query and member_query.strip():
            return resolve_user_open_id_by_query(member_query, bearer_token=bearer_token)
    return None


def cmd_share_doc(args: argparse.Namespace) -> None:
    bearer_token, auth_mode = resolve_bearer_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
    )
    member_id = resolve_member_id(
        args.member_id,
        args.member_type,
        grant_email=args.grant_email,
        member_query=args.member_query,
        bearer_token=bearer_token,
    )
    if not member_id:
        if args.member_type == "email":
            raise SystemExit("share-doc requires --member-id, or --grant-email / MY_LARK_EMAIL for email-based sharing")
        if args.member_type == "openid":
            raise SystemExit("share-doc requires --member-id, or --member-query to resolve a user by email/name into open_id")
        raise SystemExit("share-doc requires --member-id for the selected member_type")
    try:
        token, doc_type, resolved_target = resolve_permission_target(args, bearer_token)
        permission_grant_result = grant_permission_member(
            token=token,
            doc_type=doc_type,
            member_id=member_id,
            member_type=args.member_type,
            bearer_token=bearer_token,
            perm=args.perm,
            need_notification=args.need_notification,
        )
        result = {
            "success": True,
            "auth_mode": auth_mode,
            "ref": args.ref,
            "resolved_target": resolved_target,
            "token": token,
            "doc_type": doc_type,
            "member_id": member_id,
            "member_type": args.member_type,
            "perm": args.perm,
            "permission_grant_result": permission_grant_result,
        }
        if args.output:
            pathlib.Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
            result["output"] = args.output
        print_json(result)
    except SystemExit as exc:
        raise_with_auth_fallback_guidance(exc, auth_mode)


def cmd_update_share(args: argparse.Namespace) -> None:
    bearer_token, auth_mode = resolve_bearer_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
    )
    member_id = resolve_member_id(
        args.member_id,
        args.member_type,
        grant_email=args.grant_email,
        member_query=args.member_query,
        bearer_token=bearer_token,
    )
    if not member_id:
        if args.member_type == "email":
            raise SystemExit("update-share requires --member-id, or --grant-email / MY_LARK_EMAIL for email-based sharing")
        if args.member_type == "openid":
            raise SystemExit("update-share requires --member-id, or --member-query to resolve a user by email/name into open_id")
        raise SystemExit("update-share requires --member-id for the selected member_type")
    try:
        token, doc_type, resolved_target = resolve_permission_target(args, bearer_token)
        permission_update_result = update_permission_member(
            token=token,
            doc_type=doc_type,
            member_id=member_id,
            member_type=args.member_type,
            perm=args.perm,
            bearer_token=bearer_token,
            need_notification=args.need_notification,
        )
        result = {
            "success": True,
            "auth_mode": auth_mode,
            "ref": args.ref,
            "resolved_target": resolved_target,
            "token": token,
            "doc_type": doc_type,
            "member_id": member_id,
            "member_type": args.member_type,
            "perm": args.perm,
            "permission_update_result": permission_update_result,
        }
        if args.output:
            pathlib.Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
            result["output"] = args.output
        print_json(result)
    except SystemExit as exc:
        raise_with_auth_fallback_guidance(exc, auth_mode)


def cmd_remove_share(args: argparse.Namespace) -> None:
    bearer_token, auth_mode = resolve_bearer_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
    )
    member_id = resolve_member_id(
        args.member_id,
        args.member_type,
        grant_email=args.grant_email,
        member_query=args.member_query,
        bearer_token=bearer_token,
    )
    if not member_id:
        if args.member_type == "email":
            raise SystemExit("remove-share requires --member-id, or --grant-email / MY_LARK_EMAIL for email-based sharing")
        if args.member_type == "openid":
            raise SystemExit("remove-share requires --member-id, or --member-query to resolve a user by email/name into open_id")
        raise SystemExit("remove-share requires --member-id for the selected member_type")
    try:
        token, doc_type, resolved_target = resolve_permission_target(args, bearer_token)
        permission_remove_result = remove_permission_member(
            token=token,
            doc_type=doc_type,
            member_id=member_id,
            member_type=args.member_type,
            bearer_token=bearer_token,
        )
        result = {
            "success": True,
            "auth_mode": auth_mode,
            "ref": args.ref,
            "resolved_target": resolved_target,
            "token": token,
            "doc_type": doc_type,
            "member_id": member_id,
            "member_type": args.member_type,
            "permission_remove_result": permission_remove_result,
        }
        if args.output:
            pathlib.Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
            result["output"] = args.output
        print_json(result)
    except SystemExit as exc:
        raise_with_auth_fallback_guidance(exc, auth_mode)


def cmd_transfer_owner(args: argparse.Namespace) -> None:
    bearer_token, auth_mode = resolve_bearer_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
    )
    member_id = resolve_member_id(
        args.member_id,
        args.member_type,
        member_query=args.member_query,
        bearer_token=bearer_token,
    )
    if not member_id:
        if args.member_type == "openid":
            raise SystemExit("transfer-owner requires --member-id, or --member-query to resolve a user by email/name into open_id")
        raise SystemExit("transfer-owner requires --member-id for the selected member_type")
    try:
        token, doc_type, resolved_target = resolve_permission_target(args, bearer_token)
        transfer_result = transfer_permission_owner(
            token=token,
            doc_type=doc_type,
            member_id=member_id,
            member_type=args.member_type,
            bearer_token=bearer_token,
            need_notification=args.need_notification,
            old_owner_perm=args.old_owner_perm,
            remove_old_owner=args.remove_old_owner,
            stay_put=args.stay_put,
        )
        result = {
            "success": True,
            "auth_mode": auth_mode,
            "ref": args.ref,
            "resolved_target": resolved_target,
            "token": token,
            "doc_type": doc_type,
            "member_id": member_id,
            "member_type": args.member_type,
            "remove_old_owner": args.remove_old_owner,
            "stay_put": args.stay_put,
            "old_owner_perm": args.old_owner_perm,
            "transfer_result": transfer_result,
        }
        if args.output:
            pathlib.Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
            result["output"] = args.output
        print_json(result)
    except SystemExit as exc:
        raise_with_auth_fallback_guidance(exc, auth_mode)


def cmd_list_docs(args: argparse.Namespace) -> None:
    bearer_token, auth_mode = resolve_bearer_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
    )
    try:
        result = list_documents(
            bearer_token=bearer_token,
            folder_token=args.folder_token,
            node_token=args.node_token,
            wiki_space=args.wiki_space,
            page_size=args.page_size,
            page_token=args.page_token,
            order_by=args.order_by,
            direction=args.direction,
        )
        output = {
            "success": True,
            "auth_mode": auth_mode,
            **result,
        }
        if args.output:
            pathlib.Path(args.output).write_text(json.dumps(output, ensure_ascii=True, indent=2), encoding="utf-8")
            output["output"] = args.output
        print_json(output)
    except SystemExit as exc:
        raise_with_auth_fallback_guidance(exc, auth_mode)


def cmd_resolve_wiki_node(args: argparse.Namespace) -> None:
    bearer_token, auth_mode = resolve_bearer_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
    )
    target = extract_ref(args.ref)
    token = str(target.get("token") or args.ref).strip()
    lookup_obj_type = str(args.obj_type or ("wiki" if target.get("kind") == "wiki" else (target.get("kind") or "docx")))
    try:
        node = fetch_wiki_node(token, bearer_token, obj_type=lookup_obj_type)
        result = {
            "success": True,
            "auth_mode": auth_mode,
            "ref": args.ref,
            "lookup_obj_type": lookup_obj_type,
            "token": token,
            "node_token": node.get("node_token"),
            "space_id": node.get("space_id"),
            "obj_token": node.get("obj_token"),
            "obj_type": node.get("obj_type"),
            "title": node.get("title"),
            "url": build_wiki_url(str(node.get("node_token"))) if node.get("node_token") else None,
            "raw": node,
        }
        if args.output:
            pathlib.Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
            result["output"] = args.output
        print_json(result)
    except SystemExit as exc:
        raise_with_auth_fallback_guidance(exc, auth_mode)


def cmd_get_comments(args: argparse.Namespace) -> None:
    bearer_token, auth_mode = resolve_comment_bearer_token(args)
    try:
        result = list_document_comments(
            ref=args.ref,
            bearer_token=bearer_token,
            is_whole=parse_optional_bool(args.is_whole),
            is_solved=parse_optional_bool(args.is_solved),
            page_size=args.page_size,
            page_token=args.page_token,
            user_id_type=args.user_id_type,
            include_replies=not args.no_replies,
        )
        output = {
            "success": True,
            "auth_mode": auth_mode,
            "ref": args.ref,
            **result,
        }
        if args.output:
            pathlib.Path(args.output).write_text(json.dumps(output, ensure_ascii=True, indent=2), encoding="utf-8")
            output["output"] = args.output
        print_json(output)
    except SystemExit as exc:
        raise_with_auth_fallback_guidance(exc, auth_mode)


def cmd_add_comments(args: argparse.Namespace) -> None:
    if args.selection_with_ellipsis or args.selection_by_title:
        raise SystemExit(
            "当前 open API 的 fileComment.create 只支持创建全文评论，暂不支持按 selection / 标题创建内容锚定评论。"
        )
    if bool(args.text) == bool(args.elements):
        raise SystemExit("add-comments requires exactly one of --text or --elements")
    elements = (
        [{"type": "text", "text": args.text}]
        if args.text
        else parse_comment_elements_argument(args.elements)
    )
    bearer_token, auth_mode = resolve_comment_bearer_token(args)
    try:
        result = create_document_comment(
            ref=args.ref,
            elements=elements,
            bearer_token=bearer_token,
            user_id_type=args.user_id_type,
        )
        output = {
            "success": True,
            "auth_mode": auth_mode,
            "ref": args.ref,
            "input_elements": elements,
            **result,
        }
        if args.output:
            pathlib.Path(args.output).write_text(json.dumps(output, ensure_ascii=True, indent=2), encoding="utf-8")
            output["output"] = args.output
        print_json(output)
    except SystemExit as exc:
        raise_with_auth_fallback_guidance(exc, auth_mode)
