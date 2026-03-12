from __future__ import annotations

"""OAuth and token exchange helpers for the auth runtime."""

import sys
import time
import urllib.parse
import webbrowser
from typing import Any

from .common import (
    DEVICE_AUTHORIZATION_ENDPOINT,
    TENANT_TOKEN_ENDPOINT,
    TOKEN_ENDPOINT,
    http_json,
    mask_secret,
    now_epoch,
    print_json,
)
from .token_ops import (
    build_user_token_record,
    is_access_token_valid,
    is_refresh_token_valid,
    normalize_scopes,
    persist_user_record,
    require_app_credentials_values,
    resolve_cached_user_record,
    summarize_token_record,
    user_cache_key,
    user_cache_path,
)


def request_device_authorization(app_id: str, app_secret: str, scopes: list[str]) -> dict[str, Any]:
    import base64

    scope = " ".join(normalize_scopes(scopes, include_offline_access=True))
    basic = base64.b64encode(f"{app_id}:{app_secret}".encode("utf-8")).decode("ascii")
    body = urllib.parse.urlencode({"client_id": app_id, "scope": scope}).encode("utf-8")
    status, payload, text = http_json(
        DEVICE_AUTHORIZATION_ENDPOINT,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic}",
        },
        data=body,
    )
    if status >= 400 or payload.get("error"):
        raise SystemExit(f"device authorization failed: {payload or text}")
    return payload


def poll_device_token(
    app_id: str,
    app_secret: str,
    device_code: str,
    interval: int,
    expires_in: int,
) -> dict[str, Any]:
    deadline = time.time() + expires_in
    current_interval = interval
    while time.time() < deadline:
        time.sleep(current_interval)
        body = urllib.parse.urlencode(
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
                "client_id": app_id,
                "client_secret": app_secret,
            }
        ).encode("utf-8")
        status, payload, text = http_json(
            TOKEN_ENDPOINT,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=body,
        )
        if status < 400 and payload.get("access_token"):
            return payload
        error = payload.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            current_interval += 5
            continue
        if error in {"access_denied", "expired_token", "invalid_grant"}:
            raise SystemExit(f"device authorization failed: {payload}")
        if status >= 400:
            raise SystemExit(f"device token polling failed: {payload or text}")
    raise SystemExit("device authorization timed out")


def request_user_token_with_json(body: dict[str, Any]) -> tuple[int, dict[str, Any], str]:
    import json

    return http_json(
        TOKEN_ENDPOINT,
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps(body, ensure_ascii=True).encode("utf-8"),
    )


def request_user_token_with_form(body: dict[str, Any]) -> tuple[int, dict[str, Any], str]:
    encoded = urllib.parse.urlencode({key: value for key, value in body.items() if value is not None}).encode("utf-8")
    return http_json(
        TOKEN_ENDPOINT,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=encoded,
    )


def exchange_refresh_token(app_id: str, app_secret: str, refresh_token: str) -> dict[str, Any]:
    body = {
        "grant_type": "refresh_token",
        "app_id": app_id,
        "app_secret": app_secret,
        "client_id": app_id,
        "client_secret": app_secret,
        "refresh_token": refresh_token,
    }
    status, payload, text = request_user_token_with_json(body)
    if status < 400 and payload.get("access_token"):
        return payload
    status, payload, text = request_user_token_with_form(body)
    if status >= 400 or not payload.get("access_token"):
        raise SystemExit(f"refresh token exchange failed: {payload or text}")
    return payload


