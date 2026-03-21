from __future__ import annotations

"""Thin wrappers around core Feishu doc/wiki HTTP APIs."""

import json
import urllib.parse

from .common import (
    build_object_url,
    build_wiki_url,
    extract_folder_token,
    extract_ref,
    fetch_wiki_node,
    http_json,
    raise_for_lark_failure,
)
from .markdown_ops import make_text_elements


def resolve_bearer_token(
    *,
    user_access_token: str | None,
    tenant_access_token: str | None,
    use_tenant_token: bool,
) -> tuple[str, str]:
    if use_tenant_token or tenant_access_token:
        if not isinstance(tenant_access_token, str) or not tenant_access_token:
            raise SystemExit(
                "missing tenant token: pass --tenant-access-token. "
                "Use skill feishu-auth-and-scopes to obtain a tenant token first."
            )
        return tenant_access_token, "explicit_tenant_access_token"

    if not isinstance(user_access_token, str) or not user_access_token:
        raise SystemExit(
            "missing user token: pass --user-access-token. "
            "Use skill feishu-auth-and-scopes to obtain a user token first."
        )
    return user_access_token, "explicit_user_access_token"


def fetch_raw_content(document_id: str, bearer_token: str) -> dict[str, object]:
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/raw_content",
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    if status >= 400 or payload.get("code") not in {None, 0}:
        raise SystemExit(f"doc fetch failed: status={status} body={payload or text}")
    return payload


