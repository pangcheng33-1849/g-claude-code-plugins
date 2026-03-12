from __future__ import annotations

"""Comment target resolution, normalization, and doc comment CRUD helpers."""

import json
import urllib.parse

from .common import (
    extract_ref,
    http_json,
    raise_for_lark_failure,
    resolve_target_for_api,
)


COMMENT_SUPPORTED_FILE_TYPES = {"doc", "docx", "sheet", "file", "slides"}


def normalize_comment_target(ref: str, bearer_token: str) -> dict[str, object]:
    target = extract_ref(ref)
    resolved = resolve_target_for_api(target, bearer_token)
    file_type = str(resolved.get("resolved_kind") or target.get("kind") or "docx")
    if file_type not in COMMENT_SUPPORTED_FILE_TYPES:
        raise SystemExit(
            f"comments currently support {sorted(COMMENT_SUPPORTED_FILE_TYPES)}, got {file_type} for ref={ref}"
        )
    file_token = resolved.get("resolved_document_id")
    if not isinstance(file_token, str) or not file_token:
        raise SystemExit(f"unable to resolve file token for comments: {resolved}")
    return {
        "target": target,
        "resolved_target": resolved,
        "file_token": file_token,
        "file_type": file_type,
    }


def parse_comment_elements_argument(raw_input: str) -> list[dict[str, object]]:
    try:
        parsed = json.loads(raw_input)
        if isinstance(parsed, list):
            elements = parsed
        elif isinstance(parsed, dict):
            elements = [parsed]
        else:
            raise SystemExit("--elements JSON must be an object or array")
    except json.JSONDecodeError:
        elements = [{"type": "text", "text": raw_input}]
    normalized: list[dict[str, object]] = []
    for element in elements:
        if not isinstance(element, dict):
            raise SystemExit(f"invalid comment element: {element}")
        normalized.append(element)
    if not normalized:
        raise SystemExit("comment elements cannot be empty")
    return normalized


def resolve_comment_mention_open_id(element: dict[str, object]) -> str:
    open_id = element.get("open_id")
    if isinstance(open_id, str) and open_id.strip():
        return open_id.strip()
    email = element.get("email")
    if isinstance(email, str) and email.strip():
        raise SystemExit("mention 元素当前仅支持 open_id，不支持用 email 兜底解析。")
    raise SystemExit(f"mention element requires open_id: {element}")


def convert_comment_elements_to_api_format(elements: list[dict[str, object]]) -> list[dict[str, object]]:
    api_elements: list[dict[str, object]] = []
    for element in elements:
        kind = str(element.get("type") or "text").strip().lower()
        if kind == "text":
            text = element.get("text")
            if not isinstance(text, str):
                raise SystemExit(f"text element requires text: {element}")
            api_elements.append({"type": "text_run", "text_run": {"text": text}})
            continue
        if kind == "link":
            text = element.get("text")
            url = element.get("url")
            if not isinstance(url, str) or not url.strip():
                raise SystemExit(f"link element requires url: {element}")
            if isinstance(text, str) and text:
                api_elements.append({"type": "text_run", "text_run": {"text": text}})
            api_elements.append({"type": "docs_link", "docs_link": {"url": url}})
            continue
        if kind == "mention":
            api_elements.append({"type": "person", "person": {"user_id": resolve_comment_mention_open_id(element)}})
            continue
        raise SystemExit(f"unsupported comment element type: {kind}")
    return api_elements


def stringify_comment_elements(elements: object) -> str:
    if not isinstance(elements, list):
        return ""
    parts: list[str] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        text_run = element.get("text_run")
        if isinstance(text_run, dict):
            text = text_run.get("text") or text_run.get("content")
            if isinstance(text, str) and text:
                parts.append(text)
                continue
        person = element.get("person")
        if isinstance(person, dict):
            user_id = person.get("user_id")
            if isinstance(user_id, str) and user_id:
                parts.append(f"<@{user_id}>")
                continue
        docs_link = element.get("docs_link")
        if isinstance(docs_link, dict):
            url = docs_link.get("url")
            if isinstance(url, str) and url:
                parts.append(url)
    return "".join(parts)


