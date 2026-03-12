from __future__ import annotations

"""CLI command handlers for the auth-and-scopes helper."""

import argparse
import json
import urllib.parse

from .classify_ops import classify_error, classify_operation
from .common import TENANT_TOKEN_ENDPOINT, TOKEN_ENDPOINT, print_json
from .oauth_ops import (
    device_authorize_and_cache,
    emit_token_output,
    exchange_refresh_token,
    obtain_tenant_access_token,
    refresh_cached_user_record,
    resolve_token_payload,
)
from .token_ops import (
    build_user_token_record,
    normalize_scopes,
    require_app_id,
    require_app_secret,
    resolve_cached_user_record,
    summarize_token_record,
    user_cache_key,
    user_cache_path,
)
from .common import save_json_file


def cmd_required_identity(args: argparse.Namespace) -> None:
    result = classify_operation(args.operation)
    result["operation"] = args.operation
    print_json(result)


def cmd_oauth_url(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    app_id = require_app_id(args, parser)
    params = {
        "app_id": app_id,
        "redirect_uri": args.redirect_uri,
        "scope": ",".join(args.scopes),
        "state": args.state,
    }
    if args.response_type:
        params["response_type"] = args.response_type
    url = "https://open.feishu.cn/open-apis/authen/v1/authorize?" + urllib.parse.urlencode(params)
    print_json(
        {
            "oauth_url": url,
            "state": args.state,
            "scopes": args.scopes,
            "next_step": "Open the URL in a browser, then exchange the returned code for a user_access_token.",
        }
    )


def cmd_tenant_token_curl(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    app_id = require_app_id(args, parser)
    app_secret = require_app_secret(args, parser)
    body = {
        "app_id": app_id,
        "app_secret": app_secret,
    }
    curl = [
        f"curl -X POST '{TENANT_TOKEN_ENDPOINT}'",
        "  -H 'Content-Type: application/json'",
        f"  -d '{json.dumps(body, ensure_ascii=True)}'",
    ]
    print_json(
        {
            "endpoint": TENANT_TOKEN_ENDPOINT,
            "method": "POST",
            "request_body": body,
            "curl": " \\\n".join(curl),
        }
    )


def cmd_user_token_curl(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    app_id = require_app_id(args, parser)
    app_secret = require_app_secret(args, parser)
    body = {
        "grant_type": args.grant_type,
        "app_id": app_id,
        "app_secret": app_secret,
    }
    if args.grant_type == "authorization_code":
        body["code"] = args.code
    else:
        body["client_id"] = app_id
        body["client_secret"] = app_secret
        body["refresh_token"] = args.refresh_token
    curl = [
        f"curl -X POST '{TOKEN_ENDPOINT}'",
        "  -H 'Content-Type: application/json'",
        f"  -d '{json.dumps(body, ensure_ascii=True)}'",
    ]
    print_json(
        {
            "endpoint": TOKEN_ENDPOINT,
            "method": "POST",
            "request_body": body,
            "curl": " \\\n".join(curl),
        }
    )


def cmd_classify_error(args: argparse.Namespace) -> None:
    result = classify_error(args.text)
    result["error_text"] = args.text
    print_json(result)


def cmd_tenant_token(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    app_id = require_app_id(args, parser)
    app_secret = require_app_secret(args, parser)
    result = obtain_tenant_access_token(app_id, app_secret)
    emit_token_output(result, include_secrets=args.include_secrets, print_access_token=args.print_access_token)


def cmd_auth_user(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    app_id = require_app_id(args, parser)
    app_secret = require_app_secret(args, parser)
    record, path = device_authorize_and_cache(
        app_id=app_id,
        app_secret=app_secret,
        scopes=args.scopes,
        cache_key=args.cache_key,
        open_browser=args.open_browser,
    )
    payload = summarize_token_record(record, include_secrets=args.include_secrets)
    payload["cache_path"] = path
    payload["message"] = "User access token has been cached locally."
    if args.include_secrets:
        payload["access_token"] = record.get("access_token")
        payload["refresh_token"] = record.get("refresh_token")
    emit_token_output(payload, include_secrets=args.include_secrets, print_access_token=args.print_access_token)


def cmd_refresh_user_token(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    app_id = require_app_id(args, parser)
    app_secret = require_app_secret(args, parser)
    if args.refresh_token:
        payload = exchange_refresh_token(app_id, app_secret, args.refresh_token)
        record = build_user_token_record(
            payload,
            app_id=app_id,
            source="refresh_token",
            cache_key=user_cache_key(app_id, args.cache_key),
            scopes_requested=normalize_scopes(args.scopes, include_offline_access=True),
        )
        path = user_cache_path(app_id, args.cache_key)
        save_json_file(path, record)
    else:
        _, record = resolve_cached_user_record(app_id, args.cache_key)
        if not isinstance(record, dict) or not record.get("refresh_token"):
            raise SystemExit("no valid cached refresh_token found; provide --refresh-token or run auth-user again")
        record, path_str = refresh_cached_user_record(
            app_id=app_id,
            app_secret=app_secret,
            record=record,
            cache_key=args.cache_key,
        )
        path = user_cache_path(app_id, args.cache_key)
        if str(path) != path_str:
            raise SystemExit("refreshed token cache path mismatch")
    payload = summarize_token_record(record, include_secrets=args.include_secrets)
    payload["cache_path"] = str(path)
    payload["message"] = "User access token has been refreshed and cached locally."
    if args.include_secrets:
        payload["access_token"] = record.get("access_token")
        payload["refresh_token"] = record.get("refresh_token")
    emit_token_output(payload, include_secrets=args.include_secrets, print_access_token=args.print_access_token)


def cmd_resolve_token(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.identity == "user":
        require_app_id(args, parser)
        require_app_secret(args, parser)
    include_secrets = args.include_secrets or args.print_access_token
    payload = resolve_token_payload(
        identity=args.identity,
        app_id=args.app_id,
        app_secret=args.app_secret,
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        cache_key=args.cache_key,
        allow_device_auth=args.device_auth,
        open_browser=args.open_browser,
        scopes=args.scopes,
        include_secrets=include_secrets,
    )
    emit_token_output(payload, include_secrets=include_secrets, print_access_token=args.print_access_token)


def cmd_show_token_meta(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    from .common import cache_root

    app_id = require_app_id(args, parser)
    path, record = resolve_cached_user_record(app_id, args.cache_key)
    payload = {
        "cache_path": str(path),
        "cache_exists": path.exists(),
        "cache_key": user_cache_key(app_id, args.cache_key),
        "app_id": app_id,
        "cache_root": str(cache_root()),
    }
    if record:
        payload["token"] = summarize_token_record(record, include_secrets=args.include_secrets)
    print_json(payload)


def cmd_clear_token_cache(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    app_id = require_app_id(args, parser)
    path = user_cache_path(app_id, args.cache_key)
    removed = False
    if path.exists():
        path.unlink()
        removed = True
    print_json(
        {
            "cache_path": str(path),
            "removed": removed,
        }
    )