def extract_raw_content(payload: dict[str, object]) -> str:
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("content", "raw_content", "markdown", "text"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
    for key in ("content", "raw_content", "markdown", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise SystemExit(f"doc content missing in response: {payload}")


def fetch_document_blocks(document_id: str, bearer_token: str, page_size: int = 500) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    page_token: str | None = None
    while True:
        query = {"page_size": str(page_size)}
        if page_token:
            query["page_token"] = page_token
        url = (
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks?"
            f"{urllib.parse.urlencode(query)}"
        )
        status, payload, text = http_json(url, headers={"Authorization": f"Bearer {bearer_token}"})
        if status >= 400 or payload.get("code") not in {None, 0}:
            raise SystemExit(f"doc blocks fetch failed: status={status} body={payload or text}")
        data = payload.get("data")
        if not isinstance(data, dict):
            break
        page_items = data.get("items")
        if isinstance(page_items, list):
            items.extend(item for item in page_items if isinstance(item, dict))
        if not data.get("has_more"):
            break
        next_page_token = data.get("page_token")
        if not isinstance(next_page_token, str) or not next_page_token:
            break
        page_token = next_page_token
    return items


def get_page_block(document_id: str, bearer_token: str) -> dict[str, object]:
    blocks = fetch_document_blocks(document_id, bearer_token)
    for block in blocks:
        if block.get("block_id") == document_id and block.get("block_type") == 1:
            return block
    raise SystemExit(f"page block missing for document: {document_id}")


def extract_document_title(page_block: dict[str, object]) -> str:
    page = page_block.get("page")
    if isinstance(page, dict):
        elements = page.get("elements")
        if isinstance(elements, list):
            parts: list[str] = []
            for element in elements:
                if not isinstance(element, dict):
                    continue
                text_run = element.get("text_run")
                if isinstance(text_run, dict):
                    content = text_run.get("content")
                    if isinstance(content, str):
                        parts.append(content)
            if parts:
                return "".join(parts)
    return ""


def create_document(title: str, bearer_token: str, *, folder_token: str | None = None) -> dict[str, object]:
    body: dict[str, object] = {"title": title}
    if folder_token:
        body["folder_token"] = folder_token
    status, payload, text = http_json(
        "https://open.feishu.cn/open-apis/docx/v1/documents",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body, ensure_ascii=True).encode("utf-8"),
    )
    raise_for_lark_failure("document create", status, payload, text)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SystemExit(f"document create missing data: {payload}")
    document = data.get("document")
    if not isinstance(document, dict):
        raise SystemExit(f"document create missing document: {payload}")
    return document


def list_documents(
    *,
    bearer_token: str,
    folder_token: str | None = None,
    node_token: str | None = None,
    wiki_space: str | None = None,
    page_size: int = 50,
    page_token: str | None = None,
    order_by: str | None = None,
    direction: str | None = None,
) -> dict[str, object]:
    if folder_token and (node_token or wiki_space):
        raise SystemExit("--folder-token 不能和 --node-token / --wiki-space 同时使用")
    if node_token and wiki_space:
        raise SystemExit("--node-token 和 --wiki-space 只能二选一")
    if folder_token:
        normalized_folder_token = extract_folder_token(folder_token)
        query: dict[str, str] = {"page_size": str(page_size)}
        if normalized_folder_token:
            query["folder_token"] = normalized_folder_token
        if page_token:
            query["page_token"] = page_token
        if order_by:
            query["order_by"] = order_by
        if direction:
            query["direction"] = direction
        status, payload, text = http_json(
            f"https://open.feishu.cn/open-apis/drive/v1/files?{urllib.parse.urlencode(query)}",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        raise_for_lark_failure("drive file list", status, payload, text)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise SystemExit(f"drive file list missing data: {payload}")
        files = [item for item in data.get("files", []) if isinstance(item, dict)]
        return {
            "container_kind": "folder",
            "folder_token": normalized_folder_token,
            "items": [
                {
                    "title": item.get("name"),
                    "token": item.get("token"),
                    "type": item.get("type"),
                    "url": item.get("url"),
                    "parent_token": item.get("parent_token"),
                    "owner_id": item.get("owner_id"),
                    "raw": item,
                }
                for item in files
            ],
            "has_more": bool(data.get("has_more")),
            "page_token": data.get("next_page_token"),
        }

    resolved_space_id = wiki_space
    normalized_node_token = None
    if node_token:
        node_target = extract_ref(node_token)
        token = str(node_target.get("token") or node_token).strip()
        node = fetch_wiki_node(token, bearer_token)
        normalized_node_token = str(node.get("node_token") or token)
        resolved_space_id = str(node.get("space_id") or "")
        if not resolved_space_id:
            raise SystemExit(f"wiki node missing space_id: {node}")
    if resolved_space_id:
        query = {"page_size": str(page_size)}
        if page_token:
            query["page_token"] = page_token
        if normalized_node_token:
            query["parent_node_token"] = normalized_node_token
        status, payload, text = http_json(
            f"https://open.feishu.cn/open-apis/wiki/v2/spaces/{resolved_space_id}/nodes?{urllib.parse.urlencode(query)}",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        raise_for_lark_failure("wiki node list", status, payload, text)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise SystemExit(f"wiki node list missing data: {payload}")
        items = [item for item in data.get("items", []) if isinstance(item, dict)]
        return {
            "container_kind": "wiki",
            "space_id": resolved_space_id,
            "parent_node_token": normalized_node_token,
            "items": [
                {
                    "title": item.get("title"),
                    "node_token": item.get("node_token"),
                    "obj_token": item.get("obj_token"),
                    "obj_type": item.get("obj_type"),
                    "url": (
                        build_wiki_url(str(item.get("node_token")))
                        if item.get("node_token")
                        else (
                            build_object_url(str(item.get("obj_type")), str(item.get("obj_token")))
                            if item.get("obj_type") and item.get("obj_token")
                            else None
                        )
                    ),
                    "raw": item,
                }
                for item in items
            ],
            "has_more": bool(data.get("has_more")),
            "page_token": data.get("page_token"),
        }

    query = {"page_size": str(page_size)}
    if page_token:
        query["page_token"] = page_token
    if order_by:
        query["order_by"] = order_by
    if direction:
        query["direction"] = direction
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/drive/v1/files?{urllib.parse.urlencode(query)}",
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    raise_for_lark_failure("drive root list", status, payload, text)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SystemExit(f"drive root list missing data: {payload}")
    files = [item for item in data.get("files", []) if isinstance(item, dict)]
    return {
        "container_kind": "my_drive_root",
        "items": [
            {
                "title": item.get("name"),
                "token": item.get("token"),
                "type": item.get("type"),
                "url": item.get("url"),
                "parent_token": item.get("parent_token"),
                "owner_id": item.get("owner_id"),
                "raw": item,
            }
            for item in files
        ],
        "has_more": bool(data.get("has_more")),
        "page_token": data.get("next_page_token"),
    }


def update_document_title(document_id: str, title: str, bearer_token: str) -> dict[str, object]:
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}",
        method="PATCH",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(
            {
                "update_text": {
                    "elements": make_text_elements(title),
                    "fields": [1],
                    "style": {"align": 1},
                }
            },
            ensure_ascii=True,
        ).encode("utf-8"),
    )
    raise_for_lark_failure("document title update", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def extract_text_elements_for_block(block: dict[str, object]) -> list[dict[str, object]] | None:
    block_type = block.get("block_type")
    if block_type == 2:
        elements = block.get("text", {}).get("elements")
    elif block_type in {3, 4, 5, 6, 7, 8, 9, 10, 11}:
        level = int(block_type) - 2
        elements = block.get(f"heading{level}", {}).get("elements")
    elif block_type == 12:
        elements = block.get("bullet", {}).get("elements")
    elif block_type == 13:
        elements = block.get("ordered", {}).get("elements")
    elif block_type == 14:
        elements = block.get("code", {}).get("elements")
    elif block_type == 15:
        elements = block.get("quote", {}).get("elements")
    elif block_type == 17:
        elements = block.get("todo", {}).get("elements")
    else:
        return None
    return elements if isinstance(elements, list) else None


def update_block_text_elements(
    document_id: str,
    block_id: str,
    elements: list[dict[str, object]],
    bearer_token: str,
) -> dict[str, object]:
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}",
        method="PATCH",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps({"update_text_elements": {"elements": elements}}, ensure_ascii=True).encode("utf-8"),
    )
    raise_for_lark_failure("update block text elements", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def create_descendants(
    document_id: str,
    parent_block_id: str,
    children_id: list[str],
    descendants: list[dict[str, object]],
    bearer_token: str,
    *,
    index: int | None = None,
) -> dict[str, object]:
    def sanitize(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: sanitize(item)
                for key, item in value.items()
                if not str(key).startswith("_g_feishu_")
            }
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        return value

    sanitized_descendants = [sanitize(block) for block in descendants]
    body: dict[str, object] = {"children_id": children_id, "descendants": sanitized_descendants}
    if index is not None:
        body["index"] = index
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/descendant",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body, ensure_ascii=True).encode("utf-8"),
    )
    raise_for_lark_failure("create descendants", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def delete_child_range(document_id: str, parent_block_id: str, start_index: int, end_index: int, bearer_token: str) -> dict[str, object]:
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children/batch_delete",
        method="DELETE",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps({"start_index": start_index, "end_index": end_index}, ensure_ascii=True).encode("utf-8"),
    )
    raise_for_lark_failure("delete child range", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def clear_document_children(document_id: str, bearer_token: str, *, batch_size: int = 200) -> int:
    page_block = get_page_block(document_id, bearer_token)
    children = page_block.get("children")
    child_count = len(children) if isinstance(children, list) else 0
    deleted = 0
    while child_count > 0:
        start_index = max(0, child_count - batch_size)
        delete_child_range(document_id, document_id, start_index, child_count, bearer_token)
        deleted += child_count - start_index
        child_count = start_index
    return deleted


def move_document_to_wiki(
    document_id: str,
    bearer_token: str,
    *,
    wiki_node: str | None,
    wiki_space: str | None,
) -> dict[str, object]:
    if not wiki_node and not wiki_space:
        return {}
    if wiki_node:
        node = fetch_wiki_node(wiki_node, bearer_token)
        space_id = node.get("space_id")
        if not isinstance(space_id, str) or not space_id:
            raise SystemExit(f"wiki node missing space_id: {node}")
        parent_wiki_token = wiki_node
    else:
        if not wiki_space:
            raise SystemExit("wiki_space is required when wiki_node is not provided")
        space_id = wiki_space
        parent_wiki_token = None
    body: dict[str, object] = {"obj_token": document_id, "obj_type": "docx"}
    if parent_wiki_token:
        body["parent_wiki_token"] = parent_wiki_token
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/wiki/v2/spaces/{space_id}/nodes/move_docs_to_wiki",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body, ensure_ascii=True).encode("utf-8"),
    )
    if status >= 400:
        raise SystemExit(f"move document to wiki failed: status={status} body={payload or text}")
    if payload.get("code") not in {None, 0}:
        raise SystemExit(f"move document to wiki failed: {payload}")
    data = payload.get("data")
    return data if isinstance(data, dict) else {}
