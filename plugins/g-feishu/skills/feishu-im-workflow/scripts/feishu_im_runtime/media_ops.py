"""Media upload command handlers for feishu-im-workflow.

Implements upload-image and upload-file using multipart/form-data
with Python stdlib only (no third-party dependencies).

Upload image: POST /im/v1/images  → image_key
Upload file:  POST /im/v1/files   → file_key

After uploading, use send-message with:
  --msg-type image --content-json '{"image_key": "<image_key>"}'
  --msg-type file  --content-json '{"file_key": "<file_key>"}'
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import pathlib
import urllib.error
import urllib.request
import uuid

from .common import API_BASE, fail, normalize_result, print_result_or_exit, resolve_token


def _build_multipart_body(
    fields: dict[str, str],
    file_field: str,
    file_path: str,
    boundary: str,
) -> bytes:
    """Build a multipart/form-data body using stdlib only."""
    body = b""
    crlf = b"\r\n"

    for name, value in fields.items():
        body += f"--{boundary}\r\n".encode("utf-8")
        body += f'Content-Disposition: form-data; name="{name}"\r\n'.encode("utf-8")
        body += crlf
        body += value.encode("utf-8")
        body += crlf

    file_path_obj = pathlib.Path(file_path)
    filename = file_path_obj.name
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    file_data = file_path_obj.read_bytes()

    body += f"--{boundary}\r\n".encode("utf-8")
    body += (
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
    ).encode("utf-8")
    body += f"Content-Type: {mime_type}\r\n".encode("utf-8")
    body += crlf
    body += file_data
    body += crlf
    body += f"--{boundary}--\r\n".encode("utf-8")

    return body


def _multipart_request(
    *,
    path: str,
    token: str,
    fields: dict[str, str],
    file_field: str,
    file_path: str,
) -> dict[str, object]:
    boundary = uuid.uuid4().hex
    body = _build_multipart_body(fields, file_field, file_path, boundary)
    url = f"{API_BASE}{path}"
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"code": error.code, "msg": raw, "http_status": error.code}


def cmd_upload_image(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="upload-image",
    )
    file_path = args.file_path
    if not pathlib.Path(file_path).exists():
        fail(
            f"File not found: {file_path}",
            api_alias="im_v1_image_create",
            auth_mode=auth_mode,
        )

    response = _multipart_request(
        path="/im/v1/images",
        token=token,
        fields={"image_type": args.image_type},
        file_field="image",
        file_path=file_path,
    )
    data = response.get("data") or {}
    image_key = data.get("image_key", "")
    extra: dict[str, object] = {
        "image_key": image_key,
        "image_type": args.image_type,
        "file_path": file_path,
    }
    if image_key:
        extra["send_hint"] = (
            f"发送图片消息示例：send-message --receive-id <chat_id> "
            f'--msg-type image --content-json \'{{"image_key":"{image_key}"}}\''
        )
    result = normalize_result(
        api_alias="im_v1_image_create",
        auth_mode=auth_mode,
        response=response,
        extra=extra,
    )
    print_result_or_exit(result, command_name="upload-image")


def cmd_upload_file(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        tenant_access_token=args.tenant_access_token,
        command_name="upload-file",
    )
    file_path = args.file_path
    if not pathlib.Path(file_path).exists():
        fail(
            f"File not found: {file_path}",
            api_alias="im_v1_file_create",
            auth_mode=auth_mode,
        )

    file_name = args.file_name or pathlib.Path(file_path).name
    fields: dict[str, str] = {
        "file_type": args.file_type,
        "file_name": file_name,
    }
    if args.duration is not None:
        fields["duration"] = str(args.duration)

    response = _multipart_request(
        path="/im/v1/files",
        token=token,
        fields=fields,
        file_field="file",
        file_path=file_path,
    )
    data = response.get("data") or {}
    file_key = data.get("file_key", "")
    extra: dict[str, object] = {
        "file_key": file_key,
        "file_type": args.file_type,
        "file_name": file_name,
        "file_path": file_path,
    }
    if file_key:
        extra["send_hint"] = (
            f"发送文件消息示例：send-message --receive-id <chat_id> "
            f'--msg-type file --content-json \'{{"file_key":"{file_key}"}}\''
        )
    result = normalize_result(
        api_alias="im_v1_file_create",
        auth_mode=auth_mode,
        response=response,
        extra=extra,
    )
    print_result_or_exit(result, command_name="upload-file")
