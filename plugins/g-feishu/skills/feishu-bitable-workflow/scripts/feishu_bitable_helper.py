#!/usr/bin/env python3
from __future__ import annotations

"""CLI facade for the standalone Feishu Bitable workflow helper.

The real logic lives in ``feishu_bitable_runtime`` modules. Keep this file thin
so command names stay stable even if the runtime is reorganized again.
"""

import argparse
from feishu_bitable_runtime.app_table_cmds import (
    cmd_batch_create_tables,
    cmd_batch_delete_tables,
    cmd_copy_app,
    cmd_create_app,
    cmd_create_table,
    cmd_delete_table,
    cmd_get_app,
    cmd_list_apps,
    cmd_list_tables,
    cmd_update_app,
    cmd_update_table,
)
from feishu_bitable_runtime.field_record_view_cmds import (
    cmd_batch_create_records,
    cmd_batch_delete_records,
    cmd_batch_update_records,
    cmd_create_field,
    cmd_create_record,
    cmd_create_view,
    cmd_delete_field,
    cmd_delete_record,
    cmd_delete_view,
    cmd_get_view,
    cmd_list_fields,
    cmd_list_records,
    cmd_list_views,
    cmd_update_field,
    cmd_update_record,
    cmd_update_view,
)


def add_auth_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--user-access-token", help="User token. Preferred for all real Bitable operations.")
    parser.add_argument("--tenant-access-token", help="Tenant token. Only use when you explicitly want app identity.")
    parser.add_argument(
        "--use-tenant-token",
        action="store_true",
        help="Prefer MY_LARK_TENANT_ACCESS_TOKEN from the environment instead of the default user-token-first behavior.",
    )


