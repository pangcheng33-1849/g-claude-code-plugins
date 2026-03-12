from __future__ import annotations

"""Field CRUD commands for Bitable tables."""

import argparse

from .api import ensure_success, normalize_result, request_json, resolve_token
from .common import normalize_json_object, print_json
from .field_types import build_field_property, normalize_field_item, resolve_field_type, strip_field_property_if_forbidden
from .schema_ops import resolve_field_defaults


def cmd_create_field(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="create-field",
    )
    field_type = resolve_field_type(args.type)
    if field_type is None:
        raise ValueError("create-field requires --type.")
    payload = {"field_name": args.field_name, "type": field_type}
    property_value = build_field_property(args, field_type=field_type, creating=True)
    if property_value is not None:
        payload["property"] = property_value
    payload = strip_field_property_if_forbidden(payload)
    response = request_json(
        method="POST",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/fields",
        token=token,
        body=payload,
    )
    ensure_success(response, api_alias="bitable_v1_app_table_field_create", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_field_create",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            field=normalize_field_item(normalize_json_object(response.get("data", {}).get("field", response.get("data")), name="field")),
        )
    )


def cmd_list_fields(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="list-fields",
    )
    response = request_json(
        method="GET",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/fields",
        token=token,
        query={
            "view_id": args.view_id,
            "page_size": args.page_size,
            "page_token": args.page_token,
        },
    )
    ensure_success(response, api_alias="bitable_v1_app_table_field_list", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_field_list",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            fields=[normalize_field_item(item) for item in response.get("data", {}).get("items", [])],
            has_more=response.get("data", {}).get("has_more", False),
            page_token=response.get("data", {}).get("page_token"),
        )
    )


def cmd_update_field(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="update-field",
    )
    field_type_input = resolve_field_type(args.type)
    property_value = None
    field_name, field_type, final_property = resolve_field_defaults(
        token=token,
        auth_mode=auth_mode,
        app_token=args.app_token,
        table_id=args.table_id,
        field_id=args.field_id,
        field_name=args.field_name,
        field_type=field_type_input,
        property_value=property_value,
    )
    final_property = build_field_property(
        args,
        field_type=field_type,
        base_property=final_property,
        creating=False,
    )
    payload: dict[str, object] = {"field_name": field_name, "type": field_type}
    if final_property is not None:
        payload["property"] = final_property
    payload = strip_field_property_if_forbidden(payload)
    response = request_json(
        method="PUT",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/fields/{args.field_id}",
        token=token,
        body=payload,
    )
    ensure_success(response, api_alias="bitable_v1_app_table_field_update", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_field_update",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            field_id=args.field_id,
            field=normalize_field_item(normalize_json_object(response.get("data", {}).get("field", response.get("data")), name="field")),
        )
    )


def cmd_delete_field(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="delete-field",
    )
    response = request_json(
        method="DELETE",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/fields/{args.field_id}",
        token=token,
    )
    ensure_success(response, api_alias="bitable_v1_app_table_field_delete", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_field_delete",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            field_id=args.field_id,
            success=True,
        )
    )
