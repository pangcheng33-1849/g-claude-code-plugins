"""Chat and message-list command handlers for feishu-im-workflow."""

from __future__ import annotations

import argparse

from .common import fail, im_request, maybe_uuid, normalize_result, print_result_or_exit, resolve_token


def cmd_get_chat(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="get-chat",
    )
    response = im_request(
        method="GET",
        path=f"/im/v1/chats/{args.chat_id}",
        token=token,
        query={"user_id_type": args.user_id_type},
    )
    result = normalize_result(
        api_alias="im_v1_chat_get",
        auth_mode=auth_mode,
        response=response,
        extra={"chat_id": args.chat_id},
    )
    print_result_or_exit(result, command_name="get-chat")


def cmd_create_chat(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="create-chat",
    )
    body: dict[str, object] = {"name": args.name}
    if args.description:
        body["description"] = args.description
    if args.owner_id:
        body["owner_id"] = args.owner_id
    if args.member_id:
        body["user_id_list"] = args.member_id
    if args.bot_id:
        body["bot_id_list"] = args.bot_id
    if args.avatar:
        body["avatar"] = args.avatar
    response = im_request(
        method="POST",
        path="/im/v1/chats",
        token=token,
        query={
            "user_id_type": args.user_id_type,
            "set_bot_manager": "true" if args.set_bot_manager else "false",
            "uuid": maybe_uuid(args.uuid),
        },
        body=body,
    )
    data = response.get("data") or {}
    extra = {
        "chat_id": data.get("chat_id"),
        "name": ((data.get("chat") or {}).get("name")) or args.name,
        "owner_id": ((data.get("chat") or {}).get("owner_id")) or args.owner_id,
        "member_ids": args.member_id or [],
        "bot_ids": args.bot_id or [],
        "chat_mode": ((data.get("chat") or {}).get("chat_mode")),
    }
    result = normalize_result(
        api_alias="im_v1_chat_create",
        auth_mode=auth_mode,
        response=response,
        extra=extra,
    )
    print_result_or_exit(result, command_name="create-chat")


def cmd_get_chat_members(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="get-chat-members",
    )
    response = im_request(
        method="GET",
        path=f"/im/v1/chats/{args.chat_id}/members",
        token=token,
        query={
            "member_id_type": args.member_id_type,
            "page_size": args.page_size,
            "page_token": args.page_token,
        },
    )
    data = response.get("data") or {}
    result = normalize_result(
        api_alias="im_v1_chatMembers_get",
        auth_mode=auth_mode,
        response=response,
        extra={
            "chat_id": args.chat_id,
            "member_total": len(data.get("items") or []),
        },
    )
    print_result_or_exit(result, command_name="get-chat-members")


def cmd_add_chat_members(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="add-chat-members",
    )
    response = im_request(
        method="POST",
        path=f"/im/v1/chats/{args.chat_id}/members",
        token=token,
        query={"member_id_type": args.member_id_type, "succeed_type": args.succeed_type},
        body={"id_list": args.member_id},
    )
    result = normalize_result(
        api_alias="im_v1_chatMembers_create",
        auth_mode=auth_mode,
        response=response,
        extra={"chat_id": args.chat_id, "member_ids": args.member_id},
    )
    print_result_or_exit(result, command_name="add-chat-members")


def cmd_list_messages(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="list-messages",
    )
    if bool(args.chat_id) == bool(args.thread_id):
        fail("list-messages requires exactly one of --chat-id or --thread-id.")
    container_id = args.chat_id or args.thread_id
    container_type = "chat" if args.chat_id else "thread"
    response = im_request(
        method="GET",
        path="/im/v1/messages",
        token=token,
        query={
            "container_id": container_id,
            "container_id_type": container_type,
            "page_size": args.page_size,
            "page_token": args.page_token,
            "sort_type": args.sort_type,
        },
    )
    item_count = len(((response.get("data") or {}).get("items")) or [])
    result = normalize_result(
        api_alias="im_v1_message_list",
        auth_mode=auth_mode,
        response=response,
        extra={
            "container_id": container_id,
            "container_id_type": container_type,
            "item_count": item_count,
        },
    )
    print_result_or_exit(result, command_name="list-messages")