def obtain_tenant_access_token(app_id: str, app_secret: str) -> dict[str, Any]:
    import json

    status, payload, text = http_json(
        TENANT_TOKEN_ENDPOINT,
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"app_id": app_id, "app_secret": app_secret}, ensure_ascii=True).encode("utf-8"),
    )
    if status >= 400 or payload.get("code") != 0:
        raise SystemExit(f"tenant token request failed: {payload or text}")
    token = payload.get("tenant_access_token")
    if not token:
        raise SystemExit(f"tenant token missing in response: {payload}")
    obtained_at = now_epoch()
    expires_in = int(payload.get("expire") or payload.get("expires_in") or 0)
    return {
        "kind": "tenant_access_token",
        "source": "tenant_access_token_internal",
        "app_id": app_id,
        "access_token": str(token),
        "obtained_at": obtained_at,
        "expires_in": expires_in,
        "expires_at": obtained_at + expires_in if expires_in > 0 else None,
        "access_token_masked": mask_secret(str(token)),
    }


def emit_token_output(
    payload: dict[str, Any],
    *,
    include_secrets: bool,
    print_access_token: bool,
) -> None:
    if print_access_token:
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise SystemExit("resolved token payload does not include access_token")
        print(access_token)
        return
    if not include_secrets and "access_token" in payload:
        payload = dict(payload)
        payload.pop("access_token", None)
        payload.pop("refresh_token", None)
    print_json(payload)


def device_authorize_and_cache(
    *,
    app_id: str,
    app_secret: str,
    scopes: list[str],
    cache_key: str | None,
    open_browser: bool,
) -> tuple[dict[str, Any], str]:
    resolved_scopes = normalize_scopes(scopes, include_offline_access=True)
    requested_scope_text = " ".join(resolved_scopes)
    path = user_cache_path(app_id, cache_key)
    device_payload = request_device_authorization(app_id, app_secret, resolved_scopes)
    verification_url = str(device_payload.get("verification_uri_complete") or device_payload.get("verification_uri") or "")
    user_code = str(device_payload.get("user_code", ""))
    print(
        (
            "需要在浏览器中完成飞书授权。\n"
            f"本次请求的 scopes: {requested_scope_text}\n"
            f"授权地址: {verification_url}\n"
            f"用户验证码: {user_code}\n"
        ),
        file=sys.stderr,
        flush=True,
    )
    if open_browser and verification_url:
        webbrowser.open(verification_url)
    token_payload = poll_device_token(
        app_id,
        app_secret,
        str(device_payload["device_code"]),
        int(device_payload.get("interval", 5)),
        int(device_payload.get("expires_in", 240)),
    )
    record = build_user_token_record(
        token_payload,
        app_id=app_id,
        source="device_authorization",
        cache_key=user_cache_key(app_id, cache_key),
        scopes_requested=resolved_scopes,
    )
    persist_user_record(path, record)
    return record, str(path)


def refresh_cached_user_record(
    *,
    app_id: str,
    app_secret: str,
    record: dict[str, Any],
    cache_key: str | None,
) -> tuple[dict[str, Any], str]:
    refresh_token = record.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise SystemExit("cached record does not contain refresh_token")
    token_payload = exchange_refresh_token(app_id, app_secret, refresh_token)
    path = user_cache_path(app_id, cache_key)
    refreshed = build_user_token_record(
        token_payload,
        app_id=app_id,
        source="refresh_token",
        cache_key=user_cache_key(app_id, cache_key),
        scopes_requested=normalize_scopes(record.get("scopes_requested") or [], include_offline_access=True),
    )
    persist_user_record(path, refreshed)
    return refreshed, str(path)


