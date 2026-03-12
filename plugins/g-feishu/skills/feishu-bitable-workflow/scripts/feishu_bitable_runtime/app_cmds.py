from __future__ import annotations

"""App-level CRUD commands for Bitable."""

import argparse

from .api import ensure_success, normalize_result, request_json, resolve_token
from .common import fail, parse_bool, print_json


def cmd_create_app(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="create-app",
    )
    body: dict[str, object] = {"name": args.name}
    if args.folder_token:
        body["folder_token"] = args.folder_token
    response = request_json(method="POST", path="/bitable/v1/apps", token=token, body=body)
    ensure_success(response, api_alias="bitable_v1_app_create", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_create",
            auth_mode=auth_mode,
            response=response,
            app=response.get("data", {}).get("app"),
            app_token=response.get("data", {}).get("app", {}).get("app_token"),
        )
    )


def cmd_get_app(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="get-app",
    )
    response = request_json(method="GET", path=f"/bitable/v1/apps/{args.app_token}", token=token)
    ensure_success(response, api_alias="bitable_v1_app_get", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_get",
            auth_mode=auth_mode,
            response=response,
            app=response.get("data", {}).get("app"),
            app_token=args.app_token,
        )
    )


def cmd_list_apps(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="list-apps",
    )
    response = request_json(
        method="GET",
        path="/drive/v1/files",
        token=token,
        query={"folder_token": args.folder_token or "", "page_size": args.page_size, "page_token": args.page_token},
    )
    ensure_success(response, api_alias="drive_v1_file_list", auth_mode=auth_mode)
    files = response.get("data", {}).get("files", [])
    apps = [item for item in files if item.get("type") == "bitable"]
    print_json(
        normalize_result(
            api_alias="drive_v1_file_list",
            auth_mode=auth_mode,
            response=response,
            apps=apps,
            has_more=response.get("data", {}).get("has_more", False),
            page_token=response.get("data", {}).get("page_token"),
        )
    )


def cmd_update_app(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="update-app",
    )
    body: dict[str, object] = {}
    if args.name is not None:
        body["name"] = args.name
    if args.is_advanced is not None:
        body["is_advanced"] = parse_bool(args.is_advanced)
    if not body:
        fail("update-app requires at least one change: --name or --is-advanced.")
    response = request_json(method="PUT", path=f"/bitable/v1/apps/{args.app_token}", token=token, body=body)
    ensure_success(response, api_alias="bitable_v1_app_update", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_update",
            auth_mode=auth_mode,
            response=response,
            app=response.get("data", {}).get("app"),
            app_token=args.app_token,
        )
    )


def cmd_copy_app(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="copy-app",
    )
    body: dict[str, object] = {"name": args.name}
    if args.folder_token:
        body["folder_token"] = args.folder_token
    response = request_json(method="POST", path=f"/bitable/v1/apps/{args.app_token}/copy", token=token, body=body)
    ensure_success(response, api_alias="bitable_v1_app_copy", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_copy",
            auth_mode=auth_mode,
            response=response,
            app=response.get("data", {}).get("app"),
            app_token=response.get("data", {}).get("app", {}).get("app_token"),
        )
    )
