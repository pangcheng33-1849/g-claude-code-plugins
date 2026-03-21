from __future__ import annotations

"""CLI parser and command registration for the standalone doc workflow."""

import argparse
import os


_USER_TOKEN_HELP = "User access token (required unless --tenant-access-token is given). Use skill feishu-auth-and-scopes to obtain."
_TENANT_TOKEN_HELP = "Tenant access token (required unless --user-access-token is given). Use skill feishu-auth-and-scopes to obtain."
_TENANT_PREFERRED_TOKEN_HELP = "Tenant access token (preferred for this command). Use skill feishu-auth-and-scopes to obtain."
_USER_ALT_TOKEN_HELP = "User access token (alternative). Use skill feishu-auth-and-scopes to obtain."

from .command_aux_ops import (
    cmd_add_comments,
    cmd_api_plan,
    cmd_extract_ref,
    cmd_fetch_content,
    cmd_get_comments,
    cmd_list_docs,
    cmd_normalize_markdown,
    cmd_remove_share,
    cmd_resolve_wiki_node,
    cmd_share_doc,
    cmd_transfer_owner,
    cmd_update_share,
)
from .create_cmd_ops import cmd_create_doc
from .import_cmd_ops import cmd_import_doc
from .update_cmd_ops import cmd_update_doc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone Feishu doc workflow helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser(
        "create-doc",
        help="Create a Feishu doc and directly write Markdown/HTML content. Use import-doc if you want to import an existing file as a file-import workflow.",
    )
    create_parser.add_argument("--title", required=True)
    create_parser.add_argument("--markdown")
    create_parser.add_argument("--markdown-file")
    create_parser.add_argument("--content-type", choices=["markdown", "html"], default="markdown")
    create_parser.add_argument("--folder-token")
    create_parser.add_argument("--wiki-node")
    create_parser.add_argument("--wiki-space")
    create_parser.add_argument("--user-access-token", help=_USER_TOKEN_HELP)
    create_parser.add_argument("--tenant-access-token", help=_TENANT_TOKEN_HELP)
    create_parser.add_argument("--use-tenant-token", action="store_true")
    create_parser.add_argument("--grant-email", default=os.getenv("MY_LARK_EMAIL"))
    create_parser.add_argument("--output")
    create_parser.set_defaults(func=cmd_create_doc)

    update_parser = subparsers.add_parser(
        "update-doc",
        help="Update an existing Feishu doc. append uses direct block append; other modes currently rewrite top-level blocks.",
    )
    update_parser.add_argument("--ref", required=True)
    update_parser.add_argument(
        "--mode",
        choices=["overwrite", "append", "replace_range", "replace_all", "insert_before", "insert_after", "delete_range"],
        required=True,
    )
    update_parser.add_argument("--markdown")
    update_parser.add_argument("--markdown-file")
    update_parser.add_argument("--selection-with-ellipsis")
    update_parser.add_argument("--selection-by-title")
    update_parser.add_argument("--new-title")
    update_parser.add_argument("--user-access-token", help=_USER_TOKEN_HELP)
    update_parser.add_argument("--tenant-access-token", help=_TENANT_TOKEN_HELP)
    update_parser.add_argument("--use-tenant-token", action="store_true")
    update_parser.add_argument("--output")
    update_parser.set_defaults(func=cmd_update_doc)

    import_parser = subparsers.add_parser(
        "import-doc",
        help="Import an existing local file into Feishu docs/sheets/bitable via import_tasks. This is different from direct text write in create-doc/update-doc.",
    )
    import_parser.add_argument("--input-file")
    import_parser.add_argument("--type", choices=["docx", "sheet", "bitable"], default="docx")
    import_parser.add_argument("--file-extension")
    import_parser.add_argument("--file-name")
    import_parser.add_argument("--mount-key")
    import_parser.add_argument("--folder-token")
    import_parser.add_argument("--async", dest="async_mode", action="store_true")
    import_parser.add_argument("--task-id")
    import_parser.add_argument("--state-dir")
    import_parser.add_argument("--async-threshold-bytes", type=int, default=1048576)
    import_parser.add_argument("--user-access-token", help=_USER_TOKEN_HELP)
    import_parser.add_argument("--tenant-access-token", help=_TENANT_TOKEN_HELP)
    import_parser.add_argument("--use-tenant-token", action="store_true")
    import_parser.add_argument("--grant-email", default=os.getenv("MY_LARK_EMAIL"))
    import_parser.add_argument("--timeout-seconds", type=int, default=180)
    import_parser.add_argument("--output")
    import_parser.set_defaults(func=cmd_import_doc)

    share_parser = subparsers.add_parser(
        "share-doc",
        help="Grant a permission member on an existing Feishu doc/wiki. This formalizes the implicit share step used after create/import.",
    )
    share_parser.add_argument("--ref", required=True)
    share_parser.add_argument("--type", choices=["docx", "doc", "sheet", "bitable", "wiki", "file", "mindnote", "slides"])
    share_parser.add_argument("--member-id")
    share_parser.add_argument("--member-query", help="Resolve a Feishu user by email/name via search and use the matched open_id.")
    share_parser.add_argument("--grant-email", default=os.getenv("MY_LARK_EMAIL"))
    share_parser.add_argument("--member-type", choices=["email", "openid", "userid", "unionid", "openchat", "opendepartmentid", "groupid"], default="email")
    share_parser.add_argument("--perm", choices=["view", "edit", "full_access"], default="full_access")
    share_parser.add_argument("--need-notification", action="store_true")
    share_parser.add_argument("--user-access-token", help=_USER_TOKEN_HELP)
    share_parser.add_argument("--tenant-access-token", help=_TENANT_TOKEN_HELP)
    share_parser.add_argument("--use-tenant-token", action="store_true")
    share_parser.add_argument("--output")
    share_parser.set_defaults(func=cmd_share_doc)

    update_share_parser = subparsers.add_parser(
        "update-share",
        help="Update an existing permission member on a Feishu doc/wiki.",
    )
    update_share_parser.add_argument("--ref", required=True)
    update_share_parser.add_argument("--type", choices=["docx", "doc", "sheet", "bitable", "wiki", "file", "mindnote", "slides"])
    update_share_parser.add_argument("--member-id")
    update_share_parser.add_argument("--member-query", help="Resolve a Feishu user by email/name via search and use the matched open_id.")
    update_share_parser.add_argument("--grant-email", default=os.getenv("MY_LARK_EMAIL"))
    update_share_parser.add_argument("--member-type", choices=["email", "openid", "userid", "unionid", "openchat", "opendepartmentid", "groupid"], default="email")
    update_share_parser.add_argument("--perm", choices=["view", "edit", "full_access"], required=True)
    update_share_parser.add_argument("--need-notification", action="store_true")
    update_share_parser.add_argument("--user-access-token", help=_USER_TOKEN_HELP)
    update_share_parser.add_argument("--tenant-access-token", help=_TENANT_TOKEN_HELP)
    update_share_parser.add_argument("--use-tenant-token", action="store_true")
    update_share_parser.add_argument("--output")
    update_share_parser.set_defaults(func=cmd_update_share)

    remove_share_parser = subparsers.add_parser(
        "remove-share",
        help="Remove an existing permission member from a Feishu doc/wiki.",
    )
    remove_share_parser.add_argument("--ref", required=True)
    remove_share_parser.add_argument("--type", choices=["docx", "doc", "sheet", "bitable", "wiki", "file", "mindnote", "slides"])
    remove_share_parser.add_argument("--member-id")
    remove_share_parser.add_argument("--member-query", help="Resolve a Feishu user by email/name via search and use the matched open_id.")
    remove_share_parser.add_argument("--grant-email", default=os.getenv("MY_LARK_EMAIL"))
    remove_share_parser.add_argument("--member-type", choices=["email", "openid", "userid", "unionid", "openchat", "opendepartmentid", "groupid"], default="email")
    remove_share_parser.add_argument("--user-access-token", help=_USER_TOKEN_HELP)
    remove_share_parser.add_argument("--tenant-access-token", help=_TENANT_TOKEN_HELP)
    remove_share_parser.add_argument("--use-tenant-token", action="store_true")
    remove_share_parser.add_argument("--output")
    remove_share_parser.set_defaults(func=cmd_remove_share)

    transfer_owner_parser = subparsers.add_parser(
        "transfer-owner",
        help="Transfer the owner of an existing Feishu doc/wiki to another member.",
    )
    transfer_owner_parser.add_argument("--ref", required=True)
    transfer_owner_parser.add_argument("--type", choices=["docx", "doc", "sheet", "bitable", "wiki", "file", "mindnote", "slides"])
    transfer_owner_parser.add_argument("--member-id")
    transfer_owner_parser.add_argument("--member-query", help="Resolve a Feishu user by email/name via search and use the matched open_id.")
    transfer_owner_parser.add_argument("--member-type", choices=["email", "openid", "userid"], default="email")
    transfer_owner_parser.add_argument("--need-notification", action="store_true")
    transfer_owner_parser.add_argument("--old-owner-perm", choices=["view", "edit", "full_access"])
    transfer_owner_parser.add_argument("--remove-old-owner", action="store_true")
    transfer_owner_parser.add_argument("--stay-put", action="store_true")
    transfer_owner_parser.add_argument("--user-access-token", help=_USER_TOKEN_HELP)
    transfer_owner_parser.add_argument("--tenant-access-token", help=_TENANT_TOKEN_HELP)
    transfer_owner_parser.add_argument("--use-tenant-token", action="store_true")
    transfer_owner_parser.add_argument("--output")
    transfer_owner_parser.set_defaults(func=cmd_transfer_owner)

    list_docs_parser = subparsers.add_parser(
        "list-docs",
        help="List docs/files in My Drive, a folder, or a wiki space/node.",
    )
    list_docs_parser.add_argument("--folder-token")
    list_docs_parser.add_argument("--node-token")
    list_docs_parser.add_argument("--wiki-space")
    list_docs_parser.add_argument("--page-size", type=int, default=50)
    list_docs_parser.add_argument("--page-token")
    list_docs_parser.add_argument("--order-by")
    list_docs_parser.add_argument("--direction")
    list_docs_parser.add_argument("--user-access-token", help=_USER_TOKEN_HELP)
    list_docs_parser.add_argument("--tenant-access-token", help=_TENANT_TOKEN_HELP)
    list_docs_parser.add_argument("--use-tenant-token", action="store_true")
    list_docs_parser.add_argument("--output")
    list_docs_parser.set_defaults(func=cmd_list_docs)

    resolve_wiki_node_parser = subparsers.add_parser(
        "resolve-wiki-node",
        help="Resolve a wiki node from a wiki token or a docx token.",
    )
    resolve_wiki_node_parser.add_argument("--ref", required=True)
    resolve_wiki_node_parser.add_argument("--obj-type", choices=["wiki", "docx", "doc", "sheet", "slides", "bitable", "file"])
    resolve_wiki_node_parser.add_argument("--user-access-token", help=_USER_TOKEN_HELP)
    resolve_wiki_node_parser.add_argument("--tenant-access-token", help=_TENANT_TOKEN_HELP)
    resolve_wiki_node_parser.add_argument("--use-tenant-token", action="store_true")
    resolve_wiki_node_parser.add_argument("--output")
    resolve_wiki_node_parser.set_defaults(func=cmd_resolve_wiki_node)

    get_comments_parser = subparsers.add_parser(
        "get-comments",
        help="List comments and replies for a Feishu doc/file.",
    )
    get_comments_parser.add_argument("--ref", required=True)
    get_comments_parser.add_argument("--is-whole")
    get_comments_parser.add_argument("--is-solved")
    get_comments_parser.add_argument("--page-size", type=int, default=50)
    get_comments_parser.add_argument("--page-token")
    get_comments_parser.add_argument("--user-id-type", default="open_id")
    get_comments_parser.add_argument("--no-replies", action="store_true")
    get_comments_parser.add_argument("--user-access-token", help=_USER_ALT_TOKEN_HELP)
    get_comments_parser.add_argument("--tenant-access-token", help=_TENANT_PREFERRED_TOKEN_HELP)
    get_comments_parser.add_argument("--use-tenant-token", action="store_true")
    get_comments_parser.add_argument("--output")
    get_comments_parser.set_defaults(func=cmd_get_comments)

    add_comments_parser = subparsers.add_parser(
        "add-comments",
        help="Add a top-level comment to a Feishu doc/file.",
    )
    add_comments_parser.add_argument("--ref", required=True)
    add_comments_parser.add_argument("--text")
    add_comments_parser.add_argument("--elements")
    add_comments_parser.add_argument("--selection-with-ellipsis")
    add_comments_parser.add_argument("--selection-by-title")
    add_comments_parser.add_argument("--user-id-type", default="open_id")
    add_comments_parser.add_argument("--user-access-token", help=_USER_ALT_TOKEN_HELP)
    add_comments_parser.add_argument("--tenant-access-token", help=_TENANT_PREFERRED_TOKEN_HELP)
    add_comments_parser.add_argument("--use-tenant-token", action="store_true")
    add_comments_parser.add_argument("--output")
    add_comments_parser.set_defaults(func=cmd_add_comments)

    extract_ref_parser = subparsers.add_parser("extract-ref", help="Extract doc kind, token, and node_id from a URL or token.")
    extract_ref_parser.add_argument("--ref", required=True)
    extract_ref_parser.set_defaults(func=cmd_extract_ref)

    normalize_parser = subparsers.add_parser("normalize-markdown", help="Clean Markdown before Feishu doc creation or update.")
    normalize_parser.add_argument("--input", required=True)
    normalize_parser.add_argument("--title")
    normalize_parser.add_argument("--output")
    normalize_parser.set_defaults(func=cmd_normalize_markdown)

    plan_parser = subparsers.add_parser("api-plan", help="Build a document API execution plan.")
    plan_parser.add_argument("--operation", choices=["read", "export", "create", "update", "append", "import"], required=True)
    plan_parser.add_argument("--ref")
    plan_parser.add_argument("--title")
    plan_parser.add_argument("--markdown-file")
    plan_parser.add_argument("--token-type", default="tenant_or_user")
    plan_parser.set_defaults(func=cmd_api_plan)

    fetch_parser = subparsers.add_parser("fetch-content", help="Fetch Feishu doc content, blocks, and optionally download media assets.")
    fetch_parser.add_argument("--ref", required=True)
    fetch_parser.add_argument("--user-access-token", help=_USER_TOKEN_HELP)
    fetch_parser.add_argument("--tenant-access-token", help=_TENANT_TOKEN_HELP)
    fetch_parser.add_argument("--use-tenant-token", action="store_true")
    fetch_parser.add_argument("--output")
    fetch_parser.add_argument("--include-media", action="store_true")
    fetch_parser.add_argument("--images-only", action="store_true")
    fetch_parser.add_argument("--media-dir")
    fetch_parser.add_argument("--save-blocks")
    fetch_parser.add_argument("--save-image-manifest")
    fetch_parser.set_defaults(func=cmd_fetch_content)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
