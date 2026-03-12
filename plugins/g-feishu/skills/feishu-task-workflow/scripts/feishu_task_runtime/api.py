from __future__ import annotations

"""Task v2 HTTP wrappers, token resolution, and response normalization."""

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .common import fail, print_json


# API and identity helpers are separated from the task command handlers so the
# CLI entry stays focused on argument wiring and per-command business rules.
API_BASE = "https://open.feishu.cn/open-apis"
USER_ID_TYPES = {"open_id", "user_id", "union_id"}


def resolve_token(
    *,
    user_access_token: str | None,
    tenant_access_token: str | None,
    use_tenant_token: bool,
    command_name: str,
    allow_tenant: bool = True,
) -> tuple[str, str]:
    if user_access_token:
        return user_access_token, "argument_user_access_token"
    if tenant_access_token:
        return tenant_access_token, "argument_tenant_access_token"
    if use_tenant_token:
        env_tenant = os.environ.get("MY_LARK_TENANT_ACCESS_TOKEN")
        if env_tenant:
            return env_tenant, "environment_MY_LARK_TENANT_ACCESS_TOKEN"
        fail(
            f"{command_name} requested tenant mode, but no tenant token was provided. "
            "Pass --tenant-access-token or set MY_LARK_TENANT_ACCESS_TOKEN."
        )
    env_user = os.environ.get("MY_LARK_USER_ACCESS_TOKEN")
    if env_user:
        return env_user, "environment_MY_LARK_USER_ACCESS_TOKEN"
    if allow_tenant:
        env_tenant = os.environ.get("MY_LARK_TENANT_ACCESS_TOKEN")
        if env_tenant:
            return env_tenant, "environment_MY_LARK_TENANT_ACCESS_TOKEN"
    fail(
        f"{command_name} requires a Feishu token. Pass --user-access-token / --tenant-access-token, "
        "or set MY_LARK_USER_ACCESS_TOKEN / MY_LARK_TENANT_ACCESS_TOKEN. "
        "Use Agent Skill feishu-auth-and-scopes to obtain or refresh a token first."
    )


def task_request(
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


def normalize_api_result(
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
    }
    if extra:
        payload.update(extra)
    payload["ok"] = response.get("code") in (0, None)
    return payload


def ensure_success(result: dict[str, object]) -> None:
    if not result.get("ok"):
        print_json(result)
        raise SystemExit(1)


def parse_member_spec(spec: str) -> tuple[dict[str, str], str]:
    parts = spec.split(":")
    if len(parts) == 3 and parts[0] in USER_ID_TYPES:
        id_type, member_id, role = parts
    elif len(parts) == 2:
        member_id, role = parts
        id_type = "open_id"
    else:
        raise ValueError(
            "Member spec must be 'open_id:ou_xxx:assignee', 'user_id:u_xxx:assignee', or 'ou_xxx:assignee'."
        )
    return {"id": member_id, "type": "user", "role": role}, id_type


def collect_members(args: argparse.Namespace) -> tuple[list[dict[str, str]], str]:
    members: list[dict[str, str]] = []
    id_type = args.user_id_type or "open_id"
    if getattr(args, "member", None):
        for spec in args.member:
            member, parsed_type = parse_member_spec(spec)
            if id_type != parsed_type and members:
                raise ValueError("Mixed user_id_type in --member is not supported.")
            id_type = parsed_type
            members.append(member)
    for open_id in getattr(args, "assignee_open_id", []) or []:
        members.append({"id": open_id, "type": "user", "role": "assignee"})
        id_type = "open_id"
    for open_id in getattr(args, "follower_open_id", []) or []:
        members.append({"id": open_id, "type": "user", "role": "follower"})
        id_type = "open_id"
    return members, id_type


def parse_tasklist_spec(spec: str) -> dict[str, str]:
    if ":" in spec:
        tasklist_guid, section_guid = spec.split(":", 1)
        return {"tasklist_guid": tasklist_guid, "section_guid": section_guid}
    return {"tasklist_guid": spec}


def summarize_task(task: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(task, dict):
        return {}
    return {
        "guid": task.get("guid"),
        "task_id": task.get("task_id"),
        "summary": task.get("summary"),
        "status": task.get("status"),
        "completed_at": task.get("completed_at"),
        "url": task.get("url"),
        "member_count": len(task.get("members", []) or []),
    }


def add_token_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--user-access-token", help="Explicit user access token.")
    parser.add_argument("--tenant-access-token", help="Explicit tenant access token.")
    parser.add_argument("--use-tenant-token", action="store_true", help="Prefer tenant token from argument or environment.")
    parser.add_argument(
        "--user-id-type",
        choices=sorted(USER_ID_TYPES),
        default="open_id",
        help="Feishu user_id_type query parameter. Defaults to open_id.",
    )


def add_member_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--member",
        action="append",
        help="Member spec: open_id:ou_xxx:assignee, user_id:u_xxx:follower, or ou_xxx:assignee.",
    )
    parser.add_argument("--assignee-open-id", action="append", help="Convenience alias for open_id assignee members.")
    parser.add_argument("--follower-open-id", action="append", help="Convenience alias for open_id follower members.")