def resolve_user_token_record(
    *,
    app_id: str,
    app_secret: str,
    explicit_user_access_token: str | None,
    cache_key: str | None,
    allow_device_auth: bool,
    open_browser: bool,
    scopes: list[str],
) -> tuple[dict[str, Any], str | None]:
    import os

    if explicit_user_access_token:
        record = {
            "kind": "user_access_token",
            "source": "explicit_user_access_token",
            "app_id": app_id,
            "cache_key": user_cache_key(app_id, cache_key),
            "access_token": explicit_user_access_token,
            "scope": None,
            "scopes_requested": normalize_scopes(scopes, include_offline_access=False),
            "obtained_at": now_epoch(),
            "expires_in": None,
            "expires_at": None,
        }
        return record, None

    env_token = os.getenv("MY_LARK_USER_ACCESS_TOKEN")
    if env_token:
        record = {
            "kind": "user_access_token",
            "source": "environment_MY_LARK_USER_ACCESS_TOKEN",
            "app_id": app_id,
            "cache_key": user_cache_key(app_id, cache_key),
            "access_token": env_token,
            "scope": None,
            "scopes_requested": normalize_scopes(scopes, include_offline_access=False),
            "obtained_at": now_epoch(),
            "expires_in": None,
            "expires_at": None,
        }
        return record, None

    cache_path, cached_record = resolve_cached_user_record(app_id, cache_key)
    if is_access_token_valid(cached_record):
        assert cached_record is not None
        cached_record["source"] = "cache"
        return cached_record, str(cache_path)

    if is_refresh_token_valid(cached_record):
        assert cached_record is not None
        refreshed_record, path = refresh_cached_user_record(
            app_id=app_id,
            app_secret=app_secret,
            record=cached_record,
            cache_key=cache_key,
        )
        return refreshed_record, path

    if allow_device_auth:
        return device_authorize_and_cache(
            app_id=app_id,
            app_secret=app_secret,
            scopes=scopes,
            cache_key=cache_key,
            open_browser=open_browser,
        )

    raise SystemExit(
        "missing user token: provide --user-access-token, set MY_LARK_USER_ACCESS_TOKEN, or run with --device-auth"
    )


def resolve_token_payload(
    *,
    identity: str,
    app_id: str | None,
    app_secret: str | None,
    user_access_token: str | None = None,
    tenant_access_token: str | None = None,
    cache_key: str | None = None,
    allow_device_auth: bool = False,
    open_browser: bool = False,
    scopes: list[str] | None = None,
    include_secrets: bool = False,
) -> dict[str, Any]:
    import os

    if identity == "tenant":
        if tenant_access_token:
            result: dict[str, Any] = {
                "kind": "tenant_access_token",
                "source": "explicit_tenant_access_token",
                "app_id": app_id or os.getenv("MY_LARK_APP_ID"),
                "access_token": tenant_access_token,
                "access_token_masked": mask_secret(tenant_access_token),
            }
            if not include_secrets:
                result.pop("access_token", None)
            return result
        env_tenant_token = os.getenv("MY_LARK_TENANT_ACCESS_TOKEN")
        if env_tenant_token:
            result = {
                "kind": "tenant_access_token",
                "source": "environment_MY_LARK_TENANT_ACCESS_TOKEN",
                "app_id": app_id or os.getenv("MY_LARK_APP_ID"),
                "access_token": env_tenant_token,
                "access_token_masked": mask_secret(env_tenant_token),
            }
            if not include_secrets:
                result.pop("access_token", None)
            return result
        resolved_app_id, resolved_app_secret = require_app_credentials_values(app_id, app_secret, identity="tenant")
        result = obtain_tenant_access_token(resolved_app_id, resolved_app_secret)
        if not include_secrets:
            result = dict(result)
            result.pop("access_token", None)
        return result

    resolved_app_id, resolved_app_secret = require_app_credentials_values(app_id, app_secret, identity="user")
    record, path = resolve_user_token_record(
        app_id=resolved_app_id,
        app_secret=resolved_app_secret,
        explicit_user_access_token=user_access_token,
        cache_key=cache_key,
        allow_device_auth=allow_device_auth,
        open_browser=open_browser,
        scopes=scopes or [],
    )
    payload = summarize_token_record(record, include_secrets=include_secrets)
    payload["resolved_identity"] = "user"
    payload["cache_path"] = path
    if include_secrets:
        payload["access_token"] = record.get("access_token")
        payload["refresh_token"] = record.get("refresh_token")
    return payload
