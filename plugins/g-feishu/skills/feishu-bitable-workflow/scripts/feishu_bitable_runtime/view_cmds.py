from __future__ import annotations

"""View CRUD commands for Bitable tables."""

import argparse

from .api import ensure_success, normalize_result, request_json, resolve_token
from .common import fail, print_json
from .schema_ops import create_view_raw


def cmd_get_view(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="get-view",
    )
    response = request_json(
        method="GET",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/views/{args.view_id}",
        token=token,
    )
    ensure_success(response, api_alias="bitable_v1_app_table_view_get", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_view_get",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            view_id=args.view_id,
            view=response.get("data", {}).get("view"),
        )
    )


def cmd_list_views(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="list-views",
    )
    response = request_json(
        method="GET",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/views",
        token=token,
        query={"page_size": args.page_size, "page_token": args.page_token},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_view_list", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_view_list",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            views=response.get("data", {}).get("items"),
            has_more=response.get("data", {}).get("has_more", False),
            page_token=response.get("data", {}).get("page_token"),
        )
    )


def cmd_create_view(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="create-view",
    )
    response = create_view_raw(
        token=token,
        app_token=args.app_token,
        table_id=args.table_id,
        view_name=args.view_name,
        view_type=args.view_type,
    )
    ensure_success(response, api_alias="bitable_v1_app_table_view_create", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_view_create",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            view_id=response.get("data", {}).get("view", {}).get("view_id"),
            view=response.get("data", {}).get("view"),
        )
    )


def cmd_update_view(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="update-view",
    )
    if not args.view_name:
        fail("update-view requires --view-name.")
    response = request_json(
        method="PATCH",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/views/{args.view_id}",
        token=token,
        body={"view_name": args.view_name},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_view_patch", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_view_patch",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            view_id=args.view_id,
            view=response.get("data", {}).get("view"),
        )
    )


def cmd_delete_view(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="delete-view",
    )
    response = request_json(
        method="DELETE",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/views/{args.view_id}",
        token=token,
    )
    ensure_success(response, api_alias="bitable_v1_app_table_view_delete", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_view_delete",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            view_id=args.view_id,
            success=True,
        )
    )
