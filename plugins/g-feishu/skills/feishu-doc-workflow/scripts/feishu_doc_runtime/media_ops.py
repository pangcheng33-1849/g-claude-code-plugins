from __future__ import annotations

"""Read-path media discovery, export fallback, download, and summarization."""

import hashlib
import json
import pathlib
import re
import urllib.parse
import zipfile

from .common import BLOCK_TYPE_TO_KIND, IMAGE_MIME_PREFIXES, MEDIA_TOKEN_PATTERN, http_bytes, http_json
from .document_ops import create_export_task, poll_async_task


def guess_media_kind(token: str, key_name: str | None, block_type: int | None) -> str:
    if block_type in BLOCK_TYPE_TO_KIND:
        return BLOCK_TYPE_TO_KIND[block_type]
    if key_name and "image" in key_name.lower():
        return "image"
    if key_name and "file" in key_name.lower():
        return "file"
    if token.startswith(("img_", "image_", "imgv", "img_v")):
        return "image"
    return "media"


def collect_media_refs(blocks: list[dict[str, object]]) -> list[dict[str, object]]:
    collected: dict[str, dict[str, object]] = {}

    def walk(node: object, *, block_id: str | None, block_type: int | None, path: str, key_name: str | None = None) -> None:
        if isinstance(node, dict):
            node_block_id = block_id
            node_block_type = block_type
            maybe_block_id = node.get("block_id")
            if isinstance(maybe_block_id, str):
                node_block_id = maybe_block_id
            maybe_block_type = node.get("block_type")
            if isinstance(maybe_block_type, int):
                node_block_type = maybe_block_type
            for child_key, child_value in node.items():
                child_path = f"{path}.{child_key}" if path else child_key
                walk(
                    child_value,
                    block_id=node_block_id,
                    block_type=node_block_type,
                    path=child_path,
                    key_name=child_key,
                )
            return
        if isinstance(node, list):
            for index, child in enumerate(node):
                child_path = f"{path}[{index}]"
                walk(child, block_id=block_id, block_type=block_type, path=child_path, key_name=key_name)
            return
        if isinstance(node, str) and (
            MEDIA_TOKEN_PATTERN.match(node)
            or (key_name == "token" and block_type in BLOCK_TYPE_TO_KIND and ".image.token" in path)
            or (key_name == "token" and block_type in BLOCK_TYPE_TO_KIND and ".board.token" in path)
            or (key_name == "token" and block_type in BLOCK_TYPE_TO_KIND and ".file.token" in path)
        ):
            media_kind = guess_media_kind(node, key_name, block_type)
            existing = collected.get(node)
            if existing:
                existing.setdefault("paths", []).append(path)
                return
            collected[node] = {
                "token": node,
                "kind": media_kind,
                "block_id": block_id,
                "block_type": block_type,
                "source_key": key_name,
                "paths": [path],
            }

    for index, block in enumerate(blocks):
        walk(
            block,
            block_id=block.get("block_id") if isinstance(block.get("block_id"), str) else None,
            block_type=block.get("block_type") if isinstance(block.get("block_type"), int) else None,
            path=f"items[{index}]",
        )
    return list(collected.values())


