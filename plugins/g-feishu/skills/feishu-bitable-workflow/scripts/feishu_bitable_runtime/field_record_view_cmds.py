from __future__ import annotations

"""Compatibility facade for older imports of field/record/view command functions."""

from .field_cmds import cmd_create_field, cmd_delete_field, cmd_list_fields, cmd_update_field
from .record_cmds import (
    cmd_batch_create_records,
    cmd_batch_delete_records,
    cmd_batch_update_records,
    cmd_create_record,
    cmd_delete_record,
    cmd_list_records,
    cmd_update_record,
    normalize_record_filter,
)
from .view_cmds import cmd_create_view, cmd_delete_view, cmd_get_view, cmd_list_views, cmd_update_view

__all__ = [
    "normalize_record_filter",
    "cmd_create_field",
    "cmd_list_fields",
    "cmd_update_field",
    "cmd_delete_field",
    "cmd_create_record",
    "cmd_list_records",
    "cmd_update_record",
    "cmd_delete_record",
    "cmd_batch_create_records",
    "cmd_batch_update_records",
    "cmd_batch_delete_records",
    "cmd_get_view",
    "cmd_list_views",
    "cmd_create_view",
    "cmd_update_view",
    "cmd_delete_view",
]
