from __future__ import annotations

"""Token cache, scope normalization, and cache path helpers for auth runtime."""

import argparse
from pathlib import Path
from typing import Any

from .common import (
    REFRESH_TOKEN_SKEW_SECONDS,
    USER_TOKEN_SKEW_SECONDS,
    cache_root,
    iso_utc,
    load_json_file,
    mask_secret,
    now_epoch,
    save_json_file,
    sanitize_cache_key,
)


def require_app_id(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    value = getattr(args, "app_id", None)
    if value:
        return value
    parser.error("--app-id is required, or set MY_LARK_APP_ID in the environment")


def require_app_secret(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    value = getattr(args, "app_secret", None)
    if value:
        return value
    parser.error("--app-secret is required, or set MY_LARK_APP_SECRET in the environment")


def normalize_scopes(scopes: list[str] | None, *, include_offline_access: bool = False) -> list[str]:
    normalized: list[str] = []
    for scope in scopes or []:
        candidate = scope.strip()
        if candidate and candidate not in normalized:
            normalized.append(candidate)
    if include_offline_access and "offline_access" not in normalized:
        normalized.append("offline_access")
    return normalized


def user_cache_key(app_id: str, cache_key: str | None) -> str:
    return sanitize_cache_key(cache_key or app_id)


def user_cache_path(app_id: str, cache_key: str | None) -> Path:
    return cache_root() / f"user-token-{user_cache_key(app_id, cache_key)}.json"


def summarize_token_record(record: dict[str, Any], *, include_secrets: bool = False) -> dict[str, Any]:
    expires_at = record.get("expires_at")
    refresh_expires_at = record.get("refresh_expires_at")
    payload = {
        "kind": record.get("kind"),
        "source": record.get("source"),
        "app_id": record.get("app_id"),
        "cache_key": record.get("cache_key"),
        "scope": record.get("scope"),
        "scopes_requested": record.get("scopes_requested", []),
        "obtained_at": record.get("obtained_at"),
        "obtained_at_iso": iso_utc(record.get("obtained_at")),
        "expires_in": record.get("expires_in"),
        "expires_at": expires_at,
        "expires_at_iso": iso_utc(expires_at),
        "refresh_expires_in": record.get("refresh_expires_in"),
        "refresh_expires_at": refresh_expires_at,
        "refresh_expires_at_iso": iso_utc(refresh_expires_at),
        "access_token_masked": mask_secret(record.get("access_token")),
        "refresh_token_masked": mask_secret(record.get("refresh_token")),
        "is_access_token_valid": is_access_token_valid(record),
        "is_refresh_token_valid": is_refresh_token_valid(record),
    }
    if include_secrets:
        payload["access_token"] = record.get("access_token")
        payload["refresh_token"] = record.get("refresh_token")
    return payload


def is_access_token_valid(record: dict[str, Any] | None, *, skew_seconds: int = USER_TOKEN_SKEW_SECONDS) -> bool:
    if not isinstance(record, dict):
        return False
    access_token = record.get("access_token")
    expires_at = record.get("expires_at")
    if not isinstance(access_token, str) or not access_token:
        return False
    if not isinstance(expires_at, int):
        return False
    return expires_at - now_epoch() > skew_seconds


def is_refresh_token_valid(record: dict[str, Any] | None, *, skew_seconds: int = REFRESH_TOKEN_SKEW_SECONDS) -> bool:
    if not isinstance(record, dict):
        return False
    refresh_token = record.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        return False
    refresh_expires_at = record.get("refresh_expires_at")
    if isinstance(refresh_expires_at, int):
        return refresh_expires_at - now_epoch() > skew_seconds
    return True


def build_user_token_record(
    payload: dict[str, Any],
    *,
    app_id: str,
    source: str,
    cache_key: str,
    scopes_requested: list[str],
) -> dict[str, Any]:
    obtained_at = now_epoch()
    expires_in = int(payload.get("expires_in") or 0)
    refresh_expires_in = payload.get("refresh_expires_in") or payload.get("refresh_token_expires_in")
    record: dict[str, Any] = {
        "kind": "user_access_token",
        "source": source,
        "app_id": app_id,
        "cache_key": cache_key,
        "access_token": str(payload.get("access_token") or ""),
        "refresh_token": str(payload.get("refresh_token") or ""),
        "scope": payload.get("scope"),
        "scopes_requested": scopes_requested,
        "obtained_at": obtained_at,
        "expires_in": expires_in,
        "expires_at": obtained_at + expires_in if expires_in > 0 else None,
    }
    if refresh_expires_in is not None:
        refresh_expires_in_int = int(refresh_expires_in)
        record["refresh_expires_in"] = refresh_expires_in_int
        record["refresh_expires_at"] = obtained_at + refresh_expires_in_int
    return record


def resolve_cached_user_record(app_id: str, cache_key: str | None) -> tuple[Path, dict[str, Any] | None]:
    path = user_cache_path(app_id, cache_key)
    return path, load_json_file(path)


def persist_user_record(path: Path, payload: dict[str, Any]) -> None:
    save_json_file(path, payload)


def require_app_credentials_values(app_id: str | None, app_secret: str | None, *, identity: str) -> tuple[str, str]:
    if not app_id:
        raise SystemExit(f"{identity} token resolution requires app_id or MY_LARK_APP_ID")
    if not app_secret:
        raise SystemExit(f"{identity} token resolution requires app_secret or MY_LARK_APP_SECRET")
    return app_id, app_secret
