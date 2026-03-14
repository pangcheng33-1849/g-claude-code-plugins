#!/usr/bin/env python3
from __future__ import annotations

"""CLI entrypoint and parser wiring for the Feishu IM workflow helper."""

import argparse
from feishu_im_runtime.chat_ops import (
    cmd_add_chat_members,
    cmd_create_chat,
    cmd_get_chat,
    cmd_get_chat_members,
    cmd_list_messages,
)
from feishu_im_runtime.common import (
    add_message_content_args,
    add_token_args,
)
from feishu_im_runtime.media_ops import (
    cmd_upload_file,
    cmd_upload_image,
)
from feishu_im_runtime.message_ops import (
    cmd_edit_message,
    cmd_recall_message,
    cmd_reply_message,
    cmd_send_message,
)
from feishu_im_runtime.reaction_ops import (
    cmd_add_reaction,
    cmd_list_reaction_emojis,
    cmd_list_reactions,
    cmd_remove_reaction,
)
from feishu_im_runtime.thread_ops import cmd_get_thread


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Standalone Feishu IM helper. Supports real chat creation, message CRUD, "
            "thread/topic reads, reactions, and chat member operations."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_chat = subparsers.add_parser(
        "create-chat",
        help="Create a new ordinary message group chat.",
        description=(
            "Create a new ordinary message group chat with tenant token only. "
            "Use --member-id repeatedly to seed initial members, or create the group first "
            "and then call add-chat-members."
        ),
    )
    create_chat.add_argument("--name", required=True, help="Chat name.")
    create_chat.add_argument("--description", help="Optional chat description.")
    create_chat.add_argument("--owner-id", help="Optional designated owner identifier under --user-id-type.")
    create_chat.add_argument(
        "--member-id",
        action="append",
        help="Initial member identifier under --user-id-type. Repeat the flag to add multiple members.",
    )
    create_chat.add_argument(
        "--bot-id",
        action="append",
        help="Optional bot app_id values to include at creation time. Repeat the flag to add multiple bots.",
    )
    create_chat.add_argument("--avatar", help="Optional chat avatar key.")
    create_chat.add_argument("--user-id-type", default="open_id", choices=["open_id", "user_id", "union_id"])
    create_chat.add_argument("--set-bot-manager", action="store_true", help="Set the bot as a group manager when supported.")
    create_chat.add_argument("--uuid", help="Optional idempotency key. Defaults to a generated g-feishu-im UUID.")
    add_token_args(create_chat)
    create_chat.set_defaults(func=cmd_create_chat)

    get_chat = subparsers.add_parser("get-chat", help="Read chat metadata by chat_id.")
    get_chat.add_argument("--chat-id", required=True)
    get_chat.add_argument("--user-id-type", default="open_id")
    add_token_args(get_chat)
    get_chat.set_defaults(func=cmd_get_chat)

    get_members = subparsers.add_parser("get-chat-members", help="List chat members.")
    get_members.add_argument("--chat-id", required=True)
    get_members.add_argument("--member-id-type", default="open_id")
    get_members.add_argument("--page-size", type=int, default=50)
    get_members.add_argument("--page-token")
    add_token_args(get_members)
    get_members.set_defaults(func=cmd_get_chat_members)

    add_members = subparsers.add_parser("add-chat-members", help="Add members into a chat.")
    add_members.add_argument("--chat-id", required=True)
    add_members.add_argument("--member-id-type", default="open_id")
    add_members.add_argument("--succeed-type", type=int, default=0)
    add_members.add_argument("--member-id", action="append", required=True, help="Member identifier. Repeat the flag to add multiple members.")
    add_token_args(add_members)
    add_members.set_defaults(func=cmd_add_chat_members)

    list_messages = subparsers.add_parser("list-messages", help="List chat or thread messages.")
    list_messages.add_argument("--chat-id")
    list_messages.add_argument("--thread-id")
    list_messages.add_argument("--page-size", type=int, default=20)
    list_messages.add_argument("--page-token")
    list_messages.add_argument("--sort-type", default="ByCreateTimeDesc", choices=["ByCreateTimeAsc", "ByCreateTimeDesc"])
    add_token_args(list_messages)
    list_messages.set_defaults(func=cmd_list_messages)

    send_message = subparsers.add_parser(
        "send-message",
        help="Send a root message to a user or chat. For non-casual or formal long messages, prefer interactive first; use post only when card layout is unnecessary.",
    )
    send_message.add_argument("--receive-id", required=True)
    send_message.add_argument("--receive-id-type", default="chat_id", choices=["chat_id", "open_id", "user_id", "union_id", "email"])
    send_message.add_argument("--uuid")
    add_message_content_args(send_message)
    add_token_args(send_message)
    send_message.set_defaults(func=cmd_send_message)

    publish_topic = subparsers.add_parser(
        "publish-topic",
        help="Publish a topic root message to a chat. For non-casual or formal long topic bodies, prefer interactive first; use post only when card layout is unnecessary.",
    )
    publish_topic.add_argument("--receive-id", required=True, help="Target chat_id.")
    publish_topic.add_argument("--receive-id-type", default="chat_id", choices=["chat_id"])
    publish_topic.add_argument("--uuid")
    add_message_content_args(publish_topic)
    add_token_args(publish_topic)
    publish_topic.set_defaults(func=lambda args: cmd_send_message(args, topic_mode=True))

    reply_message = subparsers.add_parser(
        "reply-message",
        help="Reply to a specific message. For non-casual or formal long replies, prefer interactive first; use post only when card layout is unnecessary.",
    )
    reply_message.add_argument("--message-id", required=True)
    reply_message.add_argument("--reply-in-thread", action="store_true", help="Reply in thread mode when supported.")
    reply_message.add_argument("--uuid")
    add_message_content_args(reply_message)
    add_token_args(reply_message)
    reply_message.set_defaults(func=cmd_reply_message)

    reply_topic = subparsers.add_parser(
        "reply-topic",
        help="Reply to a topic root message in thread mode. For non-casual or formal long replies, prefer interactive first; use post only when card layout is unnecessary.",
    )
    reply_topic.add_argument("--message-id", required=True, help="Topic root message_id.")
    reply_topic.add_argument("--uuid")
    add_message_content_args(reply_topic)
    add_token_args(reply_topic)
    reply_topic.set_defaults(func=lambda args: cmd_reply_message(args, topic_mode=True))

    edit_message = subparsers.add_parser(
        "edit-message",
        help="Edit an existing message. For non-casual or formal long bodies, prefer interactive first; use post only when card layout is unnecessary.",
    )
    edit_message.add_argument("--message-id", required=True)
    add_message_content_args(edit_message)
    add_token_args(edit_message)
    edit_message.set_defaults(func=cmd_edit_message)

    edit_topic = subparsers.add_parser(
        "edit-topic",
        help="Edit a topic root message. For non-casual or formal long topic bodies, prefer interactive first; use post only when card layout is unnecessary.",
    )
    edit_topic.add_argument("--message-id", required=True, help="Topic root message_id.")
    add_message_content_args(edit_topic)
    add_token_args(edit_topic)
    edit_topic.set_defaults(func=lambda args: cmd_edit_message(args, topic_mode=True))

    recall_message = subparsers.add_parser("recall-message", help="Recall a message.")
    recall_message.add_argument("--message-id", required=True)
    add_token_args(recall_message)
    recall_message.set_defaults(func=cmd_recall_message)

    recall_topic = subparsers.add_parser("recall-topic", help="Recall a topic root message.")
    recall_topic.add_argument("--message-id", required=True, help="Topic root message_id.")
    add_token_args(recall_topic)
    recall_topic.set_defaults(func=lambda args: cmd_recall_message(args, topic_mode=True))

    get_thread = subparsers.add_parser("get-thread", help="Read a thread by thread_id, or by topic_message_id + chat_id.")
    get_thread.add_argument("--thread-id")
    get_thread.add_argument("--topic-message-id")
    get_thread.add_argument("--chat-id", help="Required when resolving thread_id from topic_message_id.")
    get_thread.add_argument("--page-size", type=int, default=20)
    get_thread.add_argument("--page-token")
    get_thread.add_argument("--sort-type", default="ByCreateTimeAsc", choices=["ByCreateTimeAsc", "ByCreateTimeDesc"])
    add_token_args(get_thread)
    get_thread.set_defaults(func=cmd_get_thread)

    get_topic = subparsers.add_parser("get-topic", help="Alias of get-thread for topic-oriented workflows.")
    get_topic.add_argument("--thread-id")
    get_topic.add_argument("--topic-message-id")
    get_topic.add_argument("--chat-id", help="Required when resolving thread_id from topic_message_id.")
    get_topic.add_argument("--page-size", type=int, default=20)
    get_topic.add_argument("--page-token")
    get_topic.add_argument("--sort-type", default="ByCreateTimeAsc", choices=["ByCreateTimeAsc", "ByCreateTimeDesc"])
    add_token_args(get_topic)
    get_topic.set_defaults(func=lambda args: cmd_get_thread(args, topic_mode=True))

    add_reaction = subparsers.add_parser("add-reaction", help="Add a reaction to a message.")
    add_reaction.add_argument("--message-id", required=True)
    add_reaction.add_argument("--emoji-type", required=True, help="Reaction emoji_type, for example SMILE.")
    add_token_args(add_reaction)
    add_reaction.set_defaults(func=cmd_add_reaction)

    list_reactions = subparsers.add_parser("list-reactions", help="List reactions on a message.")
    list_reactions.add_argument("--message-id", required=True)
    list_reactions.add_argument("--emoji-type", help="Optional emoji_type filter.")
    list_reactions.add_argument("--page-size", type=int, default=20)
    list_reactions.add_argument("--page-token")
    add_token_args(list_reactions)
    list_reactions.set_defaults(func=cmd_list_reactions)

    remove_reaction = subparsers.add_parser("remove-reaction", help="Remove a reaction by reaction_id.")
    remove_reaction.add_argument("--message-id", required=True)
    remove_reaction.add_argument("--reaction-id", required=True)
    add_token_args(remove_reaction)
    remove_reaction.set_defaults(func=cmd_remove_reaction)

    list_emojis = subparsers.add_parser(
        "list-reaction-emojis",
        help="List a built-in reaction emoji reference set, with lively positive emoji_types first.",
    )
    list_emojis.set_defaults(func=cmd_list_reaction_emojis)

    upload_image = subparsers.add_parser(
        "upload-image",
        help=(
            "Upload a local image to Feishu and get an image_key. "
            "Supports JPG, JPEG, PNG, WEBP, GIF, BMP, ICO, TIFF, HEIC. Max 10 MB. "
            "Use the returned image_key with send-message --msg-type image."
        ),
        description=(
            "Upload a local image file to Feishu open platform via multipart/form-data. "
            "Returns image_key for use in send-message --msg-type image. "
            "Required scope: im:resource or im:resource:upload."
        ),
    )
    upload_image.add_argument(
        "--file-path",
        required=True,
        help="Local path to the image file.",
    )
    upload_image.add_argument(
        "--image-type",
        default="message",
        choices=["message", "avatar"],
        help='Image usage type. "message" for sending in chat (default), "avatar" for profile pictures.',
    )
    add_token_args(upload_image)
    upload_image.set_defaults(func=cmd_upload_image)

    upload_file = subparsers.add_parser(
        "upload-file",
        help=(
            "Upload a local file to Feishu and get a file_key. "
            "Supports opus, mp4, pdf, doc, xls, ppt, stream. Max 30 MB. "
            "Use the returned file_key with send-message --msg-type file."
        ),
        description=(
            "Upload a local file to Feishu open platform via multipart/form-data. "
            "Returns file_key for use in send-message --msg-type file. "
            "Required scope: im:resource or im:resource:upload."
        ),
    )
    upload_file.add_argument(
        "--file-path",
        required=True,
        help="Local path to the file.",
    )
    upload_file.add_argument(
        "--file-type",
        required=True,
        choices=["opus", "mp4", "pdf", "doc", "xls", "ppt", "stream"],
        help=(
            "File type. Use 'stream' for generic files not matching other types. "
            "Audio must be converted to opus format before uploading."
        ),
    )
    upload_file.add_argument(
        "--file-name",
        help="Display filename with extension. Defaults to the local filename.",
    )
    upload_file.add_argument(
        "--duration",
        type=int,
        help="Duration in milliseconds for audio/video files. Omitting this hides the duration display.",
    )
    add_token_args(upload_file)
    upload_file.set_defaults(func=cmd_upload_file)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
