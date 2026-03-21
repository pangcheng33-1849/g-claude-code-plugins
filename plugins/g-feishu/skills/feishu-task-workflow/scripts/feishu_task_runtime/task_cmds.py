from __future__ import annotations

"""Real Task v2 command handlers used by the task workflow CLI."""

import argparse
import uuid

from .api import (
    collect_members,
    ensure_success,
    normalize_api_result,
    parse_tasklist_spec,
    resolve_token,
    summarize_task,
    task_request,
)
from .common import current_timestamp_ms, fail, load_json_value, merge_objects, normalize_bool, parse_time_value, print_json


# These commands wrap the real Task v2 APIs. Keeping them together makes it
# easier to audit write semantics separately from the read-only helper layer.
def cmd_create_task(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="create-task",
    )
    task = load_json_value(args.task_json, args.task_file, default={})
    if not isinstance(task, dict):
        fail("create-task expects task JSON object.")
    task = dict(task)
    task["summary"] = args.summary
    if args.description is not None:
        task["description"] = args.description
    if args.extra is not None:
        task["extra"] = args.extra
    if args.due:
        task["due"] = parse_time_value(args.due, field="due")
    if args.start:
        task["start"] = parse_time_value(args.start, field="start")
    members, user_id_type = collect_members(args)
    if members:
        task["members"] = members
    if args.tasklist:
        task["tasklists"] = [parse_tasklist_spec(item) for item in args.tasklist]
    if args.docx_token or args.docx_block_id:
        if not (args.docx_token and args.docx_block_id):
            fail("docx_source requires both --docx-token and --docx-block-id.")
        task["docx_source"] = {"token": args.docx_token, "block_id": args.docx_block_id}
    if args.reminder_minute:
        task["reminders"] = [{"relative_fire_minute": minute} for minute in args.reminder_minute]
    if args.mode is not None:
        task["mode"] = args.mode
    if args.is_milestone:
        task["is_milestone"] = True
    body = {"summary": task.get("summary")}
    body = merge_objects(body, task)
    if "client_token" not in body:
        body["client_token"] = args.client_token or str(uuid.uuid4())
    response = task_request(
        method="POST",
        path="/task/v2/tasks",
        token=token,
        query={"user_id_type": user_id_type},
        body=body,
    )
    result = normalize_api_result(
        api_alias="task.v2.task.create",
        auth_mode=auth_mode,
        response=response,
        extra={"task": summarize_task(response.get("data", {}).get("task"))},
    )
    print_json(result)
    ensure_success(result)


def cmd_update_task(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="update-task",
    )
    task = load_json_value(args.task_json, args.task_file, default={})
    if not isinstance(task, dict):
        fail("update-task expects task JSON object.")
    task = dict(task)
    update_fields: list[str] = []

    def mark(field: str, value: object) -> None:
        task[field] = value
        if field not in update_fields:
            update_fields.append(field)

    if args.set_summary is not None:
        mark("summary", args.set_summary)
    if args.set_description is not None:
        mark("description", args.set_description)
    if args.set_extra is not None:
        mark("extra", args.set_extra)
    if args.set_due:
        mark("due", parse_time_value(args.set_due, field="due"))
    if args.clear_due:
        mark("due", None)
    if args.set_start:
        mark("start", parse_time_value(args.set_start, field="start"))
    if args.clear_start:
        mark("start", None)
    if args.set_mode is not None:
        mark("mode", args.set_mode)
    if args.set_milestone is not None:
        mark("is_milestone", normalize_bool(args.set_milestone))
    if args.set_completed_at is not None:
        mark("completed_at", args.set_completed_at)
    if args.clear_completed:
        mark("completed_at", "0")
    explicit_fields = args.update_field or []
    for field in explicit_fields:
        if field not in update_fields:
            update_fields.append(field)
    if not update_fields:
        fail("update-task needs at least one field change.")
    response = task_request(
        method="PATCH",
        path=f"/task/v2/tasks/{args.task_guid}",
        token=token,
        query={"user_id_type": args.user_id_type or "open_id"},
        body={"task": task, "update_fields": update_fields},
    )
    result = normalize_api_result(
        api_alias="task.v2.task.patch",
        auth_mode=auth_mode,
        response=response,
        extra={"task": summarize_task(response.get("data", {}).get("task")), "update_fields": update_fields},
    )
    print_json(result)
    ensure_success(result)


def cmd_complete_task(args: argparse.Namespace) -> None:
    args.set_completed_at = current_timestamp_ms()
    args.clear_completed = False
    args.set_summary = None
    args.set_description = None
    args.set_extra = None
    args.set_due = None
    args.clear_due = False
    args.set_start = None
    args.clear_start = False
    args.set_mode = None
    args.set_milestone = None
    args.task_json = None
    args.task_file = None
    args.update_field = ["completed_at"]
    cmd_update_task(args)


