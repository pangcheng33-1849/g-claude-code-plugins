"""Message CRUD command handlers for feishu-im-workflow."""

from __future__ import annotations

import argparse

from .common import (
    build_message_payload,
    im_request,
    maybe_uuid,
    normalize_result,
    print_result_or_exit,
    resolve_token,
)


def cmd_send_message(args: argparse.Namespace, *, topic_mode: bool = False) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="publish-topic" if topic_mode else "send-message",
    )
    msg_type, content = build_message_payload(args)
    response = im_request(
        method="POST",
        path="/im/v1/messages",
        token=token,
        query={"receive_id_type": args.receive_id_type},
        body={
            "receive_id": args.receive_id,
            "msg_type": msg_type,
            "content": content,
            "uuid": maybe_uuid(args.uuid),
        },
    )
    data = response.get("data") or {}
    extra = {
        "receive_id": args.receive_id,
        "receive_id_type": args.receive_id_type,
        "message_id": data.get("message_id"),
    }
    if topic_mode:
        extra["topic_message_id"] = data.get("message_id")
        extra["topic_note"] = "发布话题本质上是向 chat 发送一条根消息；thread_id 可能在首次 thread 回复后出现。"
    result = normalize_result(
        api_alias="im_v1_message_create",
        auth_mode=auth_mode,
        response=response,
        extra=extra,
    )
    print_result_or_exit(result, command_name="publish-topic" if topic_mode else "send-message")


def cmd_reply_message(args: argparse.Namespace, *, topic_mode: bool = False) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="reply-topic" if topic_mode else "reply-message",
    )
    msg_type, content = build_message_payload(args)
    reply_in_thread = getattr(args, "reply_in_thread", False) or topic_mode
    response = im_request(
        method="POST",
        path=f"/im/v1/messages/{args.message_id}/reply",
        token=token,
        body={
            "msg_type": msg_type,
            "content": content,
            "uuid": maybe_uuid(args.uuid),
            "reply_in_thread": reply_in_thread,
        },
    )
    data = response.get("data") or {}
    extra = {
        "message_id": data.get("message_id"),
        "parent_id": data.get("parent_id"),
        "root_id": data.get("root_id"),
        "thread_id": data.get("thread_id"),
    }
    if topic_mode:
        extra["topic_message_id"] = args.message_id
    result = normalize_result(
        api_alias="im_v1_message_reply",
        auth_mode=auth_mode,
        response=response,
        extra=extra,
    )
    print_result_or_exit(result, command_name="reply-topic" if topic_mode else "reply-message")


def cmd_edit_message(args: argparse.Namespace, *, topic_mode: bool = False) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="edit-topic" if topic_mode else "edit-message",
    )
    msg_type, content = build_message_payload(args)
    response = im_request(
        method="PUT",
        path=f"/im/v1/messages/{args.message_id}",
        token=token,
        body={"msg_type": msg_type, "content": content},
    )
    data = response.get("data") or {}
    extra = {"message_id": data.get("message_id") or args.message_id}
    if topic_mode:
        extra["topic_message_id"] = args.message_id
    result = normalize_result(
        api_alias="im_v1_message_update",
        auth_mode=auth_mode,
        response=response,
        extra=extra,
    )
    print_result_or_exit(result, command_name="edit-topic" if topic_mode else "edit-message")


def cmd_recall_message(args: argparse.Namespace, *, topic_mode: bool = False) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="recall-topic" if topic_mode else "recall-message",
    )
    response = im_request(
        method="DELETE",
        path=f"/im/v1/messages/{args.message_id}",
        token=token,
    )
    extra = {"message_id": args.message_id}
    if topic_mode:
        extra["topic_message_id"] = args.message_id
    result = normalize_result(
        api_alias="im_v1_message_delete",
        auth_mode=auth_mode,
        response=response,
        extra=extra,
    )
    print_result_or_exit(result, command_name="recall-topic" if topic_mode else "recall-message")

