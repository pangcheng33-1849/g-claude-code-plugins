#!/usr/bin/env python3
from __future__ import annotations

"""CLI facade for the standalone Feishu Sheets workflow helper.

The real logic lives in ``feishu_sheets_runtime`` modules. Keep this file thin
so command names stay stable even if the runtime is reorganized again.
"""

import argparse
from feishu_sheets_runtime.sheet_ops import (
    cmd_append_rows,
    cmd_clear_ranges,
    cmd_copy_worksheet,
    cmd_create_sheet,
    cmd_create_worksheet,
    cmd_delete_worksheet,
    cmd_find_cells,
    cmd_get_sheet_info,
    cmd_insert_rows,
    cmd_query_sheets,
    cmd_read_ranges,
    cmd_replace_cells,
    cmd_write_cells,
)


def add_auth_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-access-token", help="User access token. Use skill feishu-auth-and-scopes to obtain.")
    group.add_argument("--tenant-access-token", help="Tenant access token. Use skill feishu-auth-and-scopes to obtain.")


def add_value_arguments(parser: argparse.ArgumentParser) -> None:
    """Add --values-json, --values-file, --simple-values to a parser."""
    parser.add_argument("--values-json", help="Inline JSON 3D array of rich text cell data.")
    parser.add_argument("--values-file", help="Path to JSON file with 3D rich text cell data.")
    parser.add_argument(
        "--simple-values",
        help="Simplified 2D JSON array of strings/numbers, auto-converted to rich text segments.",
    )


def add_find_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common find/replace search arguments."""
    parser.add_argument("--find", required=True, help="Search string or regex pattern.")
    parser.add_argument("--range", help="Optional range to search within (e.g. A1:D10).")
    parser.add_argument("--match-case", action="store_true", help="Case-sensitive search.")
    parser.add_argument("--match-entire-cell", action="store_true", help="Match entire cell content only.")
    parser.add_argument("--search-by-regex", action="store_true", help="Treat --find as a regex.")
    parser.add_argument("--include-formulas", action="store_true", help="Search within formula text.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Standalone Feishu Sheets workflow helper. Real spreadsheet/worksheet/cell APIs, user token preferred."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- create-sheet --
    p = subparsers.add_parser("create-sheet", help="Create a new spreadsheet.")
    add_auth_arguments(p)
    p.add_argument("--title", required=True, help="Spreadsheet title.")
    p.add_argument("--folder-token", help="Drive folder token. Defaults to My Space. Not for wiki nodes.")
    p.add_argument("--wiki-parent-node", help="Wiki parent node token. Creates sheet as wiki sub-node instead of in Drive.")
    p.set_defaults(func=cmd_create_sheet)

    # -- get-sheet-info --
    p = subparsers.add_parser("get-sheet-info", help="Get spreadsheet metadata.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.set_defaults(func=cmd_get_sheet_info)

    # -- query-sheets --
    p = subparsers.add_parser("query-sheets", help="List worksheets in a spreadsheet. Returns sheet_id list.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.set_defaults(func=cmd_query_sheets)

    # -- create-worksheet --
    p = subparsers.add_parser("create-worksheet", help="Create a worksheet (tab) in a spreadsheet.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.add_argument("--title", required=True, help="Worksheet title.")
    p.add_argument("--index", type=int, help="Optional position index.")
    p.set_defaults(func=cmd_create_worksheet)

    # -- copy-worksheet --
    p = subparsers.add_parser("copy-worksheet", help="Copy a worksheet within the same spreadsheet.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.add_argument("--source-sheet-id", required=True, help="Sheet ID to copy.")
    p.add_argument("--title", help="Optional title for the new copy.")
    p.set_defaults(func=cmd_copy_worksheet)

    # -- delete-worksheet --
    p = subparsers.add_parser("delete-worksheet", help="Delete a worksheet from a spreadsheet.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.add_argument("--sheet-id", required=True)
    p.set_defaults(func=cmd_delete_worksheet)

    # -- read-ranges --
    p = subparsers.add_parser("read-ranges", help="Read cell values from one or more ranges.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.add_argument("--sheet-id", required=True)
    p.add_argument("--range", action="append", required=True, help="Range string (e.g. A1:C5). Repeatable.")
    p.add_argument("--datetime-render", help="Datetime render type.")
    p.add_argument("--value-render", help="Value render type.")
    p.set_defaults(func=cmd_read_ranges)

    # -- write-cells --
    p = subparsers.add_parser("write-cells", help="Write cell values to a range.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.add_argument("--sheet-id", required=True)
    p.add_argument("--range", required=True, help="Target range (e.g. A1:C3).")
    add_value_arguments(p)
    p.set_defaults(func=cmd_write_cells)

    # -- insert-rows --
    p = subparsers.add_parser("insert-rows", help="Insert rows at a range, shifting existing rows down.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.add_argument("--sheet-id", required=True)
    p.add_argument("--range", required=True, help="Target range (e.g. A1:C3).")
    add_value_arguments(p)
    p.set_defaults(func=cmd_insert_rows)

    # -- append-rows --
    p = subparsers.add_parser("append-rows", help="Append rows after the last non-empty row in a range.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.add_argument("--sheet-id", required=True)
    p.add_argument("--range", required=True, help="Target range (e.g. A1:C3).")
    add_value_arguments(p)
    p.set_defaults(func=cmd_append_rows)

    # -- clear-ranges --
    p = subparsers.add_parser("clear-ranges", help="Clear cell content in one or more ranges.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.add_argument("--sheet-id", required=True)
    p.add_argument("--range", action="append", required=True, help="Range to clear. Repeatable, max 10.")
    p.set_defaults(func=cmd_clear_ranges)

    # -- find-cells --
    p = subparsers.add_parser("find-cells", help="Find cells matching a string or regex.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.add_argument("--sheet-id", required=True)
    add_find_arguments(p)
    p.set_defaults(func=cmd_find_cells)

    # -- replace-cells --
    p = subparsers.add_parser("replace-cells", help="Find and replace cell content.")
    add_auth_arguments(p)
    p.add_argument("--spreadsheet-token", required=True)
    p.add_argument("--sheet-id", required=True)
    add_find_arguments(p)
    p.add_argument("--replacement", required=True, help="Replacement string.")
    p.set_defaults(func=cmd_replace_cells)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
