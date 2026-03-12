"""Reaction-related command handlers for feishu-im-workflow."""

from __future__ import annotations

import argparse

from .common import REACTION_EMOJIS, im_request, normalize_result, print_json, print_result_or_exit, resolve_token


def cmd_add_reaction(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="add-reaction",
    )
    response = im_request(
        method="POST",
        path=f"/im/v1/messages/{args.message_id}/reactions",
        token=token,
        body={"reaction_type": {"emoji_type": args.emoji_type}},
    )
    data = response.get("data") or {}
    result = normalize_result(
        api_alias="im_v1_messageReaction_create",
        auth_mode=auth_mode,
        response=response,
        extra={
            "message_id": args.message_id,
            "reaction_id": data.get("reaction_id"),
            "emoji_type": ((data.get("reaction_type") or {}).get("emoji_type")),
        },
    )
    print_result_or_exit(result, command_name="add-reaction")


def cmd_list_reactions(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="list-reactions",
    )
    response = im_request(
        method="GET",
        path=f"/im/v1/messages/{args.message_id}/reactions",
        token=token,
        query={
            "emoji_type": args.emoji_type,
            "page_size": args.page_size,
            "page_token": args.page_token,
        },
    )
    data = response.get("data") or {}
    result = normalize_result(
        api_alias="im_v1_messageReaction_list",
        auth_mode=auth_mode,
        response=response,
        extra={
            "message_id": args.message_id,
            "reaction_count": len(data.get("items") or []),
        },
    )
    print_result_or_exit(result, command_name="list-reactions")


def cmd_remove_reaction(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="remove-reaction",
    )
    response = im_request(
        method="DELETE",
        path=f"/im/v1/messages/{args.message_id}/reactions/{args.reaction_id}",
        token=token,
    )
    data = response.get("data") or {}
    result = normalize_result(
        api_alias="im_v1_messageReaction_delete",
        auth_mode=auth_mode,
        response=response,
        extra={
            "message_id": args.message_id,
            "reaction_id": data.get("reaction_id") or args.reaction_id,
        },
    )
    print_result_or_exit(result, command_name="remove-reaction")


def cmd_list_reaction_emojis(args: argparse.Namespace) -> None:
    print_json(
        {
            "ok": True,
            "source": "built_in_reference",
            "preferred_positive": [
                "THUMBSUP",
                "THANKS",
                "APPLAUSE",
                "MUSCLE",
                "FINGERHEART",
                "DONE",
                "SMILE",
                "LOVE",
                "PARTY",
                "HEART",
            ],
            "emoji_types": REACTION_EMOJIS,
            "doc_note": "Reaction emoji reference is maintained as a built-in helper list. Prefer lively positive emojis first; see references/reaction-emojis.md and the official 飞书消息表情文档 for the complete catalog.",
        }
    )