def list_comment_replies(
    *,
    file_token: str,
    file_type: str,
    comment_id: str,
    bearer_token: str,
    user_id_type: str = "open_id",
) -> list[dict[str, object]]:
    replies: list[dict[str, object]] = []
    page_token: str | None = None
    while True:
        query = {"file_type": file_type, "user_id_type": user_id_type, "page_size": "50"}
        if page_token:
            query["page_token"] = page_token
        status, payload, text = http_json(
            f"https://open.feishu.cn/open-apis/drive/v1/files/{file_token}/comments/{comment_id}/replies?{urllib.parse.urlencode(query)}",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        raise_for_lark_failure("comment replies list", status, payload, text)
        data = payload.get("data")
        if not isinstance(data, dict):
            break
        items = data.get("items")
        if isinstance(items, list):
            replies.extend(item for item in items if isinstance(item, dict))
        if not data.get("has_more"):
            break
        next_page_token = data.get("page_token")
        if not isinstance(next_page_token, str) or not next_page_token:
            break
        page_token = next_page_token
    return replies


def normalize_comment_item(comment: dict[str, object]) -> dict[str, object]:
    replies_container = comment.get("reply_list")
    replies = replies_container.get("replies") if isinstance(replies_container, dict) else None
    comment_text = ""
    if isinstance(replies, list) and replies:
        first_reply = replies[0]
        if isinstance(first_reply, dict):
            comment_text = stringify_comment_elements(first_reply.get("content", {}).get("elements"))
    normalized_replies: list[dict[str, object]] = []
    if isinstance(replies, list):
        for reply in replies:
            if not isinstance(reply, dict):
                continue
            normalized_replies.append(
                {
                    "reply_id": reply.get("reply_id"),
                    "user_id": reply.get("user_id"),
                    "create_time": reply.get("create_time"),
                    "update_time": reply.get("update_time"),
                    "text": stringify_comment_elements(reply.get("content", {}).get("elements")),
                    "raw": reply,
                }
            )
    anchor_payload = (
        comment.get("quote")
        or comment.get("quoted_content")
        or comment.get("selection")
        or comment.get("selection_text")
        or comment.get("highlighted_text")
        or comment.get("anchor")
        or comment.get("region")
    )
    is_whole = comment.get("is_whole")
    scope = "whole" if is_whole is not False else "inline"
    return {
        "comment_id": comment.get("comment_id"),
        "user_id": comment.get("user_id"),
        "create_time": comment.get("create_time"),
        "update_time": comment.get("update_time"),
        "is_solved": comment.get("is_solved"),
        "is_whole": is_whole,
        "scope": scope,
        "has_more_replies": comment.get("has_more"),
        "text": comment_text,
        "anchor": anchor_payload,
        "replies": normalized_replies,
        "raw": comment,
    }


def list_document_comments(
    *,
    ref: str,
    bearer_token: str,
    is_whole: bool | None = None,
    is_solved: bool | None = None,
    page_size: int = 50,
    page_token: str | None = None,
    user_id_type: str = "open_id",
    include_replies: bool = True,
) -> dict[str, object]:
    resolved = normalize_comment_target(ref, bearer_token)
    query: dict[str, str] = {"file_type": str(resolved["file_type"]), "user_id_type": user_id_type, "page_size": str(page_size)}
    if page_token:
        query["page_token"] = page_token
    if is_whole is not None:
        query["is_whole"] = str(is_whole).lower()
    if is_solved is not None:
        query["is_solved"] = str(is_solved).lower()
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/drive/v1/files/{resolved['file_token']}/comments?{urllib.parse.urlencode(query)}",
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    raise_for_lark_failure("comment list", status, payload, text)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SystemExit(f"comment list missing data: {payload}")
    comments = [item for item in data.get("items", []) if isinstance(item, dict)]
    if include_replies:
        for comment in comments:
            if comment.get("has_more") or (isinstance(comment.get("reply_list"), dict) and comment["reply_list"].get("replies")):
                comment["reply_list"] = {
                    "replies": list_comment_replies(
                        file_token=str(resolved["file_token"]),
                        file_type=str(resolved["file_type"]),
                        comment_id=str(comment.get("comment_id")),
                        bearer_token=bearer_token,
                        user_id_type=user_id_type,
                    )
                }
    return {
        "resolved_target": resolved["resolved_target"],
        "file_token": resolved["file_token"],
        "file_type": resolved["file_type"],
        "items": comments,
        "comments": [normalize_comment_item(item) for item in comments],
        "whole_comment_count": sum(1 for item in comments if item.get("is_whole") is not False),
        "inline_comment_count": sum(1 for item in comments if item.get("is_whole") is False),
        "has_more": bool(data.get("has_more")),
        "page_token": data.get("page_token"),
    }


def create_document_comment(
    *,
    ref: str,
    elements: list[dict[str, object]],
    bearer_token: str,
    user_id_type: str = "open_id",
) -> dict[str, object]:
    resolved = normalize_comment_target(ref, bearer_token)
    api_elements = convert_comment_elements_to_api_format(elements)
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/drive/v1/files/{resolved['file_token']}/comments?{urllib.parse.urlencode({'file_type': str(resolved['file_type']), 'user_id_type': user_id_type})}",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        data=json.dumps(
            {
                "reply_list": {
                    "replies": [
                        {
                            "content": {
                                "elements": api_elements,
                            }
                        }
                    ]
                }
            },
            ensure_ascii=True,
        ).encode("utf-8"),
    )
    raise_for_lark_failure("comment create", status, payload, text)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SystemExit(f"comment create missing data: {payload}")
    raw_result = dict(data)
    normalized = normalize_comment_item(raw_result)
    result = dict(raw_result)
    result["normalized"] = normalized
    result["resolved_target"] = resolved["resolved_target"]
    result["file_token"] = resolved["file_token"]
    result["file_type"] = resolved["file_type"]
    return result