def fetch_tmp_download_url(file_token: str, bearer_token: str) -> str:
    url = (
        "https://open.feishu.cn/open-apis/drive/v1/medias/batch_get_tmp_download_url?"
        f"{urllib.parse.urlencode({'file_tokens': file_token, 'extra': ''})}"
    )
    status, payload, text = http_json(url, headers={"Authorization": f"Bearer {bearer_token}"})
    if status >= 400 or payload.get("code") not in {None, 0}:
        raise SystemExit(f"tmp download url fetch failed: status={status} body={payload or text}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SystemExit(f"tmp download url missing data: {payload}")
    items = data.get("tmp_download_urls")
    if not isinstance(items, list) or not items:
        raise SystemExit(f"tmp download url missing items: {payload}")
    first = items[0]
    if not isinstance(first, dict):
        raise SystemExit(f"tmp download url malformed: {payload}")
    tmp_url = first.get("tmp_download_url")
    if not isinstance(tmp_url, str) or not tmp_url:
        raise SystemExit(f"tmp download url missing value: {payload}")
    return tmp_url


def infer_extension(content_type: str | None, file_name: str | None) -> str:
    if file_name:
        ext = pathlib.Path(file_name).suffix
        if ext:
            return ext
    if content_type:
        mime = content_type.split(";")[0].strip().lower()
        if mime == "image/png":
            return ".png"
        if mime in {"image/jpeg", "image/jpg"}:
            return ".jpg"
        if mime == "image/gif":
            return ".gif"
        if mime == "image/webp":
            return ".webp"
        if mime == "image/svg+xml":
            return ".svg"
        if mime == "application/pdf":
            return ".pdf"
    return ""


def parse_content_disposition_file_name(headers: dict[str, str]) -> str | None:
    disposition = headers.get("Content-Disposition") or headers.get("content-disposition")
    if not disposition:
        return None
    utf8_match = re.search(r"filename\\*=UTF-8''([^;]+)", disposition, re.IGNORECASE)
    if utf8_match:
        return urllib.parse.unquote(utf8_match.group(1))
    basic_match = re.search(r'filename=\"?([^\";]+)\"?', disposition, re.IGNORECASE)
    if basic_match:
        return basic_match.group(1)
    return None


def download_media_file(file_token: str, bearer_token: str, media_dir: pathlib.Path, media_kind: str) -> dict[str, object]:
    direct_url = f"https://open.feishu.cn/open-apis/drive/v1/medias/{file_token}/download?extra"
    status, buffer, headers = http_bytes(direct_url, headers={"Authorization": f"Bearer {bearer_token}"})
    download_source = direct_url
    if status >= 400:
        tmp_url = fetch_tmp_download_url(file_token, bearer_token)
        status, buffer, headers = http_bytes(tmp_url)
        download_source = tmp_url
    if status >= 400:
        body_preview = buffer.decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"media download failed: status={status} body={body_preview}")
    content_type = headers.get("Content-Type") or headers.get("content-type") or ""
    file_name = parse_content_disposition_file_name(headers)
    ext = infer_extension(content_type, file_name)
    preferred_stem = file_name if file_name else file_token
    safe_stem = pathlib.Path(preferred_stem).stem
    if not safe_stem:
        safe_stem = file_token
    final_name = safe_stem + ext if ext else safe_stem
    if ext == "" and media_kind == "image":
        final_name = safe_stem + ".png"
    output_path = media_dir / final_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(buffer)
    return {
        "token": file_token,
        "kind": media_kind,
        "file_name": output_path.name,
        "saved_path": str(output_path),
        "size_bytes": len(buffer),
        "content_type": content_type,
        "download_source": download_source,
    }


def download_whiteboard_as_image(whiteboard_id: str, bearer_token: str, media_dir: pathlib.Path) -> dict[str, object]:
    candidate_urls = [
        f"https://open.feishu.cn/open-apis/board/v1/whiteboards/{whiteboard_id}/download_as_image",
        f"https://open.feishu.cn/open-apis/board/v1/whiteboard/{whiteboard_id}/download_as_image",
        f"https://open.feishu.cn/open-apis/board/v1/whiteboards/download_as_image?whiteboard_id={urllib.parse.quote(whiteboard_id)}",
        f"https://open.feishu.cn/open-apis/board/v1/whiteboard/download_as_image?whiteboard_id={urllib.parse.quote(whiteboard_id)}",
    ]
    last_failure: tuple[int, bytes, dict[str, str], str] | None = None
    for candidate_url in candidate_urls:
        status, buffer, headers = http_bytes(candidate_url, headers={"Authorization": f"Bearer {bearer_token}"})
        if status < 400:
            content_type = headers.get("Content-Type") or headers.get("content-type") or ""
            file_name = parse_content_disposition_file_name(headers) or f"{whiteboard_id}.png"
            ext = infer_extension(content_type, file_name) or ".png"
            safe_stem = pathlib.Path(file_name).stem or whiteboard_id
            output_path = media_dir / f"{safe_stem}{ext}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(buffer)
            return {
                "token": whiteboard_id,
                "kind": "whiteboard",
                "file_name": output_path.name,
                "saved_path": str(output_path),
                "size_bytes": len(buffer),
                "content_type": content_type,
                "download_source": candidate_url,
            }
        last_failure = (status, buffer, headers, candidate_url)
    if last_failure is None:
        raise SystemExit("whiteboard download failed: no candidate URL attempted")
    status, buffer, _headers, candidate_url = last_failure
    body_preview = buffer.decode("utf-8", errors="replace")[:500]
    raise SystemExit(f"whiteboard download failed: status={status} url={candidate_url} body={body_preview}")


