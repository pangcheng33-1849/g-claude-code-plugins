#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request

def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def require_user_token(explicit_token: str | None) -> tuple[str, str]:
    if explicit_token:
        return explicit_token, "explicit_user_access_token"
    raise SystemExit(
        "Missing user token. Pass --user-access-token (use skill feishu-auth-and-scopes to obtain)."
    )


def request_json_get(url: str, params: dict[str, object], token: str) -> dict[str, object]:
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} while calling {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error while calling {url}: {exc}") from exc


def request_json_post(url: str, body: dict[str, object], token: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} while calling {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error while calling {url}: {exc}") from exc


def strip_highlight_markup(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"</?h>", "", value)


def cmd_search_user(args: argparse.Namespace) -> None:
    token, auth_mode = require_user_token(args.user_access_token)
    payload = request_json_get(
        "https://open.feishu.cn/open-apis/search/v1/user",
        {
            "query": args.query,
            "offset": args.offset,
            "limit": args.limit,
        },
        token,
    )
    users = payload.get("data", {}).get("users", [])
    normalized = [
        {
            "name": user.get("name"),
            "open_id": user.get("open_id"),
            "user_id": user.get("user_id"),
            "department_ids": user.get("department_ids", []),
            "avatar": (user.get("avatar") or {}).get("avatar_72"),
        }
        for user in users
    ]
    print_json(
        {
            "api_alias": "search_v1_user",
            "auth_mode": auth_mode,
            "query": args.query,
            "offset": args.offset,
            "limit": args.limit,
            "has_more": payload.get("data", {}).get("has_more", False),
            "user_count": len(normalized),
            "users": normalized,
        }
    )


def cmd_search_wiki(args: argparse.Namespace) -> None:
    token, auth_mode = require_user_token(args.user_access_token)
    payload = request_json_post(
        "https://open.feishu.cn/open-apis/wiki/v1/nodes/search",
        {
            "query": args.query,
            "space_id": args.space_id,
            "node_id": args.node_id,
            "page_size": args.page_size,
            "page_token": args.page_token,
        },
        token,
    )
    data = payload.get("data", {})
    items = data.get("items", [])
    normalized = [
        {
            "node_id": item.get("node_id"),
            "obj_token": item.get("obj_token"),
            "obj_type": item.get("obj_type"),
            "space_id": item.get("space_id"),
            "parent_id": item.get("parent_id"),
            "title": item.get("title"),
            "url": item.get("url"),
        }
        for item in items
    ]
    print_json(
        {
            "api_alias": "wiki_v1_node_search",
            "auth_mode": auth_mode,
            "query": args.query,
            "space_id": args.space_id,
            "node_id": args.node_id,
            "has_more": data.get("has_more", False),
            "page_token": data.get("page_token") or "",
            "item_count": len(normalized),
            "items": normalized,
        }
    )


def cmd_search_chat(args: argparse.Namespace) -> None:
    token, auth_mode = require_user_token(args.user_access_token)
    payload = request_json_get(
        "https://open.feishu.cn/open-apis/im/v1/chats/search",
        {
            "query": args.query,
            "page_size": args.page_size,
            "page_token": args.page_token,
            "user_id_type": args.user_id_type,
        },
        token,
    )
    data = payload.get("data", {})
    items = data.get("items", [])
    normalized = [
        {
            "chat_id": item.get("chat_id"),
            "name": item.get("name"),
            "description": item.get("description"),
            "owner_id": item.get("owner_id"),
            "owner_id_type": item.get("owner_id_type"),
            "tenant_key": item.get("tenant_key"),
            "chat_status": item.get("chat_status"),
            "external": item.get("external"),
        }
        for item in items
    ]
    print_json(
        {
            "api_alias": "im_v1_chat_search",
            "auth_mode": auth_mode,
            "query": args.query,
            "has_more": data.get("has_more", False),
            "page_token": data.get("page_token") or "",
            "item_count": len(normalized),
            "items": normalized,
        }
    )


def cmd_search_message(args: argparse.Namespace) -> None:
    token, auth_mode = require_user_token(args.user_access_token)
    body: dict[str, object] = {"query": args.query}
    if args.chat_id:
        body["chat_ids"] = args.chat_id
    if args.from_id:
        body["from_ids"] = args.from_id
    if args.at_chatter_id:
        body["at_chatter_ids"] = args.at_chatter_id
    if args.message_type is not None:
        body["message_type"] = args.message_type
    if args.from_type is not None:
        body["from_type"] = args.from_type
    if args.chat_type is not None:
        body["chat_type"] = args.chat_type
    if args.start_time is not None:
        body["start_time"] = args.start_time
    if args.end_time is not None:
        body["end_time"] = args.end_time
    query_params: dict[str, object] = {
        "page_size": args.page_size,
        "user_id_type": "open_id",
    }
    if args.page_token is not None:
        query_params["page_token"] = args.page_token
    qs = urllib.parse.urlencode({k: v for k, v in query_params.items() if v is not None})
    url = f"https://open.feishu.cn/open-apis/search/v2/message?{qs}"
    payload = request_json_post(url, body, token)
    data = payload.get("data", {})
    items = data.get("items", [])
    print_json(
        {
            "api_alias": "search_v2_message",
            "auth_mode": auth_mode,
            "query": args.query,
            "has_more": data.get("has_more", False),
            "page_token": data.get("page_token") or "",
            "item_count": len(items),
            "items": items,
        }
    )


def cmd_search_doc(args: argparse.Namespace) -> None:
    token, auth_mode = require_user_token(args.user_access_token)
    payload = request_json_post(
        "https://open.feishu.cn/open-apis/search/v2/doc_wiki/search",
        {
            "query": args.query,
            "page_size": args.page_size,
            "page_token": args.page_token,
            "doc_filter": {},
            "wiki_filter": {},
        },
        token,
    )
    data = payload.get("data", {})
    units = data.get("res_units", [])
    doc_units = [unit for unit in units if unit.get("entity_type") == "DOC"]
    normalized = [
        {
            "entity_type": unit.get("entity_type"),
            "title": strip_highlight_markup(unit.get("title_highlighted")),
            "summary": strip_highlight_markup(unit.get("summary_highlighted")),
            "token": (unit.get("result_meta") or {}).get("token"),
            "doc_types": (unit.get("result_meta") or {}).get("doc_types"),
            "owner_id": (unit.get("result_meta") or {}).get("owner_id"),
            "owner_name": (unit.get("result_meta") or {}).get("owner_name"),
            "edit_user_id": (unit.get("result_meta") or {}).get("edit_user_id"),
            "edit_user_name": (unit.get("result_meta") or {}).get("edit_user_name"),
            "url": (unit.get("result_meta") or {}).get("url"),
            "create_time": (unit.get("result_meta") or {}).get("create_time"),
            "update_time": (unit.get("result_meta") or {}).get("update_time"),
            "last_open_time": (unit.get("result_meta") or {}).get("last_open_time"),
        }
        for unit in doc_units
    ]
    print_json(
        {
            "api_alias": "search_v2_doc_wiki_search",
            "auth_mode": auth_mode,
            "query": args.query,
            "has_more": data.get("has_more", False),
            "page_token": data.get("page_token") or "",
            "raw_total": data.get("total", 0),
            "raw_result_count": len(units),
            "doc_count": len(normalized),
            "docs": normalized,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Standalone Feishu search and locate helper. Supports direct search "
            "commands for users, docs, wiki nodes, and chats."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_user = subparsers.add_parser("search-user", help="Search users by name or email via search/v1/user.")
    search_user.add_argument("--query", required=True)
    search_user.add_argument("--offset", type=int, default=0)
    search_user.add_argument("--limit", type=int, default=10)
    search_user.add_argument("--user-access-token", required=True, help="Use skill feishu-auth-and-scopes to obtain.")
    search_user.set_defaults(func=cmd_search_user)

    search_wiki = subparsers.add_parser(
        "search-wiki",
        help="Search wiki nodes via wiki/v1/nodes/search.",
        description="Search wiki nodes by keyword and optionally narrow by space_id or node_id.",
    )
    search_wiki.add_argument("--query", required=True)
    search_wiki.add_argument("--space-id")
    search_wiki.add_argument("--node-id")
    search_wiki.add_argument("--page-size", type=int, default=10)
    search_wiki.add_argument("--page-token")
    search_wiki.add_argument("--user-access-token", required=True, help="Use skill feishu-auth-and-scopes to obtain.")
    search_wiki.set_defaults(func=cmd_search_wiki)

    search_chat = subparsers.add_parser(
        "search-chat",
        help="Search chats via im/v1/chats/search.",
        description="Search chats by keyword and return normalized chat metadata.",
    )
    search_chat.add_argument("--query", required=True)
    search_chat.add_argument("--page-size", type=int, default=10)
    search_chat.add_argument("--page-token")
    search_chat.add_argument("--user-id-type", default="open_id")
    search_chat.add_argument("--user-access-token", required=True, help="Use skill feishu-auth-and-scopes to obtain.")
    search_chat.set_defaults(func=cmd_search_chat)

    search_doc = subparsers.add_parser(
        "search-doc",
        help="Search docs via search/v2/doc_wiki/search and filter DOC results.",
        description="Search docs by keyword, normalize doc results, and exclude non-DOC entities from the final output.",
    )
    search_doc.add_argument("--query", required=True)
    search_doc.add_argument("--page-size", type=int, default=10)
    search_doc.add_argument("--page-token")
    search_doc.add_argument("--user-access-token", required=True, help="Use skill feishu-auth-and-scopes to obtain.")
    search_doc.set_defaults(func=cmd_search_doc)

    search_message = subparsers.add_parser(
        "search-message",
        help="Search messages via search/v2/message.",
        description="Search messages by keyword with optional filters for chat, sender, message type, and time range.",
    )
    search_message.add_argument("--query", required=True)
    search_message.add_argument("--chat-id", action="append", help="Chat ID to filter; repeatable.")
    search_message.add_argument("--from-id", action="append", help="Sender open_id to filter; repeatable.")
    search_message.add_argument("--at-chatter-id", action="append", help="At-mentioned open_id to filter; repeatable.")
    search_message.add_argument("--message-type", choices=["file", "image", "media"])
    search_message.add_argument("--from-type", choices=["bot", "user"])
    search_message.add_argument("--chat-type", choices=["group_chat", "p2p_chat"])
    search_message.add_argument("--start-time", help="Unix seconds string, inclusive lower bound.")
    search_message.add_argument("--end-time", help="Unix seconds string, inclusive upper bound.")
    search_message.add_argument("--page-size", type=int, default=20)
    search_message.add_argument("--page-token")
    search_message.add_argument("--user-access-token", required=True, help="Use skill feishu-auth-and-scopes to obtain.")
    search_message.set_defaults(func=cmd_search_message)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
