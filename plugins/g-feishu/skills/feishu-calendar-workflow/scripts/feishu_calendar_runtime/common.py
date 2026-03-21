"""Shared helpers for token resolution, HTTP requests, and time parsing."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo


API_BASE = "https://open.feishu.cn/open-apis"
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def fail(message: str, *, api_alias: str | None = None, auth_mode: str | None = None, response: object | None = None) -> None:
    payload: dict[str, object] = {"error": message}
    if api_alias:
        payload["api_alias"] = api_alias
    if auth_mode:
        payload["auth_mode"] = auth_mode
    if response is not None:
        payload["response"] = response
    print_json(payload)
    raise SystemExit(1)


def load_json_value(inline_json: str | None, file_path: str | None) -> dict[str, object]:
    if file_path:
        return json.loads(pathlib.Path(file_path).read_text(encoding="utf-8"))
    if inline_json:
        return json.loads(inline_json)
    return {}


def parse_time_expression(value: str, timezone_name: str) -> dt.datetime:
    tz = ZoneInfo(timezone_name)
    candidate = value.strip()
    if candidate.endswith("Z"):
        return dt.datetime.fromisoformat(candidate.replace("Z", "+00:00")).astimezone(tz)
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = dt.datetime.strptime(candidate, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=tz)
            return parsed.astimezone(tz)
        except ValueError:
            continue
    lowered = candidate.lower()
    today = dt.datetime.now(tz)
    simple_relative = re.match(r"^(today|tomorrow)(?:\s+(\d{1,2}:\d{2}))?$", lowered)
    if simple_relative:
        day_word, time_part = simple_relative.groups()
        base = today if day_word == "today" else today + dt.timedelta(days=1)
        hour, minute = (9, 0)
        if time_part:
            hour, minute = [int(part) for part in time_part.split(":", 1)]
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    weekday_relative = re.match(r"^next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+(\d{1,2}:\d{2}))?$", lowered)
    if weekday_relative:
        weekday_word, time_part = weekday_relative.groups()
        target = WEEKDAYS[weekday_word]
        delta = target - today.weekday()
        if delta <= 0:
            delta += 7
        base = today + dt.timedelta(days=delta)
        hour, minute = (9, 0)
        if time_part:
            hour, minute = [int(part) for part in time_part.split(":", 1)]
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    raise ValueError(f"Unsupported time expression: {value}")


def time_payload(value: dt.datetime, timezone_name: str) -> dict[str, str]:
    return {
        "timestamp": str(int(value.timestamp())),
        "timezone": timezone_name,
    }


def utc_rfc3339(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_token(
    *,
    user_access_token: str | None,
    tenant_access_token: str | None,
    use_tenant_token: bool,
    command_name: str,
    prefer_tenant: bool = False,
) -> tuple[str, str]:
    if prefer_tenant:
        if tenant_access_token:
            return tenant_access_token, "argument_tenant_access_token"
        if user_access_token:
            return user_access_token, "argument_user_access_token"
    else:
        if user_access_token:
            return user_access_token, "argument_user_access_token"
        if tenant_access_token:
            return tenant_access_token, "argument_tenant_access_token"
    if use_tenant_token:
        if tenant_access_token:
            return tenant_access_token, "argument_tenant_access_token"
        fail(
            f"{command_name} requested tenant mode, but no tenant token was provided. "
            "Pass --tenant-access-token explicitly. "
            "Use skill feishu-auth-and-scopes resolve-token to obtain one first."
        )
    fail(
        f"{command_name} requires a Feishu token. Pass --user-access-token or --tenant-access-token. "
        "Use skill feishu-auth-and-scopes resolve-token to obtain a token first."
    )


def calendar_request(
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
            return {"code": error.code, "msg": raw}


def search_users_by_query(*, token: str, query: str) -> list[dict[str, object]]:
    request = urllib.request.Request(
        f"{API_BASE}/search/v1/user?{urllib.parse.urlencode({'query': query, 'offset': 0, 'limit': 10})}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"code": error.code, "msg": raw}
    if payload.get("code") != 0:
        return []
    return payload.get("data", {}).get("users", [])


def ensure_success(response: dict[str, object], *, api_alias: str, auth_mode: str) -> None:
    if response.get("code") == 0:
        return
    fail(
        f"{api_alias} failed: {response.get('msg') or response.get('message') or 'unknown error'}",
        api_alias=api_alias,
        auth_mode=auth_mode,
        response=response,
    )


def list_calendars_raw(*, token: str, auth_mode: str, page_size: int = 50, page_token: str | None = None) -> list[dict[str, object]]:
    response = calendar_request(
        method="GET",
        path="/calendar/v4/calendars",
        token=token,
        query={"page_size": page_size, "page_token": page_token},
    )
    ensure_success(response, api_alias="calendar_v4_calendars_list", auth_mode=auth_mode)
    return response.get("data", {}).get("calendar_list", [])


def resolve_primary_calendar(*, token: str, auth_mode: str) -> dict[str, object]:
    calendars = list_calendars_raw(token=token, auth_mode=auth_mode)
    for item in calendars:
        if item.get("type") == "primary":
            return item
    if calendars:
        return calendars[0]
    fail("No calendars visible to the current identity.", api_alias="calendar_v4_calendars_list", auth_mode=auth_mode)


def resolve_calendar_id(*, token: str, auth_mode: str, calendar_id: str | None) -> tuple[str, dict[str, object] | None]:
    if calendar_id:
        return calendar_id, None
    primary = resolve_primary_calendar(token=token, auth_mode=auth_mode)
    return str(primary["calendar_id"]), primary


def normalize_result(*, api_alias: str, auth_mode: str, response: dict[str, object], **extra: object) -> dict[str, object]:
    result: dict[str, object] = {
        "api_alias": api_alias,
        "auth_mode": auth_mode,
        "response": response,
    }
    result.update(extra)
    return result


def add_token_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--user-access-token", help="User access token. Use skill feishu-auth-and-scopes to obtain.")
    parser.add_argument("--tenant-access-token", help="Tenant access token. Use skill feishu-auth-and-scopes to obtain.")
    parser.add_argument("--use-tenant-token", action="store_true", help="Force tenant token mode (requires --tenant-access-token).")


def add_calendar_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--calendar-id", help="Explicit calendar_id. If omitted, helper resolves the primary calendar.")


def add_common_event_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--location")
    parser.add_argument("--visibility", choices=["default", "public", "private"])
    parser.add_argument("--reminder-minutes", type=int, action="append", default=[], help="Reminder minutes before the event; can repeat.")


def add_create_defaults_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--need-notification",
        dest="need_notification",
        action="store_true",
        default=None,
        help="Whether Feishu should notify attendees on creation. Defaults to true.",
    )
    parser.add_argument(
        "--no-need-notification",
        dest="need_notification",
        action="store_false",
        help="Disable attendee notification on creation.",
    )
    parser.add_argument(
        "--attendee-ability",
        default="can_modify_event",
        help="attendee_ability field for created events. Defaults to can_modify_event.",
    )
    parser.add_argument(
        "--attendee-open-id",
        action="append",
        default=[],
        help="User open_id to add as attendee after create-event. Repeatable. In tenant mode, helper requires at least one attendee.",
    )
    parser.add_argument(
        "--attendee-query",
        action="append",
        default=[],
        help="User email or name used to resolve attendee open_id via search/v1/user. Repeatable.",
    )
    parser.add_argument(
        "--attendee-email",
        action="append",
        default=[],
        help="Legacy alias for --attendee-query when the input is an email address. Repeatable.",
    )


def add_update_defaults_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--set-need-notification",
        dest="set_need_notification",
        action="store_true",
        default=None,
        help="Set need_notification=true in patch body.",
    )
    parser.add_argument(
        "--unset-need-notification",
        dest="set_need_notification",
        action="store_false",
        help="Set need_notification=false in patch body.",
    )
    parser.add_argument(
        "--set-attendee-ability",
        help="Set attendee_ability in patch body.",
    )
