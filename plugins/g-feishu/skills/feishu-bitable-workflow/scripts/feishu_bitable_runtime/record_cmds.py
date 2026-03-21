from __future__ import annotations

"""Record CRUD commands plus filter normalization for Bitable tables."""

import argparse

from .api import USER_ID_TYPE, ensure_success, normalize_result, request_json, resolve_token
from .common import fail, load_json_value, load_string_list, normalize_json_list, normalize_json_object, parse_bool, print_json
from .record_normalization import (
    normalize_record_batch_input,
    normalize_record_fields,
    normalize_record_output_item,
    normalize_record_output_list,
)
from .schema_ops import load_table_schema_map


def normalize_record_filter(filter_value: object | None) -> object | None:
    if not isinstance(filter_value, dict):
        return filter_value
    conditions = filter_value.get("conditions")
    if not isinstance(conditions, list):
        return filter_value
    normalized_conditions = []
    for condition in conditions:
        if not isinstance(condition, dict):
            normalized_conditions.append(condition)
            continue
        if condition.get("operator") in {"isEmpty", "isNotEmpty"} and "value" not in condition:
            updated = dict(condition)
            updated["value"] = []
            normalized_conditions.append(updated)
        else:
            normalized_conditions.append(condition)
    updated_filter = dict(filter_value)
    updated_filter["conditions"] = normalized_conditions
    return updated_filter


def cmd_create_record(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="create-record",
    )
    schema_map = load_table_schema_map(token=token, auth_mode=auth_mode, app_token=args.app_token, table_id=args.table_id)
    fields = normalize_json_object(load_json_value(args.fields_json, args.fields_file, default={}), name="fields")
    normalized_fields = normalize_record_fields(fields, schema_map)
    response = request_json(
        method="POST",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/records",
        token=token,
        query={"user_id_type": USER_ID_TYPE},
        body={"fields": normalized_fields},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_record_create", auth_mode=auth_mode)
    record_raw = normalize_json_object(response.get("data", {}).get("record", {}), name="record")
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_record_create",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            record=normalize_record_output_item(record_raw, schema_map),
            record_raw=record_raw,
            record_id=record_raw.get("record_id"),
        )
    )


def cmd_list_records(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="list-records",
    )
    schema_map = load_table_schema_map(token=token, auth_mode=auth_mode, app_token=args.app_token, table_id=args.table_id)
    field_names = load_json_value(args.field_names_json, args.field_names_file, default=None)
    sort_value = load_json_value(args.sort_json, args.sort_file, default=None)
    filter_value = load_json_value(args.filter_json, args.filter_file, default=None)
    payload: dict[str, object] = {}
    if args.view_id:
        payload["view_id"] = args.view_id
    if field_names:
        payload["field_names"] = normalize_json_list(field_names, name="field_names")
    if sort_value:
        payload["sort"] = normalize_json_list(sort_value, name="sort")
    if filter_value:
        payload["filter"] = normalize_record_filter(normalize_json_object(filter_value, name="filter"))
    if args.automatic_fields is not None:
        payload["automatic_fields"] = parse_bool(args.automatic_fields)
    response = request_json(
        method="POST",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/records/search",
        token=token,
        query={
            "page_size": args.page_size,
            "page_token": args.page_token,
            "user_id_type": USER_ID_TYPE,
        },
        body=payload,
    )
    ensure_success(response, api_alias="bitable_v1_app_table_record_search", auth_mode=auth_mode)
    records_raw = response.get("data", {}).get("items", [])
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_record_search",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            records=normalize_record_output_list(records_raw, schema_map),
            records_raw=records_raw,
            has_more=response.get("data", {}).get("has_more", False),
            page_token=response.get("data", {}).get("page_token"),
            total=response.get("data", {}).get("total"),
        )
    )


def cmd_update_record(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="update-record",
    )
    schema_map = load_table_schema_map(token=token, auth_mode=auth_mode, app_token=args.app_token, table_id=args.table_id)
    fields = normalize_json_object(load_json_value(args.fields_json, args.fields_file, default={}), name="fields")
    normalized_fields = normalize_record_fields(fields, schema_map)
    response = request_json(
        method="PUT",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/records/{args.record_id}",
        token=token,
        query={"user_id_type": USER_ID_TYPE},
        body={"fields": normalized_fields},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_record_update", auth_mode=auth_mode)
    record_raw = normalize_json_object(response.get("data", {}).get("record", {}), name="record")
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_record_update",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            record_id=args.record_id,
            record=normalize_record_output_item(record_raw, schema_map),
            record_raw=record_raw,
        )
    )


def cmd_delete_record(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="delete-record",
    )
    response = request_json(
        method="DELETE",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/records/{args.record_id}",
        token=token,
    )
    ensure_success(response, api_alias="bitable_v1_app_table_record_delete", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_record_delete",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            record_id=args.record_id,
            success=True,
        )
    )


def cmd_batch_create_records(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="batch-create-records",
    )
    schema_map = load_table_schema_map(token=token, auth_mode=auth_mode, app_token=args.app_token, table_id=args.table_id)
    records = normalize_json_list(load_json_value(args.records_json, args.records_file, default=[]), name="records")
    if not records:
        fail("batch-create-records requires at least one record.")
    normalized_records = normalize_record_batch_input(records, schema_map)
    response = request_json(
        method="POST",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/records/batch_create",
        token=token,
        query={"user_id_type": USER_ID_TYPE},
        body={"records": normalized_records},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_record_batch_create", auth_mode=auth_mode)
    records_raw = response.get("data", {}).get("records", [])
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_record_batch_create",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            records=normalize_record_output_list(records_raw, schema_map),
            records_raw=records_raw,
        )
    )


def cmd_batch_update_records(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="batch-update-records",
    )
    schema_map = load_table_schema_map(token=token, auth_mode=auth_mode, app_token=args.app_token, table_id=args.table_id)
    records = normalize_json_list(load_json_value(args.records_json, args.records_file, default=[]), name="records")
    if not records:
        fail("batch-update-records requires at least one record.")
    normalized_records = normalize_record_batch_input(records, schema_map)
    response = request_json(
        method="POST",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/records/batch_update",
        token=token,
        query={"user_id_type": USER_ID_TYPE},
        body={"records": normalized_records},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_record_batch_update", auth_mode=auth_mode)
    records_raw = response.get("data", {}).get("records", [])
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_record_batch_update",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            records=normalize_record_output_list(records_raw, schema_map),
            records_raw=records_raw,
        )
    )


def cmd_batch_delete_records(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,

        command_name="batch-delete-records",
    )
    record_ids = load_string_list(args.record_ids, args.record_ids_json, args.record_ids_file, name="record_ids")
    if not record_ids:
        fail("batch-delete-records requires at least one record id.")
    response = request_json(
        method="POST",
        path=f"/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/records/batch_delete",
        token=token,
        body={"records": record_ids},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_record_batch_delete", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="bitable_v1_app_table_record_batch_delete",
            auth_mode=auth_mode,
            response=response,
            app_token=args.app_token,
            table_id=args.table_id,
            record_ids=record_ids,
            success=True,
        )
    )
