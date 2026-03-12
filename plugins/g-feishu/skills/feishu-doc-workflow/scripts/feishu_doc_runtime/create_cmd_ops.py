from __future__ import annotations

"""Create-doc command implementation."""

import argparse
import json
import pathlib

from .command_aux_ops import (
    build_direct_write_decision,
    raise_with_auth_fallback_guidance,
    should_auto_grant_default_access,
)
from .common import build_doc_url, build_web_link_notice, dedupe_strings, print_json, resolve_contact_email
from .document_ops import (
    append_content_with_strategy,
    create_document,
    grant_permission_member,
    move_document_to_wiki,
    resolve_bearer_token,
)
from .markdown_ops import (
    load_markdown_argument,
    normalize_markdown,
    preprocess_lark_flavored_markdown,
)


def cmd_create_doc(args: argparse.Namespace) -> None:
    if not args.title:
        raise SystemExit("--title is required")
    flags = [args.folder_token, args.wiki_node, args.wiki_space]
    if len([item for item in flags if item]) > 1:
        raise SystemExit("--folder-token, --wiki-node, and --wiki-space are mutually exclusive")

    markdown_source = load_markdown_argument(args.markdown, args.markdown_file) or ""
    content_type = args.content_type
    source_base_dir = pathlib.Path(args.markdown_file).resolve().parent if args.markdown_file else None
    normalized_content = (
        normalize_markdown(markdown_source, args.title) if content_type == "markdown" and markdown_source.strip() else markdown_source
    )
    syntax_warnings: list[str] = []
    if content_type == "markdown" and normalized_content.strip():
        normalized_content, syntax_warnings = preprocess_lark_flavored_markdown(normalized_content)
    routing_decision = build_direct_write_decision(
        operation="create",
        markdown_arg=args.markdown,
        markdown_file=args.markdown_file,
        content_type=content_type,
    )
    grant_email = resolve_contact_email(args.grant_email)
    bearer_token, auth_mode = resolve_bearer_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
    )
    try:
        document = create_document(args.title, bearer_token, folder_token=args.folder_token)
        document_id = str(document["document_id"])
        write_result: dict[str, object] = {}
        if normalized_content.strip():
            # New documents do not need overwrite/diff logic; write directly to
            # avoid flattening container blocks during a fake rewrite cycle.
            write_result = append_content_with_strategy(
                document_id,
                normalized_content,
                bearer_token,
                content_type=content_type,
                source_base_dir=source_base_dir,
            )

        move_result: dict[str, object] = {}
        if args.wiki_node or args.wiki_space:
            move_result = move_document_to_wiki(
                document_id,
                bearer_token,
                wiki_node=args.wiki_node,
                wiki_space=args.wiki_space,
            )

        permission_grant_result: dict[str, object] = {}
        grant_warnings: list[str] = []
        if should_auto_grant_default_access(auth_mode):
            if grant_email:
                try:
                    permission_grant_result = grant_permission_member(
                        token=document_id,
                        doc_type="docx",
                        member_id=grant_email,
                        member_type="email",
                        bearer_token=bearer_token,
                        perm="full_access",
                        need_notification=False,
                    )
                except SystemExit as exc:
                    grant_warnings.append(f"文档已创建，但自动授权 full_access 给 {grant_email} 失败：{exc}")
            else:
                grant_warnings.append("当前使用 tenant token 创建文档，但未读取到邮箱，未自动授予 full_access。请传 --grant-email 或设置 MY_LARK_EMAIL。")

        result = {
            "success": True,
            "auth_mode": auth_mode,
            "routing_decision": routing_decision,
            "doc_id": document_id,
            "title": args.title,
            "doc_url": build_doc_url(document_id),
            "grant_email": grant_email,
            "permission_grant_result": permission_grant_result,
            "content_type": content_type,
            "location": {
                "folder_token": args.folder_token,
                "wiki_node": args.wiki_node,
                "wiki_space": args.wiki_space,
            },
            "write_result": write_result,
            "move_result": move_result,
        }
        if not result["doc_url"]:
            result["web_link_notice"] = build_web_link_notice(resource_kind="document")
        image_failures = write_result.get("image_failures")
        if isinstance(image_failures, list) and image_failures:
            result["image_failures"] = image_failures
        write_warnings = write_result.get("warnings")
        parser_warnings = write_result.get("parser_warnings")
        warnings: list[str] = []
        if isinstance(write_warnings, list):
            warnings.extend(item for item in write_warnings if isinstance(item, str))
        if isinstance(parser_warnings, list):
            warnings.extend(item for item in parser_warnings if isinstance(item, str))
        warnings.extend(grant_warnings)
        decision_warnings = routing_decision.get("warnings")
        if isinstance(decision_warnings, list):
            warnings.extend(item for item in decision_warnings if isinstance(item, str))
        warnings.extend(syntax_warnings)
        if warnings:
            result["warnings"] = dedupe_strings(warnings)
        if args.output:
            pathlib.Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
            result["output"] = args.output
        print_json(result)
    except SystemExit as exc:
        raise_with_auth_fallback_guidance(exc, auth_mode)
