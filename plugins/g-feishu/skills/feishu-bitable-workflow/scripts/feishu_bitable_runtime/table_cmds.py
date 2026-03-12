from __future__ import annotations

"""Table CRUD commands for Bitable apps."""

import argparse

from .api import ensure_success, normalize_result, request_json, resolve_token
from .common import fail, load_json_value, load_string_list, normalize_json_list, normalize_json_object, print_json
from .field_types import strip_field_property_if_forbidden


def cmd_create_table(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="create-table",
    )
    table: dict[str, object] = {"name": args.name}
    fields = load_json_value(args.fields_json, args.fields_file, default=[])
    if fields:
        normalized_fields = []
        for item in normalize_json_list(fields, name="fields"):
            normalized_fields.append(strip_field_property_if_forbidden(normalize_json_object(item, name="field")))
        table["fields"] = normalized_fields
    response = request_json(
        method="POST",
        path=f"/bitable/v1/apps/{args.app_token}/tables",
        token=token,
        body={"table": table},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_create", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_create",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=response.get("data", {}).get("table_id"),
            default_view_id=response.get("data", {}).get("default_view_id"),
            field_id_list=response.get("data", {}).get("field_id_list"),
        )
    )


def cmd_list_tables(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="list-tables",
    )
    response = request_json(
        method="GET",
        path=f"/bitable/v1/apps/{args.app_token}/tables",
        token=token,
        query={"page_size": args.page_size, "page_token": args.page_token},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_list", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_list",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            tables=response.get("data", {}).get("items"),
            has_more=response.get("data", {}).get("has_more", False),
            page_token=response.get("data", {}).get("page_token"),
        )
    )


def cmd_update_table(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="update-table",
    )
    if not args.name:
        fail("update-table requires --name.")
    response = request_json(
        method="PATCH",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}",
        token=token,
        body={"name": args.name},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_patch", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_patch",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            name=response.get("data", {}).get("name"),
        )
    )


def cmd_delete_table(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="delete-table",
    )
    response = request_json(
        method="DELETE",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}",
        token=token,
    )
    ensure_success(response, api_alias="bitable_v1_app_table_delete", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_delete",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            success=True,
        )
    )


def cmd_batch_create_tables(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="batch-create-tables",
    )
    tables = normalize_json_list(load_json_value(args.tables_json, args.tables_file, default=[]), name="tables")
    if not tables:
        fail("batch-create-tables requires --tables-json or --tables-file with at least one table.")
    response = request_json(
        method="POST",
        path=f"/bitable/v1/apps/{args.app_token}/tables/batch_create",
        token=token,
        body={"tables": tables},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_batch_create", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_batch_create",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_ids=response.get("data", {}).get("table_ids"),
        )
    )


def cmd_batch_delete_tables(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="batch-delete-tables",
    )
    table_ids = load_string_list(args.table_ids, args.table_ids_json, args.table_ids_file, name="table_ids")
    if not table_ids:
        fail("batch-delete-tables requires at least one table id.")
    response = request_json(
        method="POST",
        path=f"/bitable/v1/apps/{args.app_token}/tables/batch_delete",
        token=token,
        body={"table_ids": table_ids},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_batch_delete", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_batch_delete",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_ids=table_ids,
            success=True,
        )
    )
