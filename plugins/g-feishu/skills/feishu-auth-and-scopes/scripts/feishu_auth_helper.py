#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import urllib.parse
from feishu_auth_runtime.command_ops import (
    cmd_auth_user,
    cmd_classify_error,
    cmd_clear_token_cache,
    cmd_oauth_url,
    cmd_refresh_user_token,
    cmd_required_identity,
    cmd_resolve_token,
    cmd_show_token_meta,
    cmd_tenant_token,
    cmd_tenant_token_curl,
    cmd_user_token_curl,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone Feishu auth and scope helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    required_identity = subparsers.add_parser("required-identity", help="Infer the likely identity and token type for an operation.")
    required_identity.add_argument("--operation", required=True, help="Natural-language description of the action.")
    required_identity.set_defaults(func=cmd_required_identity)

    oauth_url = subparsers.add_parser("oauth-url", help="Build an OAuth authorize URL.")
    oauth_url.add_argument("--app-id", default=os.getenv("MY_LARK_APP_ID"), help="Defaults to MY_LARK_APP_ID.")
    oauth_url.add_argument("--redirect-uri", required=True)
    oauth_url.add_argument("--scopes", nargs="+", required=True)
    oauth_url.add_argument("--state", default="codex-state")
    oauth_url.add_argument("--response-type", default="code")
    oauth_url.set_defaults(func=cmd_oauth_url)

    tenant_token_curl = subparsers.add_parser("tenant-token-curl", help="Emit a curl template for tenant_access_token/internal.")
    tenant_token_curl.add_argument("--app-id", default=os.getenv("MY_LARK_APP_ID"), help="Defaults to MY_LARK_APP_ID.")
    tenant_token_curl.add_argument("--app-secret", default=os.getenv("MY_LARK_APP_SECRET"), help="Defaults to MY_LARK_APP_SECRET.")
    tenant_token_curl.set_defaults(func=cmd_tenant_token_curl)

    user_token_curl = subparsers.add_parser("user-token-curl", help="Emit a curl template for exchanging an auth code or refresh token.")
    user_token_curl.add_argument("--app-id", default=os.getenv("MY_LARK_APP_ID"), help="Defaults to MY_LARK_APP_ID.")
    user_token_curl.add_argument("--app-secret", default=os.getenv("MY_LARK_APP_SECRET"), help="Defaults to MY_LARK_APP_SECRET.")
    user_token_curl.add_argument("--grant-type", choices=["authorization_code", "refresh_token"], required=True)
    user_token_curl.add_argument("--code")
    user_token_curl.add_argument("--refresh-token")
    user_token_curl.set_defaults(func=cmd_user_token_curl)

    classify = subparsers.add_parser("classify-error", help="Bucket a Feishu auth or scope failure.")
    classify.add_argument("--text", required=True)
    classify.set_defaults(func=cmd_classify_error)

    tenant_token = subparsers.add_parser("tenant-token", help="Fetch a real tenant access token.")
    tenant_token.add_argument("--app-id", default=os.getenv("MY_LARK_APP_ID"), help="Defaults to MY_LARK_APP_ID.")
    tenant_token.add_argument("--app-secret", default=os.getenv("MY_LARK_APP_SECRET"), help="Defaults to MY_LARK_APP_SECRET.")
    tenant_token.add_argument("--include-secrets", action="store_true", help="Include access_token in the JSON output.")
    tenant_token.add_argument("--print-access-token", action="store_true", help="Print only the raw access token.")
    tenant_token.set_defaults(func=cmd_tenant_token)

    auth_user = subparsers.add_parser("auth-user", help="Run device authorization, cache the user token, and optionally print it.")
    auth_user.add_argument("--app-id", default=os.getenv("MY_LARK_APP_ID"), help="Defaults to MY_LARK_APP_ID.")
    auth_user.add_argument("--app-secret", default=os.getenv("MY_LARK_APP_SECRET"), help="Defaults to MY_LARK_APP_SECRET.")
    auth_user.add_argument("--scopes", nargs="*", default=[], help="Requested scopes; offline_access is added automatically.")
    auth_user.add_argument("--cache-key", help="Optional cache key when one app uses multiple token profiles.")
    auth_user.add_argument("--open-browser", action="store_true", help="Open the verification URL in the default browser.")
    auth_user.add_argument("--include-secrets", action="store_true", help="Include access_token and refresh_token in the JSON output.")
    auth_user.add_argument("--print-access-token", action="store_true", help="Print only the raw access token.")
    auth_user.set_defaults(func=cmd_auth_user)

    refresh_user_token = subparsers.add_parser("refresh-user-token", help="Refresh a cached user token or an explicitly provided refresh token.")
    refresh_user_token.add_argument("--app-id", default=os.getenv("MY_LARK_APP_ID"), help="Defaults to MY_LARK_APP_ID.")
    refresh_user_token.add_argument("--app-secret", default=os.getenv("MY_LARK_APP_SECRET"), help="Defaults to MY_LARK_APP_SECRET.")
    refresh_user_token.add_argument("--refresh-token", help="Explicit refresh_token. If omitted, the cached refresh token is used.")
    refresh_user_token.add_argument("--cache-key", help="Optional cache key when one app uses multiple token profiles.")
    refresh_user_token.add_argument("--scopes", nargs="*", default=[], help="Optional scope hint to store alongside the refreshed token.")
    refresh_user_token.add_argument("--include-secrets", action="store_true", help="Include access_token and refresh_token in the JSON output.")
    refresh_user_token.add_argument("--print-access-token", action="store_true", help="Print only the raw access token.")
    refresh_user_token.set_defaults(func=cmd_refresh_user_token)

    resolve_token = subparsers.add_parser("resolve-token", help="Resolve a tenant or user token from explicit input, env, cache, refresh, or device auth.")
    resolve_token.add_argument("--identity", choices=["user", "tenant"], default="user")
    resolve_token.add_argument("--app-id", default=os.getenv("MY_LARK_APP_ID"), help="Defaults to MY_LARK_APP_ID.")
    resolve_token.add_argument("--app-secret", default=os.getenv("MY_LARK_APP_SECRET"), help="Defaults to MY_LARK_APP_SECRET.")
    resolve_token.add_argument("--user-access-token", help="Explicit user_access_token.")
    resolve_token.add_argument("--tenant-access-token", help="Explicit tenant_access_token.")
    resolve_token.add_argument("--device-auth", action="store_true", help="If no user token is available, start device authorization.")
    resolve_token.add_argument("--open-browser", action="store_true", help="Open the verification URL in the default browser when using device auth.")
    resolve_token.add_argument("--scopes", nargs="*", default=[], help="Requested scopes when device auth is needed.")
    resolve_token.add_argument("--cache-key", help="Optional cache key when one app uses multiple token profiles.")
    resolve_token.add_argument("--include-secrets", action="store_true", help="Include access_token and refresh_token in the JSON output.")
    resolve_token.add_argument("--print-access-token", action="store_true", help="Print only the raw access token.")
    resolve_token.set_defaults(func=cmd_resolve_token)

    show_token_meta = subparsers.add_parser("show-token-meta", help="Show cached user token metadata without re-authorizing.")
    show_token_meta.add_argument("--app-id", default=os.getenv("MY_LARK_APP_ID"), help="Defaults to MY_LARK_APP_ID.")
    show_token_meta.add_argument("--cache-key", help="Optional cache key when one app uses multiple token profiles.")
    show_token_meta.add_argument("--include-secrets", action="store_true", help="Include masked token metadata plus raw secrets.")
    show_token_meta.set_defaults(func=cmd_show_token_meta)

    clear_token_cache = subparsers.add_parser("clear-token-cache", help="Delete the cached user token record for the current app/cache key.")
    clear_token_cache.add_argument("--app-id", default=os.getenv("MY_LARK_APP_ID"), help="Defaults to MY_LARK_APP_ID.")
    clear_token_cache.add_argument("--cache-key", help="Optional cache key when one app uses multiple token profiles.")
    clear_token_cache.set_defaults(func=cmd_clear_token_cache)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "grant_type", None) == "authorization_code" and not args.code:
        parser.error("--code is required when --grant-type authorization_code")
    if getattr(args, "grant_type", None) == "refresh_token" and not args.refresh_token:
        parser.error("--refresh-token is required when --grant-type refresh_token")
    args.func(args, parser) if getattr(args, "command", None) in {
        "oauth-url",
        "tenant-token-curl",
        "user-token-curl",
        "tenant-token",
        "auth-user",
        "refresh-user-token",
        "resolve-token",
        "show-token-meta",
        "clear-token-cache",
    } else args.func(args)


if __name__ == "__main__":
    main()
