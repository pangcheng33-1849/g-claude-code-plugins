"""Shared helpers for Feishu IM API commands.

This module holds token resolution, HTTP requests, and message payload helpers
used by multiple IM command groups. Keeping them here lets the entry script stay
small while preserving the original CLI contract.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request
import uuid


API_BASE = "https://open.feishu.cn/open-apis"
REACTION_EMOJIS = [
    "THUMBSUP",
    "THANKS",
    "APPLAUSE",
    "MUSCLE",
    "FINGERHEART",
    "FISTBUMP",
    "JIAYI",
    "DONE",
    "SMILE",
    "BLUSH",
    "LAUGH",
    "LOVE",
    "PARTY",
    "GoGoGo",
    "ThanksFace",
    "SaluteFace",
    "HappyDragon",
    "HEART",
    "Trophy",
    "Fire",
    "OK",
    "CheckMark",
    "Yes",
    "Pin",
    "Alarm",
    "Loudspeaker",
    "LOL",
    "SMIRK",
    "WINK",
    "PROUD",
    "WITTY",
    "SMART",
    "THINKING",
    "ROSE",
    "GIFT",
    "FORTUNE",
    "LUCK",
    "BeamingFace",
    "Delighted",
    "Partying",
    "Shrug",
    "ClownFace",
    "FACEPALM",
    "SCOWL",
    "SOB",
    "CRY",
    "ERROR",
    "HEARTBROKEN",
    "POOP",
    "No",
    "CrossMark",
    "BOMB",
    "ColdSweat",
    "NOSEPICK",
    "HAUGHTY",
    "Hundred",
    "AWESOMEN",
    "REDPACKET",
    "GeneralDoNotDisturb",
    "Status_PrivateMessage",
    "GeneralInMeetingBusy",
    "StatusReading",
    "StatusInFlight",
    "GeneralBusinessTrip",
    "GeneralWorkFromHome",
    "SAD",
]


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def fail(
    message: str,
    *,
    api_alias: str | None = None,
    auth_mode: str | None = None,
    response: object | None = None,
    hints: list[str] | None = None,
) -> None:
    payload: dict[str, object] = {"error": message}
    if api_alias:
        payload["api_alias"] = api_alias
    if auth_mode:
        payload["auth_mode"] = auth_mode
    if response is not None:
        payload["response"] = response
    if hints:
        payload["permission_hints"] = hints
    print_json(payload)
    raise SystemExit(1)


def load_content_json(inline_json: str | None, file_path: str | None) -> dict[str, object]:
    if file_path:
        return json.loads(pathlib.Path(file_path).read_text(encoding="utf-8"))
    if inline_json:
        return json.loads(inline_json)
    raise ValueError("content_json or content_file is required for non-text messages.")


def resolve_token(
    *,
    tenant_access_token: str | None,
    command_name: str,
) -> tuple[str, str]:
    if tenant_access_token:
        return tenant_access_token, "argument_tenant_access_token"
    env_tenant = os.environ.get("MY_LARK_TENANT_ACCESS_TOKEN")
    if env_tenant:
        return env_tenant, "environment_MY_LARK_TENANT_ACCESS_TOKEN"
    fail(
        f"{command_name} requires a tenant token. Pass --tenant-access-token, "
        "or set MY_LARK_TENANT_ACCESS_TOKEN. "
        "Use Agent Skill feishu-auth-and-scopes to obtain or refresh a tenant token first."
    )


def im_request(
    *,
    method: str,
    path: str,
    token: str,
    query: dict[str, object] | None = None,
    body: dict[str, object] | None = None,
) -> dict[str, object]:
    url = f"{API_BASE}{path}"
    if query:
        filtered = {k: v for k, v in query.items() if v is not None}
        if filtered:
            url = f"{url}?{urllib.parse.urlencode(filtered, doseq=True)}"
    payload = None
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"code": error.code, "msg": raw, "http_status": error.code}


def permission_hints(response: dict[str, object], *, command_name: str, auth_mode: str) -> list[str]:
    code = response.get("code")
    message = str(response.get("msg") or "")
    hints: list[str] = []
    if code == 99991672 and any(scope in message for scope in ("im:chat:create", "im:chat:create_by_user")):
        hints.append("当前 tenant token 缺少建群权限。请为应用开通 im:chat、im:chat:create 或 im:chat:create_by_user 后重新获取 tenant token。")
    if code == 99991679 and "im:chat.members:write_only" in message:
        hints.append("当前 tenant token 缺少 im:chat.members:write_only。请补齐应用 scope 后重新获取 tenant token。")
    if code == 99991672 and ("im:chat" in message or "im:chat.members:write_only" in message):
        hints.append("当前 tenant token 缺少群聊或成员写权限。请为应用开通 im:chat 或 im:chat.members:write_only 后重试。")
    if code == 230002:
        hints.append("当前应用身份不在目标 chat 中，无法读取该群消息。请先确认 bot 已加入目标 chat。")
    if code == 230001 and "invalid container_id" in message:
        hints.append("thread 读取需要真实 thread_id（通常形如 omt_xxx）。如果只有 topic 根消息，请先通过回复话题或消息列表获取 thread_id。")
    if code == 230017:
        hints.append("消息可能已经被撤回或不存在。请先重新获取 message_id。")
    return hints


def normalize_result(
    *,
    api_alias: str,
    auth_mode: str,
    response: dict[str, object],
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "api_alias": api_alias,
        "auth_mode": auth_mode,
        "response": response,
        "ok": response.get("code") in (0, None),
    }
    if extra:
        payload.update(extra)
    return payload


def print_result_or_exit(result: dict[str, object], *, command_name: str) -> None:
    if not result.get("ok"):
        response = result.get("response")
        hints = permission_hints(response if isinstance(response, dict) else {}, command_name=command_name, auth_mode=str(result.get("auth_mode") or ""))
        if hints:
            result["permission_hints"] = hints
        print_json(result)
        raise SystemExit(1)
    print_json(result)


def build_message_payload(args: argparse.Namespace) -> tuple[str, str]:
    if args.text is not None:
        return "text", json.dumps({"text": args.text}, ensure_ascii=False)
    msg_type = args.msg_type
    content = load_content_json(args.content_json, args.content_file)
    return msg_type, json.dumps(content, ensure_ascii=False)


def maybe_uuid(value: str | None) -> str:
    return value or f"codex-im-{uuid.uuid4()}"


def find_message_in_chat(*, token: str, chat_id: str, message_id: str, auth_mode: str) -> dict[str, object]:
    page_token = ""
    for _ in range(5):
        response = im_request(
            method="GET",
            path="/im/v1/messages",
            token=token,
            query={
                "container_id": chat_id,
                "container_id_type": "chat",
                "page_size": 50,
                "page_token": page_token or None,
                "sort_type": "ByCreateTimeDesc",
            },
        )
        result = normalize_result(api_alias="im_v1_message_list", auth_mode=auth_mode, response=response)
        if not result["ok"]:
            return result
        items = (((response.get("data") or {}).get("items")) or [])
        for item in items:
            if item.get("message_id") == message_id:
                return {"ok": True, "item": item}
        page_token = ((response.get("data") or {}).get("page_token")) or ""
        if not ((response.get("data") or {}).get("has_more")):
            break
    return {"ok": False, "error": "message_not_found_in_chat_scan"}


def add_token_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tenant-access-token", help="Explicit tenant_access_token.")


def add_message_content_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--text", help="Convenience shortcut for text messages.")
    parser.add_argument(
        "--msg-type",
        default="text",
        help="Message type for non-text messages. Common choices: text, post, interactive. For non-casual or formal long messages, prefer interactive first; use post only when card layout is unnecessary. Defaults to text.",
    )
    parser.add_argument(
        "--content-json",
        help="Inline JSON content for non-text messages. Suitable for short post/interactive payloads.",
    )
    parser.add_argument(
        "--content-file",
        help="Path to a JSON file for non-text messages. Recommended for interactive card JSON and long post payloads.",
    )

