from __future__ import annotations

"""Import/export task primitives and multipart upload helpers."""

import json
import mimetypes
import pathlib
import time
import uuid

from .common import IMPORT_EXTRA_HINTS, http_json, raise_for_lark_failure


def poll_async_task(
    fetch_once,
    *,
    description: str,
    timeout_seconds: int = 120,
    interval_seconds: int = 2,
) -> dict[str, object]:
    deadline = time.time() + timeout_seconds
    last_state: dict[str, object] | None = None
    while time.time() < deadline:
        state = fetch_once()
        last_state = state
        task_state = state.get("state")
        if task_state == "success":
            result = state.get("result")
            return result if isinstance(result, dict) else {}
        if task_state == "failed":
            raise SystemExit(f"{description} failed: {state.get('error') or state}")
        time.sleep(interval_seconds)
    raise SystemExit(f"{description} timed out: {last_state or {}}")


def encode_multipart_payload(
    fields: dict[str, str],
    file_field_name: str,
    *,
    file_name: str,
    file_bytes: bytes,
    file_content_type: str,
) -> tuple[bytes, str]:
    boundary = f"----CodexBoundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="{file_field_name}"; filename="{file_name}"\r\n'.encode("utf-8"),
            f"Content-Type: {file_content_type}\r\n\r\n".encode("utf-8"),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(chunks), boundary


def upload_import_source_file(
    file_path: pathlib.Path,
    bearer_token: str,
    *,
    target_type: str,
    file_extension: str,
) -> dict[str, object]:
    file_bytes = file_path.read_bytes()
    file_content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    extra = json.dumps({"obj_type": target_type, "file_extension": file_extension}, ensure_ascii=True)
    body, boundary = encode_multipart_payload(
        {
            "file_name": file_path.name,
            "parent_type": "ccm_import_open",
            "parent_node": "",
            "size": str(file_path.stat().st_size),
            "extra": extra,
        },
        "file",
        file_name=file_path.name,
        file_bytes=file_bytes,
        file_content_type=file_content_type,
    )
    status, payload, text = http_json(
        "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        data=body,
        timeout=120,
    )
    raise_for_lark_failure("upload import source file", status, payload, text)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SystemExit(f"upload import source file missing data: {payload}")
    file_token = data.get("file_token")
    if not isinstance(file_token, str) or not file_token:
        raise SystemExit(f"upload import source file missing file_token: {payload}")
    return data


def create_import_task(
    *,
    file_extension: str,
    file_token: str,
    target_type: str,
    mount_key: str,
    bearer_token: str,
    file_name: str | None = None,
) -> str:
    body: dict[str, object] = {
        "file_extension": file_extension,
        "file_token": file_token,
        "type": target_type,
        "point": {"mount_type": 1, "mount_key": mount_key},
    }
    if file_name:
        body["file_name"] = file_name
    status, payload, text = http_json(
        "https://open.feishu.cn/open-apis/drive/v1/import_tasks",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body, ensure_ascii=True).encode("utf-8"),
    )
    raise_for_lark_failure("create import task", status, payload, text)
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("ticket"), str):
        raise SystemExit(f"create import task missing ticket: {payload}")
    return str(data["ticket"])


def classify_import_job_status(result: dict[str, object]) -> dict[str, object]:
    job_status = result.get("job_status")
    job_error_msg = result.get("job_error_msg")
    token = result.get("token")
    url = result.get("url")
    if job_status == 0 and (isinstance(token, str) or isinstance(url, str)):
        return {"state": "success", "result": result}
    if job_status in {1, 2, 3, None} and (not isinstance(job_error_msg, str) or job_error_msg in {"", "success", "processing", "pending"}):
        return {"state": "pending", "result": result}
    return {"state": "failed", "error": result}


def poll_import_task(ticket: str, bearer_token: str, *, timeout_seconds: int = 120) -> dict[str, object]:
    def fetch_once() -> dict[str, object]:
        status, payload, text = http_json(
            f"https://open.feishu.cn/open-apis/drive/v1/import_tasks/{ticket}",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        raise_for_lark_failure("poll import task", status, payload, text)
        data = payload.get("data")
        if not isinstance(data, dict):
            return {"state": "failed", "error": f"missing data: {payload}"}
        result = data.get("result")
        if not isinstance(result, dict):
            return {"state": "pending", "result": {}}
        return classify_import_job_status(result)

    return poll_async_task(fetch_once, description="import task", timeout_seconds=timeout_seconds, interval_seconds=2)


def decode_import_extra(extra: object) -> list[dict[str, object]]:
    if not isinstance(extra, list):
        return []
    decoded: list[dict[str, object]] = []
    for item in extra:
        code = str(item)
        if not code.isdigit():
            decoded.append(
                {
                    "code": code,
                    "message": "系统返回了非诊断型 extra 元数据，通常可忽略。",
                    "severity": "info",
                }
            )
            continue
        decoded.append(
            {
                "code": code,
                "message": IMPORT_EXTRA_HINTS.get(code, "系统返回了额外提示码，但本地映射表中暂无对应解释。"),
                "severity": "warning",
            }
        )
    return decoded


def create_export_task(document_id: str, bearer_token: str, *, file_extension: str = "docx", file_type: str = "docx") -> str:
    status, payload, text = http_json(
        "https://open.feishu.cn/open-apis/drive/v1/export_tasks",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(
            {
                "file_extension": file_extension,
                "token": document_id,
                "type": file_type,
            },
            ensure_ascii=True,
        ).encode("utf-8"),
    )
    raise_for_lark_failure("export task create", status, payload, text)
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("ticket"), str):
        raise SystemExit(f"export task ticket missing: {payload}")
    return str(data["ticket"])


def infer_file_extension(file_path: pathlib.Path, explicit_extension: str | None) -> str:
    if explicit_extension:
        return explicit_extension.lstrip(".").lower()
    suffix = file_path.suffix.lstrip(".").lower()
    if suffix:
        return suffix
    raise SystemExit("--file-extension is required when the input file has no suffix")