def poll_export_task(ticket: str, bearer_token: str, *, document_id: str, timeout_seconds: int = 120) -> dict[str, object]:
    def fetch_once() -> dict[str, object]:
        status, payload, text = http_json(
            f"https://open.feishu.cn/open-apis/drive/v1/export_tasks/{ticket}",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        if (
            status >= 400
            and isinstance(payload.get("error"), dict)
            and isinstance(payload["error"].get("field_violations"), list)
            and any(isinstance(item, dict) and item.get("field") == "token" for item in payload["error"]["field_violations"])
        ):
            status, payload, text = http_json(
                f"https://open.feishu.cn/open-apis/drive/v1/export_tasks/{ticket}?token={urllib.parse.quote(document_id)}",
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
        if status >= 400 or payload.get("code") not in {None, 0}:
            raise SystemExit(f"export task poll failed: status={status} body={payload or text}")
        data = payload.get("data")
        if isinstance(data, dict):
            result = data.get("result")
            if isinstance(result, dict):
                job_status = result.get("job_status")
                if job_status == 0 and isinstance(result.get("file_token"), str):
                    return {"state": "success", "result": result}
                if job_status in {1, 2, 3, None} and (
                    not isinstance(result.get("job_error_msg"), str)
                    or result.get("job_error_msg") in {"success", "", "processing", "pending"}
                ):
                    return {"state": "pending", "result": result}
                return {"state": "failed", "error": result}
        return {"state": "pending", "result": {}}

    return poll_async_task(fetch_once, description="export task", timeout_seconds=timeout_seconds, interval_seconds=2)


def download_export_docx(file_token: str, bearer_token: str, output_path: pathlib.Path) -> pathlib.Path:
    status, buffer, _headers = http_bytes(
        f"https://open.feishu.cn/open-apis/drive/v1/export_tasks/file/{file_token}/download",
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    if status >= 400:
        body_preview = buffer.decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"exported docx download failed: status={status} body={body_preview}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(buffer)
    return output_path


def extract_images_from_docx(docx_path: pathlib.Path, media_dir: pathlib.Path) -> list[dict[str, object]]:
    downloaded_media: list[dict[str, object]] = []
    media_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(docx_path) as archive:
        for member in archive.namelist():
            if not member.startswith("word/media/"):
                continue
            file_name = pathlib.Path(member).name
            if not file_name:
                continue
            target_path = media_dir / file_name
            target_path.write_bytes(archive.read(member))
            downloaded_media.append(
                {
                    "token": None,
                    "kind": "image",
                    "file_name": target_path.name,
                    "saved_path": str(target_path),
                    "size_bytes": target_path.stat().st_size,
                    "content_type": "",
                    "download_source": f"docx_export:{docx_path}",
                }
            )
    return downloaded_media


def export_docx_and_extract_images(
    document_id: str,
    bearer_token: str,
    media_dir: pathlib.Path,
    *,
    file_type: str = "docx",
    export_docx_path: pathlib.Path | None = None,
) -> tuple[list[dict[str, object]], pathlib.Path]:
    if export_docx_path is None:
        export_docx_path = media_dir.parent / f"{document_id}.export.docx"
    ticket = create_export_task(document_id, bearer_token, file_type=file_type)
    export_result = poll_export_task(ticket, bearer_token, document_id=document_id)
    file_token = export_result.get("file_token")
    if not isinstance(file_token, str) or not file_token:
        raise SystemExit(f"export task file token missing: {export_result}")
    downloaded_docx_path = download_export_docx(file_token, bearer_token, export_docx_path)
    return extract_images_from_docx(downloaded_docx_path, media_dir), downloaded_docx_path


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def is_text_like_attachment(path: pathlib.Path, content_type: str | None) -> bool:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown", ".mark", ".csv", ".tsv", ".json", ".yaml", ".yml", ".html", ".htm", ".xml", ".log"}:
        return True
    if content_type:
        normalized = content_type.split(";")[0].strip().lower()
        if normalized.startswith("text/"):
            return True
        if normalized in {
            "application/json",
            "application/xml",
            "application/x-yaml",
            "application/yaml",
        }:
            return True
    return False


def summarize_attachment_file(path: pathlib.Path, content_type: str | None) -> dict[str, object]:
    summary: dict[str, object] = {
        "file_name": path.name,
        "file_extension": path.suffix.lower(),
        "is_binary": True,
    }
    if not path.is_file():
        summary["summary_kind"] = "missing"
        summary["note"] = "本地附件文件不存在，无法生成摘要。"
        return summary
    if not is_text_like_attachment(path, content_type):
        summary["summary_kind"] = "binary"
        summary["note"] = "二进制附件；保留下载路径供后续人工处理。"
        return summary
    try:
        raw_text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            raw_text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            summary["summary_kind"] = "binary_like"
            summary["note"] = "附件疑似文本，但无法稳定解码；保留下载路径供后续处理。"
            return summary
    except Exception as exc:
        summary["summary_kind"] = "error"
        summary["note"] = f"读取附件摘要失败：{exc}"
        return summary

    preview = raw_text.strip()
    line_count = len(raw_text.splitlines())
    summary["is_binary"] = False
    summary["line_count"] = line_count

    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                summary["summary_kind"] = "json"
                summary["top_level_keys"] = list(parsed.keys())[:10]
            elif isinstance(parsed, list):
                summary["summary_kind"] = "json"
                summary["top_level_type"] = "list"
                summary["item_count"] = len(parsed)
            else:
                summary["summary_kind"] = "json"
                summary["top_level_type"] = type(parsed).__name__
        except Exception:
            summary["summary_kind"] = "text"
    elif suffix in {".csv", ".tsv"}:
        lines = [line for line in raw_text.splitlines() if line.strip()]
        delimiter = "\t" if suffix == ".tsv" else ","
        summary["summary_kind"] = "table_text"
        if lines:
            summary["header"] = [cell.strip() for cell in lines[0].split(delimiter)]
            summary["row_count"] = max(len(lines) - 1, 0)
    elif suffix in {".md", ".markdown", ".mark"}:
        summary["summary_kind"] = "markdown"
    elif suffix in {".html", ".htm", ".xml"}:
        summary["summary_kind"] = "markup"
    else:
        summary["summary_kind"] = "text"

    if preview:
        summary["text_preview"] = preview[:400]
    else:
        summary["text_preview"] = ""
    return summary


def merge_exported_images(
    exported_media: list[dict[str, object]],
    existing_media: list[dict[str, object]],
    unresolved_refs: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    existing_hashes: set[str] = set()
    for item in existing_media:
        saved_path = item.get("saved_path")
        if isinstance(saved_path, str) and pathlib.Path(saved_path).is_file():
            existing_hashes.add(file_sha256(pathlib.Path(saved_path)))

    new_exported_media: list[dict[str, object]] = []
    unmatched_exported_media: list[dict[str, object]] = []
    for item in exported_media:
        saved_path = item.get("saved_path")
        if not isinstance(saved_path, str):
            continue
        path = pathlib.Path(saved_path)
        if not path.is_file():
            continue
        digest = file_sha256(path)
        if digest in existing_hashes:
            continue
        existing_hashes.add(digest)
        new_exported_media.append(item)
        unmatched_exported_media.append(item)

    for media_ref in unresolved_refs:
        if not unmatched_exported_media:
            break
        matched_item = unmatched_exported_media.pop(0)
        media_ref["download_status"] = "exported_from_docx_fallback"
        media_ref["saved_path"] = matched_item.get("saved_path")
        media_ref["reason"] = "通过导出 docx 后抽取媒体快照补齐。"

    return new_exported_media, unmatched_exported_media


def summarize_downloaded_images(downloaded_media: list[dict[str, object]]) -> dict[str, object]:
    images = [
        item
        for item in downloaded_media
        if item.get("kind") == "image"
        or (isinstance(item.get("content_type"), str) and item["content_type"].startswith(IMAGE_MIME_PREFIXES))
    ]
    image_paths = [str(item["saved_path"]) for item in images if isinstance(item.get("saved_path"), str)]
    image_items = [
        {
            "saved_path": str(item["saved_path"]),
            "file_name": item.get("file_name"),
            "content_type": item.get("content_type"),
            "size_bytes": item.get("size_bytes"),
            "source_kind": item.get("kind"),
            "download_source": item.get("download_source"),
            "understanding_status": "pending_review",
            "recommended_tool": "view_image",
            "summary": None,
            "extracted_text": None,
            "entities": [],
            "questions_to_answer": [
                "这张图片主要展示了什么？",
                "是否包含文字、表格、流程图、截图或图表？",
                "哪些内容应该被并入最终文档总结？",
            ],
        }
        for item in images
        if isinstance(item.get("saved_path"), str)
    ]
    return {
        "schema_version": 1,
        "image_count": len(image_paths),
        "image_paths": image_paths,
        "items": image_items,
        "merge_instruction": "先逐张完成 items[].summary / extracted_text / entities，再把图片结论与正文内容合并。",
        "next_step": (
            "如果当前运行环境支持图片理解，请优先用 view_image 等图片理解工具逐个打开 image_paths 对应的本地图片，先理解图中信息，再结合正文做总结。"
            if image_paths
            else "没有拿到可下载图片；如果文档里明确存在图片，请改走浏览器截图或页面导出，再用 view_image 做图片理解。"
        ),
    }


def order_and_dedupe_downloaded_media(
    downloaded_media: list[dict[str, object]],
    media_refs: list[dict[str, object]],
) -> list[dict[str, object]]:
    token_order = {
        str(item.get("token")): index
        for index, item in enumerate(media_refs)
        if isinstance(item.get("token"), str)
    }
    deduped: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for item in downloaded_media:
        saved_path = item.get("saved_path")
        file_name = item.get("file_name")
        token = item.get("token")
        key = (
            item.get("kind"),
            str(saved_path) if isinstance(saved_path, str) else None,
            str(token) if isinstance(token, str) else None,
            str(file_name) if isinstance(file_name, str) else None,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    decorated: list[tuple[tuple[int, int], dict[str, object]]] = []
    for index, item in enumerate(deduped):
        token = item.get("token")
        primary_order = token_order.get(str(token), len(token_order) + index) if isinstance(token, str) else len(token_order) + index
        decorated.append(((primary_order, index), item))
    decorated.sort(key=lambda item: item[0])
    return [item for _sort_key, item in decorated]


def summarize_downloaded_media(downloaded_media: list[dict[str, object]]) -> dict[str, object]:
    images = [
        item
        for item in downloaded_media
        if item.get("kind") == "image"
        or (isinstance(item.get("content_type"), str) and item["content_type"].startswith(IMAGE_MIME_PREFIXES))
    ]
    whiteboards = [item for item in downloaded_media if item.get("kind") == "whiteboard"]
    attachments = [
        item
        for item in downloaded_media
        if item.get("kind") not in {"image", "whiteboard"}
        and not (isinstance(item.get("content_type"), str) and item["content_type"].startswith(IMAGE_MIME_PREFIXES))
    ]
    image_paths = [str(item["saved_path"]) for item in images if isinstance(item.get("saved_path"), str)]
    whiteboard_paths = [str(item["saved_path"]) for item in whiteboards if isinstance(item.get("saved_path"), str)]
    attachment_items = [
        {
            "file_name": item.get("file_name"),
            "saved_path": item.get("saved_path"),
            "content_type": item.get("content_type"),
            "size_bytes": item.get("size_bytes"),
            "download_source": item.get("download_source"),
            **(
                summarize_attachment_file(pathlib.Path(item["saved_path"]), item.get("content_type"))
                if isinstance(item.get("saved_path"), str)
                else {"summary_kind": "unknown", "note": "没有本地文件路径，无法生成附件摘要。"}
            ),
        }
        for item in attachments
    ]
    return {
        "media_count": len(downloaded_media),
        "image_count": len(images),
        "whiteboard_count": len(whiteboards),
        "attachment_count": len(attachments),
        "image_paths": image_paths,
        "whiteboard_paths": whiteboard_paths,
        "attachments": attachment_items,
        "image_understanding": summarize_downloaded_images(downloaded_media),
        "attachment_next_step": (
            "对 attachments 里的本地文件按类型继续处理：文本类附件优先参考 text_preview / header / top_level_keys；二进制附件保留下载路径并在总结里说明。"
            if attachment_items
            else "没有拿到可下载附件。"
        ),
    }


def build_image_manifest(
    document_id: str,
    downloaded_media: list[dict[str, object]],
    *,
    export_docx_path: pathlib.Path | None = None,
    warnings: list[str] | None = None,
) -> dict[str, object]:
    image_items = [
        item
        for item in downloaded_media
        if item.get("kind") == "image"
        or (isinstance(item.get("content_type"), str) and item["content_type"].startswith(IMAGE_MIME_PREFIXES))
    ]
    whiteboard_items = [item for item in downloaded_media if item.get("kind") == "whiteboard"]
    attachment_items = [
        item
        for item in downloaded_media
        if item.get("kind") not in {"image", "whiteboard"}
        and not (isinstance(item.get("content_type"), str) and item["content_type"].startswith(IMAGE_MIME_PREFIXES))
    ]
    return {
        "document_id": document_id,
        "media_count": len(downloaded_media),
        "image_count": len(image_items),
        "whiteboard_count": len(whiteboard_items),
        "attachment_count": len(attachment_items),
        "images": image_items,
        "whiteboards": whiteboard_items,
        "attachments": attachment_items,
        "export_docx_path": str(export_docx_path) if export_docx_path else None,
        "warnings": warnings or [],
        "browser_capture_fallback_recommended": len(image_items) == 0,
        "next_step": (
            "用图片理解工具逐个打开 images[].saved_path，提取图表、流程图、截图里的关键信息。"
            if image_items
            else "API 没拿到图片时，改用浏览器打开文档、逐屏截图或截取图片区域，再用 view_image 理解图片内容。"
        ),
    }


def build_failure_hints(error_text: str, *, operation: str, auth_mode: str, target_kind: str) -> list[str]:
    hints: list[str] = []
    lowered = error_text.lower()
    tenant_identity = "tenant" in auth_mode.lower()
    if operation == "import":
        if "1069902" in lowered or "no permission" in lowered or "403" in lowered:
            hints.extend(
                [
                    "当前身份没有导入相关文档或目标目录的权限。",
                    "如果使用 tenant token，常见原因是应用未被授予目标文件夹权限，或者应用没有被加入可访问该目录的群/文档权限链路。",
                    "如果使用 user token，常见原因是当前用户对目标目录没有编辑权限。",
                ]
            )
        if "1069908" in lowered or "mount point not found" in lowered:
            hints.extend(
                [
                    "mount_key 可能不是有效的文件夹 token，或者当前身份不能导入到该目录。",
                    "请确认目标文件夹存在，并且当前身份对该文件夹具有编辑权限。",
                ]
            )
        if "1069910" in lowered or "extension not match" in lowered:
            hints.extend(
                [
                    "导入任务里的 file_extension 必须和实际文件后缀严格一致，例如 md 与 markdown 不能混用。",
                    "如果你通过 upload_all 上传临时文件，extra.file_extension 也必须与真实后缀一致。",
                ]
            )
        if "1069913" in lowered or "token expired" in lowered:
            hints.append("上传得到的 file_token 已过期；通过 upload_all 方式导入时，临时文件 token 有效期通常只有 5 分钟。")
    if operation == "export":
        if "1069902" in lowered or "no permission" in lowered or "403" in lowered:
            hints.extend(
                [
                    "当前身份可以读取正文，但导出接口要求更强权限边界；正文可读不代表允许导出。",
                    "如果你用的是 user token，常见原因是这次授权的 token 没有实际拿到 docs:document:export，需要重新授权并确认授权页包含“导出云文档”。",
                    "如果组织或文档本身关闭了导出能力，用户能看文档，但导出接口仍会失败。",
                    "如果最终走的是应用身份，还可能是应用没有被加入该文档的“文档应用”访问链路。",
                ]
            )
        if "1069914" in lowered or "file token invalid" in lowered:
            hints.extend(
                [
                    "传入的 token 类型不对。导出接口需要实际文档 token，而不是 wiki 节点 token。",
                    "如果目标是 wiki 页面，应该先把 wiki token 解析成实际 obj_token 再导出。",
                    "如果目标是目录节点而不是文档页，也会报 token 不合法。",
                ]
            )
    if operation == "image_download":
        if "tmp_download_urls" in lowered and "[]" in lowered:
            hints.extend(
                [
                    "图片 token 已识别，但当前接口没有返回可用下载地址。",
                    "常见原因是该 token 不是可直接通过 drive media 下载的资源类型。",
                    "这种情况下更适合回退到文档导出；如果导出也失败，就只能走浏览器截图。",
                ]
            )
        if "403" in lowered or "no permission" in lowered:
            hints.extend(
                [
                    "当前身份对这张图片资源没有直接下载权限。",
                    "这可能是图片资源权限与正文权限分离导致的：正文可读，但图片直下仍被拒绝。",
                    "建议先确认是否能改用 user token，再重试单图下载；如果仍失败，再回退导出 docx 抽取图片快照。",
                ]
            )
    if operation == "file_download":
        if "tmp_download_urls" in lowered and "[]" in lowered:
            hints.extend(
                [
                    "附件 token 已识别，但当前接口没有返回可用下载地址。",
                    "常见原因是该 token 不是可直接通过 drive media 下载的资源类型，或者当前身份没有附件下载权限。",
                ]
            )
        if "403" in lowered or "no permission" in lowered:
            hints.extend(
                [
                    "当前身份对这个附件资源没有直接下载权限。",
                    "附件权限可能与正文权限分离：正文可读，不代表附件可直下。",
                    "如果附件必须获取，建议先切到 user token 重试；若服务端仍不返回下载地址，则当前文档只能保留附件元信息。",
                ]
            )
        if "media download failed" in lowered:
            hints.append("建议保留附件元信息（文件名、下载来源、大小、content_type），并在总结里明确说明当前无法直下附件。")
    if operation == "whiteboard_download":
        if "403" in lowered or "no permission" in lowered:
            hints.extend(
                [
                    "当前身份对该白板没有下载缩略图权限，常见原因是用户 token 没有拿到 board:whiteboard:node:read。",
                    "即使用户能看到文档正文，白板缩略图下载仍可能要求单独的白板读取权限。",
                ]
            )
        if "404" in lowered:
            hints.extend(
                [
                    "当前白板 token 无法通过普通 drive media 接口下载，应该改走 board-v1 的 download_as_image 接口。",
                    "如果 board-v1 也返回 404，需要确认 whiteboard_id 是否正确，或该 block 是否仍指向有效白板。",
                ]
            )
        if "invalid_scope" in lowered:
            hints.append("设备授权或 OAuth scope 缺少 board:whiteboard:node:read，需要重新授权。")
    if not hints:
        hints.append(f"{operation} 失败，建议先检查 token 类型、scope、目标对象类型，以及 {target_kind} 资源是否支持当前接口。")
    if tenant_identity:
        hints.append("当前是应用身份调用；如果资源是用户私有文档或未添加文档应用，应用身份通常会失败。")
        if any(
            needle in lowered
            for needle in ("403", "forbidden", "no permission", "unauthorized", "permission denied", "1069902", "1770032", "2890005")
        ):
            hints.append("建议降级到 user token：先用 feishu-auth-and-scopes 获取或刷新 user token，再通过 --user-access-token 重试。")
    return list(dict.fromkeys(hints))
