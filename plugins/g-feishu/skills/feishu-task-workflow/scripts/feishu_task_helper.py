#!/usr/bin/env python3
from __future__ import annotations

import argparse

from feishu_task_runtime.api import (
    add_member_args,
    add_token_args,
)
from feishu_task_runtime.common import fail
from feishu_task_runtime.task_cmds import (
    cmd_add_members,
    cmd_add_reminders,
    cmd_complete_task,
    cmd_create_task,
    cmd_delete_task,
    cmd_get_task,
    cmd_list_tasks,
    cmd_reopen_task,
    cmd_remove_members,
    cmd_update_task,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone Feishu task workflow helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_task = subparsers.add_parser("create-task", help="Create a real Feishu task via Task v2 API.")
    add_token_args(create_task)
    create_task.add_argument("--summary", required=True, help="Task summary.")
    create_task.add_argument("--description", help="Task description.")
    create_task.add_argument("--extra", help="Extra metadata string.")
    create_task.add_argument("--due", help="Due date/time. Supports YYYY-MM-DD or ISO datetime.")
    create_task.add_argument("--start", help="Start date/time. Supports YYYY-MM-DD or ISO datetime.")
    create_task.add_argument("--task-json", help="Inline JSON object merged into the create payload.")
    create_task.add_argument("--task-file", help="Path to a JSON file merged into the create payload.")
    add_member_args(create_task)
    create_task.add_argument("--tasklist", action="append", help="Tasklist mapping: tasklist_guid or tasklist_guid:section_guid.")
    create_task.add_argument("--docx-token", help="Optional docx source token.")
    create_task.add_argument("--docx-block-id", help="Optional docx source block id.")
    create_task.add_argument("--reminder-minute", type=int, action="append", help="Reminder relative_fire_minute.")
    create_task.add_argument("--client-token", help="Optional idempotency token.")
    create_task.add_argument("--mode", type=int, help="Optional task mode integer.")
    create_task.add_argument("--is-milestone", action="store_true", help="Create the task as a milestone.")
    create_task.set_defaults(func=cmd_create_task)

    update_task = subparsers.add_parser("update-task", help="Patch a real Feishu task.")
    add_token_args(update_task)
    update_task.add_argument("--task-guid", required=True, help="Task GUID.")
    update_task.add_argument("--task-json", help="Inline JSON object merged into the task patch body.")
    update_task.add_argument("--task-file", help="Path to a JSON file merged into the task patch body.")
    update_task.add_argument("--set-summary", help="New task summary.")
    update_task.add_argument("--set-description", help="New task description.")
    update_task.add_argument("--set-extra", help="New extra metadata string.")
    update_task.add_argument("--set-due", help="New due date/time.")
    update_task.add_argument("--clear-due", action="store_true", help="Clear due.")
    update_task.add_argument("--set-start", help="New start date/time.")
    update_task.add_argument("--clear-start", action="store_true", help="Clear start.")
    update_task.add_argument("--set-mode", type=int, help="Set task mode integer.")
    update_task.add_argument("--set-milestone", choices=["true", "false"], help="Set milestone flag.")
    update_task.add_argument("--set-completed-at", help="Explicit completed_at timestamp in milliseconds.")
    update_task.add_argument("--clear-completed", action="store_true", help="Reset completed_at to 0.")
    update_task.add_argument("--update-field", action="append", help="Explicit update_fields entry to include.")
    update_task.set_defaults(func=cmd_update_task)

    complete_task = subparsers.add_parser("complete-task", help="Mark a task as completed.")
    add_token_args(complete_task)
    complete_task.add_argument("--task-guid", required=True, help="Task GUID.")
    complete_task.set_defaults(func=cmd_complete_task)

    reopen_task = subparsers.add_parser("reopen-task", help="Reopen a completed task.")
    add_token_args(reopen_task)
    reopen_task.add_argument("--task-guid", required=True, help="Task GUID.")
    reopen_task.set_defaults(func=cmd_reopen_task)

    get_task = subparsers.add_parser("get-task", help="Get a task by GUID.")
    add_token_args(get_task)
    get_task.add_argument("--task-guid", required=True, help="Task GUID.")
    get_task.set_defaults(func=cmd_get_task)

    delete_task = subparsers.add_parser("delete-task", help="Delete a task by GUID.")
    add_token_args(delete_task)
    delete_task.add_argument("--task-guid", required=True, help="Task GUID.")
    delete_task.set_defaults(func=cmd_delete_task)

    list_tasks = subparsers.add_parser("list-tasks", help="List my tasks.")
    add_token_args(list_tasks)
    list_tasks.add_argument("--completed", choices=["true", "false"], help="Filter by completed state.")
    list_tasks.add_argument("--page-size", type=int, default=50, help="Page size. Defaults to 50.")
    list_tasks.add_argument("--page-token", help="Page token for pagination.")
    list_tasks.add_argument("--type", default="my_tasks", help="Task list type. Defaults to my_tasks.")
    list_tasks.set_defaults(func=cmd_list_tasks)

    add_members = subparsers.add_parser("add-members", help="Add task members.")
    add_token_args(add_members)
    add_members.add_argument("--task-guid", required=True, help="Task GUID.")
    add_member_args(add_members)
    add_members.add_argument("--client-token", help="Optional idempotency token.")
    add_members.set_defaults(func=cmd_add_members)

    remove_members = subparsers.add_parser("remove-members", help="Remove task members.")
    add_token_args(remove_members)
    remove_members.add_argument("--task-guid", required=True, help="Task GUID.")
    add_member_args(remove_members)
    remove_members.set_defaults(func=cmd_remove_members)

    add_reminders = subparsers.add_parser("add-reminders", help="Add task reminders.")
    add_token_args(add_reminders)
    add_reminders.add_argument("--task-guid", required=True, help="Task GUID.")
    add_reminders.add_argument(
        "--relative-fire-minute",
        type=int,
        action="append",
        help="Reminder relative_fire_minute. Repeat to add multiple reminders.",
    )
    add_reminders.set_defaults(func=cmd_add_reminders)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except ValueError as exc:
        fail(str(exc))


if __name__ == "__main__":
    main()
