from __future__ import annotations

"""Shared HTTP/auth/link helpers for Bitable runtime modules."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .common import fail


API_BASE = "https://open.feishu.cn/open-apis"
USER_ID_TYPE = "open_id"


def resolve_bitable_web_base() -> str | None:
    for env_name in ("MY_LARK_WEB_BASE_URL", "FEISHU_WEB_BASE_URL", "LARK_WEB_BASE_URL"):
        env_value = os.environ.get(env_name)
        if env_value and env_value.strip():
            return f"{env_value.strip().rstrip('/')}/base"
    return None


def build_web_link_notice(*, resource_kind: str) -> dict[str, str] | None:
    if resolve_bitable_web_base():
        return None
    return {
        "reason": "web_base_url_not_configured",
        "env_var": "MY_LARK_WEB_BASE_URL",
        "resource_kind": resource_kind,
        "message": (
            "当前未设置 MY_LARK_WEB_BASE_URL，因此本次输出不会包含可点击的租户内网页链接。"
            "如需返回可直接打开的多维表格链接，请先配置该环境变量。"
        ),
    }


def resolve_token(
    *,
    user_access_token: str | None,
    tenant_access_token: str | None,
    use_tenant_token: bool,
    command_name: str,
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
    env_tenant = os.environ.get("MY_LARK_TENANT_ACCESS_TOKEN")
    if env_tenant:
        return env_tenant, "environment_MY_LARK_TENANT_ACCESS_TOKEN"
    fail(
        f"{command_name} requires a Feishu token. Pass --user-access-token / --tenant-access-token, "
        "or set MY_LARK_USER_ACCESS_TOKEN / MY_LARK_TENANT_ACCESS_TOKEN. "
        "Use Agent Skill feishu-auth-and-scopes to obtain or refresh a token first."
    )


def request_json(
    *,
    method: str,
    path: str,
    token: str,
    query: dict[str, object] | None = None,
    body: dict[str, object] | None = None,
) -> dict[str, object]:
    url = f"{API_BASE}{path}"
    if query:
        filtered = {key: value for key, value in query.items() if value is not None}
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


def normalize_result(*, api_alias: str, auth_mode: str, response: dict[str, object], **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "api_alias": api_alias,
        "auth_mode": auth_mode,
        "response": response,
    }
    payload.update(extra)
    return add_bitable_links(payload)


def app_url_for(app_token: str | None, explicit_url: str | None = None) -> str | None:
    if explicit_url:
        return explicit_url
    if not app_token:
        return None
    web_base = resolve_bitable_web_base()
    if not web_base:
        return None
    return f"{web_base}/{app_token}"


def table_url_for(app_token: str | None, table_id: str | None, explicit_url: str | None = None) -> str | None:
    app_url = app_url_for(app_token, explicit_url)
    if not app_url or not table_id:
        return None
    return f"{app_url}?table={urllib.parse.quote(table_id)}"


def view_url_for(
    app_token: str | None,
    table_id: str | None,
    view_id: str | None,
    explicit_url: str | None = None,
) -> str | None:
    table_url = table_url_for(app_token, table_id, explicit_url)
    if not table_url or not view_id:
        return None
    return f"{table_url}&view={urllib.parse.quote(view_id)}"


def add_bitable_links(payload: dict[str, object]) -> dict[str, object]:
    response_data = payload.get("response", {}).get("data", {}) if isinstance(payload.get("response"), dict) else {}
    app = payload.get("app")
    if not isinstance(app, dict):
        app = response_data.get("app") if isinstance(response_data, dict) else None
    explicit_app_url = app.get("url") if isinstance(app, dict) and isinstance(app.get("url"), str) else None
    app_token = payload.get("app_token")
    if app_token is None and isinstance(app, dict):
        app_token = app.get("app_token")
    table_id = payload.get("table_id")
    if table_id is None and isinstance(response_data, dict):
        table_id = response_data.get("table_id")
    view_id = payload.get("view_id")
    if view_id is None and isinstance(response_data, dict):
        view = response_data.get("view")
        if isinstance(view, dict):
            view_id = view.get("view_id")
    app_url = app_url_for(str(app_token) if app_token else None, explicit_app_url)
    if app_url:
        payload["app_url"] = app_url
    table_url = table_url_for(str(app_token) if app_token else None, str(table_id) if table_id else None, explicit_app_url)
    if table_url:
        payload["table_url"] = table_url
    view_url = view_url_for(
        str(app_token) if app_token else None,
        str(table_id) if table_id else None,
        str(view_id) if view_id else None,
        explicit_app_url,
    )
    if view_url:
        payload["view_url"] = view_url
    if app_token and not payload.get("app_url"):
        payload["web_link_notice"] = build_web_link_notice(resource_kind="bitable")
    return payload
