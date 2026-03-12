"""Thread/topic lookup handlers for feishu-im-workflow."""

from __future__ import annotations

import argparse

from .common import fail, find_message_in_chat, im_request, normalize_result, print_json, print_result_or_exit, resolve_token


def resolve_thread_id_from_args(args: argparse.Namespace, *, token: str, auth_mode: str) -> tuple[str | None, dict[str, object] | None]:
    if args.thread_id:
        return args.thread_id, None
    if args.topic_message_id and args.chat_id:
        lookup = find_message_in_chat(token=token, chat_id=args.chat_id, message_id=args.topic_message_id, auth_mode=auth_mode)
        if not lookup.get("ok"):
            return None, {"lookup_error": lookup}
        item = lookup["item"]
        return item.get("thread_id"), {"topic_message": item}
    return None, None


def cmd_get_thread(args: argparse.Namespace, *, topic_mode: bool = False) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="get-topic" if topic_mode else "get-thread",
    )
    thread_id, topic_lookup = resolve_thread_id_from_args(args, token=token, auth_mode=auth_mode)
    if not thread_id:
        if topic_lookup and topic_lookup.get("topic_message"):
            print_json(
                {
                    "ok": False,
                    "api_alias": "im_v1_message_list",
                    "auth_mode": auth_mode,
                    "reason": "thread_not_created_yet",
                    "thread_id": None,
                    "topic_message_id": args.topic_message_id,
                    "topic_message": topic_lookup["topic_message"],
                    "thread_note": "topic root message found, but no thread_id exists yet. Publish at least one reply_in_thread message first.",
                }
            )
            raise SystemExit(1)
        fail(
            "get-thread requires --thread-id, or --topic-message-id together with --chat-id.",
            auth_mode=auth_mode,
        )
    response = im_request(
        method="GET",
        path="/im/v1/messages",
        token=token,
        query={
            "container_id": thread_id,
            "container_id_type": "thread",
            "page_size": args.page_size,
            "page_token": args.page_token,
            "sort_type": args.sort_type,
        },
    )
    item_count = len(((response.get("data") or {}).get("items")) or [])
    extra = {
        "thread_id": thread_id,
        "item_count": item_count,
    }
    if args.topic_message_id:
        extra["topic_message_id"] = args.topic_message_id
    if topic_lookup:
        extra["topic_message"] = topic_lookup.get("topic_message")
    result = normalize_result(
        api_alias="im_v1_message_list",
        auth_mode=auth_mode,
        response=response,
        extra=extra,
    )
    print_result_or_exit(result, command_name="get-topic" if topic_mode else "get-thread")