def add_field_property_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--property-json",
        help="Inline JSON object for raw field property. Takes precedence over convenience options.",
    )
    parser.add_argument(
        "--property-file",
        help="Path to JSON file with raw field property. Takes precedence over convenience options.",
    )
    parser.add_argument(
        "--option",
        dest="options",
        action="append",
        help="Repeatable select option name. Supported for single_select and multi_select.",
    )
    parser.add_argument("--options-json", help="Inline JSON array for select options.")
    parser.add_argument("--options-file", help="Path to JSON file with select options.")
    parser.add_argument("--formatter", help="Number field formatter. Supported for number fields.")
    parser.add_argument("--date-formatter", help="Date field formatter. Supported for datetime/date fields.")
    parser.add_argument("--auto-fill", help="true/false for datetime auto-fill behavior.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Standalone Feishu Bitable workflow helper. Real app/table/field/record/view APIs, user token preferred. All successful write operations return the most relevant Bitable link(s)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    app_create = subparsers.add_parser("create-app", help="Create a Bitable app.")
    add_auth_arguments(app_create)
    app_create.add_argument("--name", required=True, help="Bitable app name.")
    app_create.add_argument("--folder-token", help="Optional folder token. Defaults to My Space.")
    app_create.set_defaults(func=cmd_create_app)

    app_get = subparsers.add_parser("get-app", help="Get app metadata by app token.")
    add_auth_arguments(app_get)
    app_get.add_argument("--app-token", required=True)
    app_get.set_defaults(func=cmd_get_app)

    app_list = subparsers.add_parser("list-apps", help="List Bitable apps visible under a folder or My Space.")
    add_auth_arguments(app_list)
    app_list.add_argument("--folder-token", help="Optional folder token.")
    app_list.add_argument("--page-size", type=int, default=50)
    app_list.add_argument("--page-token")
    app_list.set_defaults(func=cmd_list_apps)

    app_update = subparsers.add_parser("update-app", help="Update app metadata.")
    add_auth_arguments(app_update)
    app_update.add_argument("--app-token", required=True)
    app_update.add_argument("--name", help="New app name.")
    app_update.add_argument("--is-advanced", help="true/false to toggle advanced permission mode.")
    app_update.set_defaults(func=cmd_update_app)

    app_copy = subparsers.add_parser("copy-app", help="Copy a Bitable app.")
    add_auth_arguments(app_copy)
    app_copy.add_argument("--app-token", required=True)
    app_copy.add_argument("--name", required=True, help="New copied app name.")
    app_copy.add_argument("--folder-token", help="Optional target folder token.")
    app_copy.set_defaults(func=cmd_copy_app)

    table_create = subparsers.add_parser("create-table", help="Create a table in an app.")
    add_auth_arguments(table_create)
    table_create.add_argument("--app-token", required=True)
    table_create.add_argument("--name", required=True, help="Table name.")
    table_create.add_argument("--fields-json", help="Inline JSON array of field definitions.")
    table_create.add_argument("--fields-file", help="Path to JSON file containing field definitions.")
    table_create.set_defaults(func=cmd_create_table)

    table_list = subparsers.add_parser("list-tables", help="List tables in an app.")
    add_auth_arguments(table_list)
    table_list.add_argument("--app-token", required=True)
    table_list.add_argument("--page-size", type=int, default=50)
    table_list.add_argument("--page-token")
    table_list.set_defaults(func=cmd_list_tables)

    table_update = subparsers.add_parser("update-table", help="Update a table name.")
    add_auth_arguments(table_update)
    table_update.add_argument("--app-token", required=True)
    table_update.add_argument("--table-id", required=True)
    table_update.add_argument("--name", required=True, help="New table name.")
    table_update.set_defaults(func=cmd_update_table)

    table_delete = subparsers.add_parser("delete-table", help="Delete a table.")
    add_auth_arguments(table_delete)
    table_delete.add_argument("--app-token", required=True)
    table_delete.add_argument("--table-id", required=True)
    table_delete.set_defaults(func=cmd_delete_table)

    table_batch_create = subparsers.add_parser("batch-create-tables", help="Create multiple tables at once.")
    add_auth_arguments(table_batch_create)
    table_batch_create.add_argument("--app-token", required=True)
    table_batch_create.add_argument("--tables-json", help="Inline JSON array of tables.")
    table_batch_create.add_argument("--tables-file", help="Path to JSON file with tables.")
    table_batch_create.set_defaults(func=cmd_batch_create_tables)

    table_batch_delete = subparsers.add_parser("batch-delete-tables", help="Delete multiple tables at once.")
    add_auth_arguments(table_batch_delete)
    table_batch_delete.add_argument("--app-token", required=True)
    table_batch_delete.add_argument("--table-id", dest="table_ids", action="append", help="Repeatable table id.")
    table_batch_delete.add_argument("--table-ids-json", help="Inline JSON array of table ids.")
    table_batch_delete.add_argument("--table-ids-file", help="Path to JSON file with table ids.")
    table_batch_delete.set_defaults(func=cmd_batch_delete_tables)

    field_create = subparsers.add_parser(
        "create-field",
        help="Create a field in a table. Common aliases: text, number, single_select, multi_select, datetime, checkbox, person, phone, link, attachment.",
    )
    add_auth_arguments(field_create)
    field_create.add_argument("--app-token", required=True)
    field_create.add_argument("--table-id", required=True)
    field_create.add_argument("--field-name", required=True)
    field_create.add_argument(
        "--type",
        required=True,
        help="Field type alias or raw integer type. Recommended aliases: text, number, single_select, multi_select, datetime, checkbox, person, phone, link, attachment.",
    )
    add_field_property_arguments(field_create)
    field_create.set_defaults(func=cmd_create_field)

    field_list = subparsers.add_parser("list-fields", help="List fields in a table.")
    add_auth_arguments(field_list)
    field_list.add_argument("--app-token", required=True)
    field_list.add_argument("--table-id", required=True)
    field_list.add_argument("--view-id")
    field_list.add_argument("--page-size", type=int, default=50)
    field_list.add_argument("--page-token")
    field_list.set_defaults(func=cmd_list_fields)

    field_update = subparsers.add_parser(
        "update-field",
        help="Update a field. Missing values are auto-filled from the current schema. Supports the same common aliases as create-field.",
    )
    add_auth_arguments(field_update)
    field_update.add_argument("--app-token", required=True)
    field_update.add_argument("--table-id", required=True)
    field_update.add_argument("--field-id", required=True)
    field_update.add_argument("--field-name")
    field_update.add_argument(
        "--type",
        help="Field type alias or raw integer type. Recommended aliases: text, number, single_select, multi_select, datetime, checkbox, person, phone, link, attachment.",
    )
    add_field_property_arguments(field_update)
    field_update.set_defaults(func=cmd_update_field)

    field_delete = subparsers.add_parser("delete-field", help="Delete a field.")
    add_auth_arguments(field_delete)
    field_delete.add_argument("--app-token", required=True)
    field_delete.add_argument("--table-id", required=True)
    field_delete.add_argument("--field-id", required=True)
    field_delete.set_defaults(func=cmd_delete_field)

    record_create = subparsers.add_parser(
        "create-record",
        help="Create a single record. Common field values are normalized for text, number, single_select, multi_select, datetime, checkbox, person, phone, link, and attachment.",
    )
    add_auth_arguments(record_create)
    record_create.add_argument("--app-token", required=True)
    record_create.add_argument("--table-id", required=True)
    record_create.add_argument("--fields-json", required=True, help="Inline JSON object of field values.")
    record_create.add_argument("--fields-file", help="Optional JSON file; overrides inline when also set.")
    record_create.set_defaults(func=cmd_create_record)

    record_list = subparsers.add_parser(
        "list-records",
        help="Search/list records using the records/search API. Returns both normalized records and raw records.",
    )
    add_auth_arguments(record_list)
    record_list.add_argument("--app-token", required=True)
    record_list.add_argument("--table-id", required=True)
    record_list.add_argument("--view-id")
    record_list.add_argument("--field-names-json", help="Inline JSON array of field names to return.")
    record_list.add_argument("--field-names-file", help="Path to JSON file with field names.")
    record_list.add_argument("--filter-json", help="Inline JSON filter object.")
    record_list.add_argument("--filter-file", help="Path to JSON file with filter object.")
    record_list.add_argument("--sort-json", help="Inline JSON array of sort clauses.")
    record_list.add_argument("--sort-file", help="Path to JSON file with sort clauses.")
    record_list.add_argument("--automatic-fields", help="true/false to include automatic metadata fields.")
    record_list.add_argument("--page-size", type=int, default=50)
    record_list.add_argument("--page-token")
    record_list.set_defaults(func=cmd_list_records)

    record_update = subparsers.add_parser(
        "update-record",
        help="Update a single record. Common field values are normalized before write.",
    )
    add_auth_arguments(record_update)
    record_update.add_argument("--app-token", required=True)
    record_update.add_argument("--table-id", required=True)
    record_update.add_argument("--record-id", required=True)
    record_update.add_argument("--fields-json", required=True, help="Inline JSON object of fields to update.")
    record_update.add_argument("--fields-file", help="Optional JSON file; overrides inline when also set.")
    record_update.set_defaults(func=cmd_update_record)

    record_delete = subparsers.add_parser("delete-record", help="Delete a single record.")
    add_auth_arguments(record_delete)
    record_delete.add_argument("--app-token", required=True)
    record_delete.add_argument("--table-id", required=True)
    record_delete.add_argument("--record-id", required=True)
    record_delete.set_defaults(func=cmd_delete_record)

    record_batch_create = subparsers.add_parser(
        "batch-create-records",
        help="Create multiple records at once. Common field values are normalized before write.",
    )
    add_auth_arguments(record_batch_create)
    record_batch_create.add_argument("--app-token", required=True)
    record_batch_create.add_argument("--table-id", required=True)
    record_batch_create.add_argument("--records-json", help="Inline JSON array of records.")
    record_batch_create.add_argument("--records-file", help="Path to JSON file with records.")
    record_batch_create.set_defaults(func=cmd_batch_create_records)

    record_batch_update = subparsers.add_parser(
        "batch-update-records",
        help="Update multiple records at once. Common field values are normalized before write.",
    )
    add_auth_arguments(record_batch_update)
    record_batch_update.add_argument("--app-token", required=True)
    record_batch_update.add_argument("--table-id", required=True)
    record_batch_update.add_argument("--records-json", help="Inline JSON array of record updates.")
    record_batch_update.add_argument("--records-file", help="Path to JSON file with record updates.")
    record_batch_update.set_defaults(func=cmd_batch_update_records)

    record_batch_delete = subparsers.add_parser("batch-delete-records", help="Delete multiple records at once.")
    add_auth_arguments(record_batch_delete)
    record_batch_delete.add_argument("--app-token", required=True)
    record_batch_delete.add_argument("--table-id", required=True)
    record_batch_delete.add_argument("--record-id", dest="record_ids", action="append", help="Repeatable record id.")
    record_batch_delete.add_argument("--record-ids-json", help="Inline JSON array of record ids.")
    record_batch_delete.add_argument("--record-ids-file", help="Path to JSON file with record ids.")
    record_batch_delete.set_defaults(func=cmd_batch_delete_records)

    view_get = subparsers.add_parser("get-view", help="Get an existing view.")
    add_auth_arguments(view_get)
    view_get.add_argument("--app-token", required=True)
    view_get.add_argument("--table-id", required=True)
    view_get.add_argument("--view-id", required=True)
    view_get.set_defaults(func=cmd_get_view)

    view_create = subparsers.add_parser("create-view", help="Create a view in a table.")
    add_auth_arguments(view_create)
    view_create.add_argument("--app-token", required=True)
    view_create.add_argument("--table-id", required=True)
    view_create.add_argument("--view-name", required=True)
    view_create.add_argument("--view-type", default="grid", help="View type. Default: grid.")
    view_create.set_defaults(func=cmd_create_view)

    view_list = subparsers.add_parser("list-views", help="List views in a table.")
    add_auth_arguments(view_list)
    view_list.add_argument("--app-token", required=True)
    view_list.add_argument("--table-id", required=True)
    view_list.add_argument("--page-size", type=int, default=50)
    view_list.add_argument("--page-token")
    view_list.set_defaults(func=cmd_list_views)

    view_update = subparsers.add_parser("update-view", help="Update an existing view name.")
    add_auth_arguments(view_update)
    view_update.add_argument("--app-token", required=True)
    view_update.add_argument("--table-id", required=True)
    view_update.add_argument("--view-id", required=True)
    view_update.add_argument("--view-name", required=True)
    view_update.set_defaults(func=cmd_update_view)

    view_delete = subparsers.add_parser("delete-view", help="Delete an existing view.")
    add_auth_arguments(view_delete)
    view_delete.add_argument("--app-token", required=True)
    view_delete.add_argument("--table-id", required=True)
    view_delete.add_argument("--view-id", required=True)
    view_delete.set_defaults(func=cmd_delete_view)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
