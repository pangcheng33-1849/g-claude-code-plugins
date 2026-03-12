from __future__ import annotations

"""Asset loading and block-level image/file replacement helpers."""

import base64
import json
import mimetypes
import pathlib
import urllib.parse
import uuid

from .common import http_bytes, http_json, raise_for_lark_failure
from .import_ops import encode_multipart_payload
from .markdown_ops import normalize_markdown_image_target


def load_image_source(source: str, source_base_dir: pathlib.Path | None) -> tuple[bytes, str, str]:
    normalized_source = normalize_markdown_image_target(source)
    parsed = urllib.parse.urlparse(normalized_source)
    if normalized_source.startswith("data:"):
        header, _, raw_data = normalized_source.partition(",")
        if not raw_data:
            raise SystemExit("image source data URL is malformed: missing payload")
        content_type = (header[5:].split(";", 1)[0].strip() or "application/octet-stream")
        if ";base64" in header:
            try:
                image_bytes = base64.b64decode(raw_data)
            except Exception as exc:
                raise SystemExit(f"decode image data URL failed: {exc}") from exc
        else:
            image_bytes = urllib.parse.unquote_to_bytes(raw_data)
        extension = mimetypes.guess_extension(content_type) or ".bin"
        file_name = f"image_{uuid.uuid4().hex[:8]}{extension}"
        return image_bytes, file_name, content_type
    if parsed.scheme in {"http", "https"}:
        status, buffer, headers = http_bytes(normalized_source)
        if status >= 400:
            body_preview = buffer.decode("utf-8", errors="replace")[:500]
            raise SystemExit(f"download image source failed: status={status} body={body_preview}")
        file_name = pathlib.Path(parsed.path).name or f"image_{uuid.uuid4().hex[:8]}.png"
        content_type = headers.get("Content-Type") or headers.get("content-type") or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        return buffer, file_name, content_type
    image_path = pathlib.Path(normalized_source)
    if not image_path.is_absolute() and source_base_dir:
        image_path = source_base_dir / image_path
    if not image_path.is_file() and not pathlib.Path(normalized_source).is_absolute():
        cwd_candidate = pathlib.Path.cwd() / pathlib.Path(normalized_source)
        if cwd_candidate.is_file():
            image_path = cwd_candidate
    if not image_path.is_file():
        raise SystemExit(
            "image source file does not exist: "
            f"{image_path}. supported inputs: http(s) URL, data URL, attachment://path, @relative/path, @/absolute/path, local file path."
        )
    content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    return image_path.read_bytes(), image_path.name, content_type


def load_attachment_source(source: str, source_base_dir: pathlib.Path | None) -> tuple[bytes, str, str]:
    normalized_source = normalize_markdown_image_target(source)
    parsed = urllib.parse.urlparse(normalized_source)
    if parsed.scheme in {"http", "https"}:
        status, buffer, headers = http_bytes(normalized_source)
        if status >= 400:
            body_preview = buffer.decode("utf-8", errors="replace")[:500]
            raise SystemExit(f"download attachment source failed: status={status} body={body_preview}")
        file_name = pathlib.Path(parsed.path).name or f"attachment_{uuid.uuid4().hex[:8]}.bin"
        content_type = headers.get("Content-Type") or headers.get("content-type") or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        return buffer, file_name, content_type
    file_path = pathlib.Path(normalized_source)
    if not file_path.is_absolute() and source_base_dir:
        file_path = source_base_dir / file_path
    if not file_path.is_file() and not pathlib.Path(normalized_source).is_absolute():
        cwd_candidate = pathlib.Path.cwd() / pathlib.Path(normalized_source)
        if cwd_candidate.is_file():
            file_path = cwd_candidate
    if not file_path.is_file():
        raise SystemExit(
            "attachment source file does not exist: "
            f"{file_path}. supported inputs: http(s) URL, attachment://path, @relative/path, @/absolute/path, local file path."
        )
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return file_path.read_bytes(), file_path.name, content_type


def replace_block_image(document_id: str, block_id: str, image_token: str, bearer_token: str) -> dict[str, object]:
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}",
        method="PATCH",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps({"replace_image": {"token": image_token}}, ensure_ascii=True).encode("utf-8"),
    )
    raise_for_lark_failure("replace image block", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def upload_docx_image(
    document_id: str,
    block_id: str,
    image_bytes: bytes,
    file_name: str,
    content_type: str,
    bearer_token: str,
) -> dict[str, object]:
    body, boundary = encode_multipart_payload(
        {
            "file_name": file_name,
            "parent_type": "docx_image",
            "parent_node": block_id,
            "size": str(len(image_bytes)),
        },
        "file",
        file_name=file_name,
        file_bytes=image_bytes,
        file_content_type=content_type or "application/octet-stream",
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
    raise_for_lark_failure("upload docx image", status, payload, text)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SystemExit(f"upload docx image missing data: {payload}")
    image_token = data.get("file_token")
    if not isinstance(image_token, str) or not image_token:
        raise SystemExit(f"upload docx image missing file_token: {payload}")
    replace_result = replace_block_image(document_id, block_id, image_token, bearer_token)
    return {
        "image_token": image_token,
        "replace_result": replace_result,
    }


def replace_block_file(document_id: str, block_id: str, file_token: str, bearer_token: str) -> dict[str, object]:
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}",
        method="PATCH",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps({"replace_file": {"token": file_token}}, ensure_ascii=True).encode("utf-8"),
    )
    raise_for_lark_failure("replace file block", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def upload_docx_file(
    document_id: str,
    block_id: str,
    file_bytes: bytes,
    file_name: str,
    content_type: str,
    bearer_token: str,
) -> dict[str, object]:
    body, boundary = encode_multipart_payload(
        {
            "file_name": file_name,
            "parent_type": "docx_file",
            "parent_node": block_id,
            "size": str(len(file_bytes)),
        },
        "file",
        file_name=file_name,
        file_bytes=file_bytes,
        file_content_type=content_type or "application/octet-stream",
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
    raise_for_lark_failure("upload docx file", status, payload, text)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SystemExit(f"upload docx file missing data: {payload}")
    file_token = data.get("file_token")
    if not isinstance(file_token, str) or not file_token:
        raise SystemExit(f"upload docx file missing file_token: {payload}")
    replace_result = replace_block_file(document_id, block_id, file_token, bearer_token)
    return {
        "file_token": file_token,
        "replace_result": replace_result,
    }
