from __future__ import annotations

"""Command implementations for all Feishu Sheets operations."""

import argparse
import json

from .common import (
    convert_simple_values,
    ensure_success,
    fail,
    load_json_value,
    normalize_result,
    print_json,
    resolve_token,
    sheets_request,
)


# ---------------------------------------------------------------------------
# Spreadsheet-level commands
# ---------------------------------------------------------------------------


def cmd_create_sheet(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="create-sheet",
    )
    wiki_parent = getattr(args, "wiki_parent_node", None)
    if wiki_parent:
        # 先解析 parent node 获取 space_id
        node_resp = sheets_request(
            method="GET",
            path="/wiki/v2/spaces/get_node",
            token=token,
            query={"token": wiki_parent, "obj_type": "wiki"},
        )
        space_id = (node_resp.get("data") or {}).get("node", {}).get("space_id")
        if not space_id:
            fail(
                f"无法从 wiki node {wiki_parent} 解析 space_id。请确认 node token 正确且有权限。",
                api_alias="wiki_v2_get_node",
                auth_mode=auth_mode,
                response=node_resp,
            )
        # Wiki 节点下创建：走 wiki/v2 API
        body: dict[str, object] = {
            "obj_type": "sheet",
            "node_type": "origin",
            "parent_node_token": wiki_parent,
            "title": args.title,
        }
        response = sheets_request(method="POST", path=f"/wiki/v2/spaces/{space_id}/nodes", token=token, body=body)
        ensure_success(response, api_alias="wiki_v2_node_create_sheet", auth_mode=auth_mode)
        node = response.get("data", {}).get("node", {})
        print_json(
            normalize_result(
                api_alias="wiki_v2_node_create_sheet",
                auth_mode=auth_mode,
                response=response,
                spreadsheet_token=node.get("obj_token"),
                node_token=node.get("node_token"),
                wiki_note="表格已创建在 wiki 节点下。spreadsheet_token 为 obj_token，后续操作用此 token。",
            )
        )
    else:
        body = {"title": args.title}
        if args.folder_token:
            body["folder_token"] = args.folder_token
        response = sheets_request(method="POST", path="/sheets/v3/spreadsheets", token=token, body=body)
        ensure_success(response, api_alias="sheets_v3_spreadsheet_create", auth_mode=auth_mode)
        data = response.get("data", {})
        spreadsheet = data.get("spreadsheet", {})
        print_json(
            normalize_result(
                api_alias="sheets_v3_spreadsheet_create",
                auth_mode=auth_mode,
                response=response,
                spreadsheet_token=spreadsheet.get("spreadsheet_token"),
            )
        )


def cmd_get_sheet_info(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="get-sheet-info",
    )
    response = sheets_request(
        method="GET",
        path=f"/sheets/v3/spreadsheets/{args.spreadsheet_token}",
        token=token,
    )
    ensure_success(response, api_alias="sheets_v3_spreadsheet_get", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="sheets_v3_spreadsheet_get",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
        )
    )


def cmd_query_sheets(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="query-sheets",
    )
    response = sheets_request(
        method="GET",
        path=f"/sheets/v3/spreadsheets/{args.spreadsheet_token}/sheets/query",
        token=token,
    )
    ensure_success(response, api_alias="sheets_v3_sheets_query", auth_mode=auth_mode)
    sheets = response.get("data", {}).get("sheets", [])
    sheet_ids = [s.get("sheet_id") for s in sheets if s.get("sheet_id")]
    print_json(
        normalize_result(
            api_alias="sheets_v3_sheets_query",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
            sheet_ids=sheet_ids,
        )
    )


# ---------------------------------------------------------------------------
# Worksheet-level commands
# ---------------------------------------------------------------------------


def cmd_create_worksheet(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="create-worksheet",
    )
    body: dict[str, object] = {"title": args.title}
    if args.index is not None:
        body["index"] = args.index
    response = sheets_request(
        method="POST",
        path=f"/sheets/v3/spreadsheets/{args.spreadsheet_token}/sheets",
        token=token,
        body=body,
    )
    ensure_success(response, api_alias="sheets_v3_sheet_create", auth_mode=auth_mode)
    sheet = response.get("data", {}).get("sheet", {})
    print_json(
        normalize_result(
            api_alias="sheets_v3_sheet_create",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
            sheet_id=sheet.get("sheet_id"),
        )
    )


def cmd_copy_worksheet(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="copy-worksheet",
    )
    copy_req: dict[str, object] = {
        "source": {"sheetId": args.source_sheet_id},
        "destination": {},
    }
    if args.title:
        copy_req["destination"]["title"] = args.title
    body: dict[str, object] = {"requests": [{"copySheet": copy_req}]}
    response = sheets_request(
        method="POST",
        path=f"/sheets/v2/spreadsheets/{args.spreadsheet_token}/sheets_batch_update",
        token=token,
        body=body,
    )
    ensure_success(response, api_alias="sheets_v2_copy_sheet", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="sheets_v2_copy_sheet",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
        )
    )


def cmd_delete_worksheet(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="delete-worksheet",
    )
    body: dict[str, object] = {
        "requests": [{"deleteSheet": {"sheetId": args.sheet_id}}],
    }
    response = sheets_request(
        method="POST",
        path=f"/sheets/v2/spreadsheets/{args.spreadsheet_token}/sheets_batch_update",
        token=token,
        body=body,
    )
    ensure_success(response, api_alias="sheets_v2_delete_sheet", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="sheets_v2_delete_sheet",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
        )
    )


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------