def cmd_reopen_task(args: argparse.Namespace) -> None:
    args.set_completed_at = None
    args.clear_completed = True
    args.set_summary = None
    args.set_description = None
    args.set_extra = None
    args.set_due = None
    args.clear_due = False
    args.set_start = None
    args.clear_start = False
    args.set_mode = None
    args.set_milestone = None
    args.task_json = None
    args.task_file = None
    args.update_field = ["completed_at"]
    cmd_update_task(args)


def cmd_get_task(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="get-task",
    )
    response = task_request(
        method="GET",
        path=f"/task/v2/tasks/{args.task_guid}",
        token=token,
        query={"user_id_type": args.user_id_type or "open_id"},
    )
    result = normalize_api_result(
        api_alias="task.v2.task.get",
        auth_mode=auth_mode,
        response=response,
        extra={"task": summarize_task(response.get("data", {}).get("task"))},
    )
    print_json(result)
    ensure_success(result)


def cmd_delete_task(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="delete-task",
    )
    response = task_request(
        method="DELETE",
        path=f"/task/v2/tasks/{args.task_guid}",
        token=token,
    )
    result = normalize_api_result(
        api_alias="task.v2.task.delete",
        auth_mode=auth_mode,
        response=response,
        extra={"task_guid": args.task_guid},
    )
    print_json(result)
    ensure_success(result)


def cmd_list_tasks(args: argparse.Namespace) -> None:
    if args.use_tenant_token or args.tenant_access_token:
        fail("list-tasks only supports user token according to Task v2 API. Pass --user-access-token. Use skill feishu-auth-and-scopes to obtain a user token.")
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=None,
        use_tenant_token=False,
        command_name="list-tasks",
        allow_tenant=False,
    )
    response = task_request(
        method="GET",
        path="/task/v2/tasks",
        token=token,
        query={
            "user_id_type": args.user_id_type or "open_id",
            "page_size": args.page_size,
            "page_token": args.page_token,
            "completed": normalize_bool(args.completed) if args.completed is not None else None,
            "type": args.type or "my_tasks",
        },
    )
    tasks = response.get("data", {}).get("items") or response.get("data", {}).get("tasks") or []
    result = normalize_api_result(
        api_alias="task.v2.task.list",
        auth_mode=auth_mode,
        response=response,
        extra={
            "task_count": len(tasks),
            "tasks": [summarize_task(task) for task in tasks],
            "has_more": response.get("data", {}).get("has_more"),
            "page_token": response.get("data", {}).get("page_token"),
        },
    )
    print_json(result)
    ensure_success(result)


def cmd_add_members(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="add-members",
    )
    members, user_id_type = collect_members(args)
    if not members:
        fail("add-members requires at least one --member or assignee/follower open id.")
    body: dict[str, object] = {"members": members}
    body["client_token"] = args.client_token or str(uuid.uuid4())
    response = task_request(
        method="POST",
        path=f"/task/v2/tasks/{args.task_guid}/add_members",
        token=token,
        query={"user_id_type": user_id_type},
        body=body,
    )
    result = normalize_api_result(
        api_alias="task.v2.task.add_members",
        auth_mode=auth_mode,
        response=response,
        extra={"task_guid": args.task_guid, "member_count": len(members)},
    )
    print_json(result)
    ensure_success(result)


def cmd_remove_members(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="remove-members",
    )
    members, user_id_type = collect_members(args)
    if not members:
        fail("remove-members requires at least one --member or assignee/follower open id.")
    body: dict[str, object] = {"members": members}
    response = task_request(
        method="POST",
        path=f"/task/v2/tasks/{args.task_guid}/remove_members",
        token=token,
        query={"user_id_type": user_id_type},
        body=body,
    )
    result = normalize_api_result(
        api_alias="task.v2.task.remove_members",
        auth_mode=auth_mode,
        response=response,
        extra={"task_guid": args.task_guid, "member_count": len(members)},
    )
    print_json(result)
    ensure_success(result)


def cmd_add_reminders(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="add-reminders",
    )
    if not args.relative_fire_minute:
        fail("add-reminders requires at least one --relative-fire-minute.")
    response = task_request(
        method="POST",
        path=f"/task/v2/tasks/{args.task_guid}/add_reminders",
        token=token,
        query={"user_id_type": args.user_id_type or "open_id"},
        body={
            "reminders": [{"relative_fire_minute": minute} for minute in args.relative_fire_minute],
        },
    )
    result = normalize_api_result(
        api_alias="task.v2.task.add_reminders",
        auth_mode=auth_mode,
        response=response,
        extra={"task_guid": args.task_guid, "reminder_count": len(args.relative_fire_minute)},
    )
    print_json(result)
    ensure_success(result)
