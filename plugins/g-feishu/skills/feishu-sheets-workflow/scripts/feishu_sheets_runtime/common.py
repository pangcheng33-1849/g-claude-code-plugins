from __future__ import annotations

"""Shared HTTP/auth/JSON helpers for Sheets runtime modules."""

import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request


API_BASE = "https://open.feishu.cn/open-apis"


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def fail(
    message: str,
    *,
    api_alias: str | None = None,
    auth_mode: str | None = None,
    response: object | None = None,
) -> None:
    payload: dict[str, object] = {"error": message}
    if api_alias:
        payload["api_alias"] = api_alias
    if auth_mode:
        payload["auth_mode"] = auth_mode
    if response is not None:
        payload["response"] = response
    print_json(payload)
    raise SystemExit(1)


def load_json_value(inline_json: str | None, file_path: str | None, *, default: object) -> object:
    value = default
    if file_path:
        value = json.loads(pathlib.Path(file_path).read_text(encoding="utf-8"))
    if inline_json:
        value = json.loads(inline_json)
    return value


def resolve_token(
    *,
    user_access_token: str | None,
    tenant_access_token: str | None,
    command_name: str,
) -> tuple[str, str]:
    if user_access_token:
        return user_access_token, "argument_user_access_token"
    if tenant_access_token:
        return tenant_access_token, "argument_tenant_access_token"
    fail(
        f"{command_name} requires a Feishu token. Pass --user-access-token or --tenant-access-token. "
        "Use skill feishu-auth-and-scopes resolve-token to obtain a token first."
    )


def sheets_request(
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
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=payload, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"code": error.code, "msg": raw}


def ensure_success(response: dict[str, object], *, api_alias: str, auth_mode: str) -> None:
    if response.get("code") == 0:
        return
    fail(
        f"{api_alias} failed: {response.get('msg') or response.get('message') or 'unknown error'}",
        api_alias=api_alias,
        auth_mode=auth_mode,
        response=response,
    )


def resolve_sheets_web_base() -> str | None:
    for env_name in ("MY_LARK_WEB_BASE_URL", "FEISHU_WEB_BASE_URL", "LARK_WEB_BASE_URL"):
        env_value = os.environ.get(env_name)
        if env_value and env_value.strip():
            return env_value.strip().rstrip("/")
    return None


def spreadsheet_url_for(spreadsheet_token: str | None) -> str | None:
    if not spreadsheet_token:
        return None
    web_base = resolve_sheets_web_base()
    if not web_base:
        return None
    return f"{web_base}/sheets/{spreadsheet_token}"


def normalize_result(*, api_alias: str, auth_mode: str, response: dict[str, object], **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "api_alias": api_alias,
        "auth_mode": auth_mode,
        "response": response,
    }
    payload.update(extra)
    spreadsheet_token = payload.get("spreadsheet_token")
    if spreadsheet_token:
        url = spreadsheet_url_for(str(spreadsheet_token))
        if url:
            payload["spreadsheet_url"] = url
        else:
            payload["web_link_notice"] = {
                "reason": "web_base_url_not_configured",
                "env_var": "MY_LARK_WEB_BASE_URL",
                "resource_kind": "spreadsheet",
                "message": (
                    "MY_LARK_WEB_BASE_URL is not set, so clickable spreadsheet links are omitted. "
                    "Set the env var to enable web links."
                ),
            }
    return payload


def convert_simple_values(rows: list[list[object]]) -> list[list[list[dict[str, object]]]]:
    """Convert a 2D array of simple values into the rich text 3D array the Sheets API expects.

    Each cell becomes a list of segments (the inner-most list).
    - str  -> [{"type":"text","text":{"text":"value"}}]
    - int/float -> [{"type":"value","value":{"value":"123"}}]
    - None -> []
    """
    result: list[list[list[dict[str, object]]]] = []
    for row in rows:
        converted_row: list[list[dict[str, object]]] = []
        for cell in row:
            if cell is None:
                converted_row.append([])
            elif isinstance(cell, (int, float)):
                converted_row.append([{"type": "value", "value": {"value": str(cell)}}])
            else:
                converted_row.append([{"type": "text", "text": {"text": str(cell)}}])
        result.append(converted_row)
    return result
