from __future__ import annotations

"""Import-doc command implementation."""

import argparse
import json
import pathlib

from .command_aux_ops import (
    build_import_decision,
    should_auto_grant_default_access,
)
from .common import (
    build_web_link_notice,
    dedupe_strings,
    print_json,
    read_task_state,
    resolve_contact_email,
    resolve_task_state_dir,
    write_task_state,
)
from .document_ops import (
    create_import_task,
    decode_import_extra,
    grant_permission_member,
    infer_file_extension,
    poll_import_task,
    resolve_bearer_token,
    upload_import_source_file,
)
from .media_ops import build_failure_hints


def cmd_import_doc(args: argparse.Namespace) -> None:
    bearer_token, auth_mode = resolve_bearer_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
    )
    state_dir = resolve_task_state_dir(args.state_dir)
    grant_email = resolve_contact_email(args.grant_email)
    try:
        if args.task_id:
            saved_state = read_task_state(args.task_id, args.state_dir)
            import_result = poll_import_task(args.task_id, bearer_token, timeout_seconds=args.timeout_seconds)
            state_payload = {
                **(saved_state or {}),
                "status": "completed",
                "import_result": import_result,
                "grant_email": grant_email,
            }
            state_path = write_task_state(args.task_id, state_payload, args.state_dir)
            output_result = {
                "success": True,
                "auth_mode": auth_mode,
                "task_id": args.task_id,
                "task_kind": (saved_state or {}).get("task_kind", "import"),
                "task_state_path": str(state_path),
                "state_dir": str(state_dir),
                "saved_state": saved_state or {},
                "import_result": import_result,
            }
            imported_url = import_result.get("url")
            if not isinstance(imported_url, str) or not imported_url.strip():
                output_result["web_link_notice"] = build_web_link_notice(resource_kind="document")
            if args.output:
                pathlib.Path(args.output).write_text(json.dumps(output_result, ensure_ascii=True, indent=2), encoding="utf-8")
                output_result["output"] = args.output
            print_json(output_result)
            return

        if not args.input_file:
            raise SystemExit("--input-file is required unless --task-id is provided")
        file_path = pathlib.Path(args.input_file)
        if not file_path.is_file():
            raise SystemExit(f"input file does not exist: {file_path}")
        mount_key = args.mount_key if args.mount_key is not None else (args.folder_token if args.folder_token is not None else "")
        file_extension = infer_file_extension(file_path, args.file_extension)
        routing_decision = build_import_decision(input_file=file_path, file_extension=file_extension, target_type=args.type)
        file_size = file_path.stat().st_size
        async_reason = "explicit_async" if args.async_mode else ("auto_threshold" if file_size >= args.async_threshold_bytes else "inline_wait")
        submit_async = bool(args.async_mode or file_size >= args.async_threshold_bytes)
        upload_result = upload_import_source_file(
            file_path,
            bearer_token,
            target_type=args.type,
            file_extension=file_extension,
        )
        import_ticket = create_import_task(
            file_extension=file_extension,
            file_token=str(upload_result["file_token"]),
            target_type=args.type,
            mount_key=mount_key,
            bearer_token=bearer_token,
            file_name=args.file_name or file_path.stem,
        )
        state_payload = {
            "task_kind": "import",
            "status": "submitted",
            "auth_mode": auth_mode,
            "routing_decision": routing_decision,
            "input_file": str(file_path),
            "file_extension": file_extension,
            "target_type": args.type,
            "mount_key": mount_key,
            "mount_type": 1,
            "upload_result": upload_result,
            "grant_email": grant_email,
            "async_decision": async_reason,
        }
        state_path = write_task_state(import_ticket, state_payload, args.state_dir)
        if submit_async:
            async_result = {
                "success": True,
                "submitted": True,
                "async_mode": True,
                "async_decision": async_reason,
                "auth_mode": auth_mode,
                "routing_decision": routing_decision,
                "input_file": str(file_path),
                "file_extension": file_extension,
                "target_type": args.type,
                "mount_key": mount_key,
                "mount_type": 1,
                "ticket": import_ticket,
                "task_id": import_ticket,
                "task_kind": "import",
                "state_dir": str(state_dir),
                "task_state_path": str(state_path),
                "grant_email": grant_email,
                "next_step": "使用 import-doc --task-id <ticket> 继续查询或收取导入结果。",
            }
            if args.output:
                pathlib.Path(args.output).write_text(json.dumps(async_result, ensure_ascii=True, indent=2), encoding="utf-8")
                async_result["output"] = args.output
            print_json(async_result)
            return

        import_result = poll_import_task(import_ticket, bearer_token, timeout_seconds=args.timeout_seconds)
        permission_grant_result: dict[str, object] = {}
        permission_warnings: list[str] = []
        imported_token = import_result.get("token")
        if should_auto_grant_default_access(auth_mode):
            if isinstance(imported_token, str) and imported_token and grant_email:
                try:
                    permission_grant_result = grant_permission_member(
                        token=imported_token,
                        doc_type=args.type,
                        member_id=grant_email,
                        member_type="email",
                        bearer_token=bearer_token,
                        perm="full_access",
                        need_notification=False,
                    )
                except SystemExit as exc:
                    permission_warnings.append(f"已完成导入，但自动授权 full_access 给 {grant_email} 失败：{exc}")
            elif not grant_email:
                permission_warnings.append("当前使用 tenant token 导入，但未读取到邮箱，未自动授予 full_access。请传 --grant-email 或设置 MY_LARK_EMAIL。")
        extra_details = decode_import_extra(import_result.get("extra"))
        warnings = [
            item["message"]
            for item in extra_details
            if isinstance(item, dict)
            and isinstance(item.get("message"), str)
            and item.get("severity") == "warning"
        ]
        result = {
            "success": True,
            "auth_mode": auth_mode,
            "routing_decision": routing_decision,
            "input_file": str(file_path),
            "file_extension": file_extension,
            "target_type": args.type,
            "mount_key": mount_key,
            "mount_type": 1,
            "async_mode": False,
            "async_decision": async_reason,
            "upload_result": upload_result,
            "ticket": import_ticket,
            "task_id": import_ticket,
            "task_kind": "import",
            "state_dir": str(state_dir),
            "task_state_path": str(state_path),
            "import_result": import_result,
            "grant_email": grant_email,
            "permission_grant_result": permission_grant_result,
            "extra_details": extra_details,
            "warnings": dedupe_strings([*warnings, *permission_warnings]),
        }
        imported_url = import_result.get("url")
        if not isinstance(imported_url, str) or not imported_url.strip():
            result["web_link_notice"] = build_web_link_notice(resource_kind="document")
        write_task_state(
            import_ticket,
            {
                **state_payload,
                "status": "completed",
                "import_result": import_result,
                "permission_grant_result": permission_grant_result,
                "warnings": result["warnings"],
            },
            args.state_dir,
        )
    except SystemExit as exc:
        result = {
            "success": False,
            "auth_mode": auth_mode,
            "task_id": args.task_id,
            "error": str(exc),
            "permission_hints": build_failure_hints(
                str(exc),
                operation="import",
                auth_mode=auth_mode,
                target_kind=args.type,
            ),
        }
        if not args.task_id:
            result.update(
                {
                    "routing_decision": routing_decision,
                    "input_file": str(file_path),
                    "file_extension": file_extension,
                    "target_type": args.type,
                    "mount_key": mount_key,
                    "mount_type": 1,
                    "state_dir": str(state_dir),
                }
            )
        if args.output:
            pathlib.Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
            result["output"] = args.output
        print_json(result)
        return
    if args.output:
        pathlib.Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
        result["output"] = args.output
    print_json(result)