def _resolve_values(args: argparse.Namespace) -> list[list[list[dict[str, object]]]]:
    """Resolve cell values from --values-json, --values-file, or --simple-values."""
    if getattr(args, "simple_values", None):
        raw = json.loads(args.simple_values)
        if not isinstance(raw, list):
            fail("--simple-values must be a JSON 2D array.")
        return convert_simple_values(raw)
    loaded = load_json_value(
        getattr(args, "values_json", None),
        getattr(args, "values_file", None),
        default=None,
    )
    if loaded is None:
        fail("Provide cell data via --values-json, --values-file, or --simple-values.")
    if not isinstance(loaded, list):
        fail("Cell values must be a JSON array (3D: rows -> cells -> segments).")
    return loaded


# ---------------------------------------------------------------------------
# Read / Write / Insert / Append / Clear
# ---------------------------------------------------------------------------


def cmd_read_ranges(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="read-ranges",
    )
    body: dict[str, object] = {"ranges": args.range}
    query: dict[str, object] = {}
    if args.datetime_render:
        query["datetime_render_option"] = args.datetime_render
    if args.value_render:
        query["value_render_option"] = args.value_render
    response = sheets_request(
        method="POST",
        path=f"/sheets/v3/spreadsheets/{args.spreadsheet_token}/sheets/{args.sheet_id}/values/batch_get",
        token=token,
        query=query or None,
        body=body,
    )
    ensure_success(response, api_alias="sheets_v3_values_batch_get", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="sheets_v3_values_batch_get",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
            sheet_id=args.sheet_id,
        )
    )


def cmd_write_cells(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="write-cells",
    )
    values = _resolve_values(args)
    body: dict[str, object] = {
        "value_ranges": [
            {"range": args.range, "values": values},
        ],
    }
    response = sheets_request(
        method="POST",
        path=f"/sheets/v3/spreadsheets/{args.spreadsheet_token}/sheets/{args.sheet_id}/values/batch_update",
        token=token,
        body=body,
    )
    ensure_success(response, api_alias="sheets_v3_values_batch_update", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="sheets_v3_values_batch_update",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
            sheet_id=args.sheet_id,
        )
    )


def cmd_insert_rows(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="insert-rows",
    )
    values = _resolve_values(args)
    body: dict[str, object] = {"values": values}
    response = sheets_request(
        method="POST",
        path=f"/sheets/v3/spreadsheets/{args.spreadsheet_token}/sheets/{args.sheet_id}/values/{args.range}/insert",
        token=token,
        body=body,
    )
    ensure_success(response, api_alias="sheets_v3_values_insert", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="sheets_v3_values_insert",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
            sheet_id=args.sheet_id,
        )
    )


def cmd_append_rows(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="append-rows",
    )
    values = _resolve_values(args)
    body: dict[str, object] = {"values": values}
    response = sheets_request(
        method="POST",
        path=f"/sheets/v3/spreadsheets/{args.spreadsheet_token}/sheets/{args.sheet_id}/values/{args.range}/append",
        token=token,
        body=body,
    )
    ensure_success(response, api_alias="sheets_v3_values_append", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="sheets_v3_values_append",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
            sheet_id=args.sheet_id,
        )
    )


def cmd_clear_ranges(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="clear-ranges",
    )
    body: dict[str, object] = {"ranges": args.range}
    response = sheets_request(
        method="POST",
        path=f"/sheets/v3/spreadsheets/{args.spreadsheet_token}/sheets/{args.sheet_id}/values/batch_clear",
        token=token,
        body=body,
    )
    ensure_success(response, api_alias="sheets_v3_values_batch_clear", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="sheets_v3_values_batch_clear",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
            sheet_id=args.sheet_id,
        )
    )


# ---------------------------------------------------------------------------
# Find / Replace
# ---------------------------------------------------------------------------


def _build_find_body(args: argparse.Namespace, *, is_replace: bool = False) -> dict[str, object]:
    find_condition: dict[str, object] = {}
    if args.range:
        find_condition["range"] = args.range
    if args.match_case:
        find_condition["match_case"] = True
    if args.match_entire_cell:
        find_condition["match_entire_cell"] = True
    if args.search_by_regex:
        find_condition["search_by_regex"] = True
    if args.include_formulas:
        find_condition["include_formulas"] = True
    body: dict[str, object] = {
        "find_condition": find_condition,
        "find": args.find,
    }
    return body


def cmd_find_cells(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="find-cells",
    )
    body = _build_find_body(args)
    response = sheets_request(
        method="POST",
        path=f"/sheets/v3/spreadsheets/{args.spreadsheet_token}/sheets/{args.sheet_id}/find",
        token=token,
        body=body,
    )
    ensure_success(response, api_alias="sheets_v3_find", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="sheets_v3_find",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
            sheet_id=args.sheet_id,
        )
    )


def cmd_replace_cells(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        command_name="replace-cells",
    )
    body = _build_find_body(args)
    body["replacement"] = args.replacement
    response = sheets_request(
        method="POST",
        path=f"/sheets/v3/spreadsheets/{args.spreadsheet_token}/sheets/{args.sheet_id}/replace",
        token=token,
        body=body,
    )
    ensure_success(response, api_alias="sheets_v3_replace", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="sheets_v3_replace",
            auth_mode=auth_mode,
            response=response,
            spreadsheet_token=args.spreadsheet_token,
            sheet_id=args.sheet_id,
        )
    )
