from __future__ import annotations

"""Compatibility facade for older imports of app/table command functions."""

from .app_cmds import cmd_copy_app, cmd_create_app, cmd_get_app, cmd_list_apps, cmd_update_app
from .table_cmds import (
    cmd_batch_create_tables,
    cmd_batch_delete_tables,
    cmd_create_table,
    cmd_delete_table,
    cmd_list_tables,
    cmd_update_table,
)

__all__ = [
    "cmd_create_app",
    "cmd_get_app",
    "cmd_list_apps",
    "cmd_update_app",
    "cmd_copy_app",
    "cmd_create_table",
    "cmd_list_tables",
    "cmd_update_table",
    "cmd_delete_table",
    "cmd_batch_create_tables",
    "cmd_batch_delete_tables",
]
