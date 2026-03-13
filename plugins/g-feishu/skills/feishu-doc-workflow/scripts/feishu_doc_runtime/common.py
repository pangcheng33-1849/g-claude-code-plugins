from __future__ import annotations

"""Shared low-level helpers for HTTP, ids, task state, and token-safe IO."""

import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request


MEDIA_TOKEN_PATTERN = re.compile(r"^(boxcn|file_|img_|image_|imgv|img_v)[A-Za-z0-9_-]+$")
IMAGE_MIME_PREFIXES = ("image/",)
BLOCK_TYPE_TO_KIND = {
    23: "file",
    27: "image",
    43: "whiteboard",
}
CODE_LANGUAGE_MAP = {
    "plaintext": 1,
    "text": 1,
    "abap": 2,
    "ada": 3,
    "apache": 4,
    "apex": 5,
    "asm": 6,
    "assembly": 6,
    "bash": 7,
    "sh": 60,
    "zsh": 60,
    "csharp": 8,
    "cs": 8,
    "cpp": 9,
    "c++": 9,
    "c": 10,
    "css": 12,
    "dockerfile": 18,
    "go": 22,
    "groovy": 23,
    "html": 24,
    "json": 28,
    "java": 29,
    "javascript": 30,
    "js": 30,
    "kotlin": 32,
    "latex": 33,
    "lua": 36,
    "markdown": 39,
    "nginx": 40,
    "objective-c": 41,
    "objc": 41,
    "php": 43,
    "powershell": 46,
    "protobuf": 48,
    "python": 49,
    "py": 49,
    "ruby": 52,
    "rust": 53,
    "scss": 55,
    "sql": 56,
    "scala": 57,
    "shell": 60,
    "swift": 61,
    "typescript": 63,
    "ts": 63,
    "xml": 66,
    "yaml": 67,
    "yml": 67,
    "diff": 69,
    "graphql": 71,
    "toml": 75,
}
TEMP_ELLIPSIS_MARKER = "__G_FEISHU_LITERAL_ELLIPSIS__"
IMPORT_EXTRA_HINTS = {
    "1000": "导入内容块数量超过新版文档上限，超出部分被截断。",
    "1001": "导入表格单元格数量超过新版文档上限，超出部分被截断。",
    "1002": "导入表格列数超过新版文档上限，超出部分被截断。",
    "1003": "导入单段文本长度超过新版文档上限，超出部分被截断。",
    "1005": "导入后的新版文档中，部分图片上传失败。",
    "2000": "电子表格列数超过上限，超出部分被截断。",
    "2001": "电子表格单元格数超过上限，超出部分被截断。",
    "2002": "电子表格图片超过 4000 张，超出图片被丢弃。",
    "2003": "电子表格导入时云空间存储不足。",
    "2004": "电子表格中部分图片上传失败。",
    "2005": "电子表格单元格字符长度超过上限，超出部分被截断。",
    "3000": "多维表格图片超出数据行区域，被系统丢弃。",
    "3001": "多维表格图片超出数据列区域，被系统丢弃。",
    "3003": "多维表格列数超过上限，超出部分被截断。",
    "3004": "多维表格单元格数超过上限，超出部分被截断。",
    "3005": "多维表格图片超过 4000 张，超出图片被丢弃。",
    "3006": "多维表格中部分图片上传失败。",
}


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, object], str]:
    request = urllib.request.Request(url, headers=headers or {}, data=data, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8")
            payload = json.loads(text) if text else {}
            return response.status, payload, text
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            payload = json.loads(text) if text else {}
        except json.JSONDecodeError:
            payload = {"raw_body": text}
        return exc.code, payload, text


def http_bytes(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: int = 60,
) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers=headers or {}, data=data, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items())


def payload_code(payload: dict[str, object]) -> int | None:
    value = payload.get("code")
    return value if isinstance(value, int) else None


def payload_message(payload: dict[str, object]) -> str:
    for key in ("msg", "message", "error_description", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def dedupe_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys([item for item in values if item]))


def resolve_lark_web_base_url() -> str | None:
    for env_name in ("MY_LARK_WEB_BASE_URL", "FEISHU_WEB_BASE_URL", "LARK_WEB_BASE_URL"):
        env_value = os.getenv(env_name)
        if isinstance(env_value, str) and env_value.strip():
            return env_value.strip().rstrip("/")
    return None


def build_lark_resource_url(path: str) -> str | None:
    base_url = resolve_lark_web_base_url()
    if not base_url:
        return None
    return f"{base_url}/{path.lstrip('/')}"


def build_web_link_notice(*, resource_kind: str) -> dict[str, str] | None:
    if resolve_lark_web_base_url():
        return None
    return {
        "reason": "web_base_url_not_configured",
        "env_var": "MY_LARK_WEB_BASE_URL",
        "resource_kind": resource_kind,
        "message": (
            "当前未设置 MY_LARK_WEB_BASE_URL，因此本次输出不会包含可点击的租户内网页链接。"
            "如需返回可直接打开的文档或 wiki 链接，请先配置该环境变量。"
        ),
    }


def build_doc_url(document_id: str | None) -> str | None:
    if not document_id:
        return None
    return build_lark_resource_url(f"docx/{urllib.parse.quote(document_id)}")


def build_wiki_url(node_token: str | None) -> str | None:
    if not node_token:
        return None
    return build_lark_resource_url(f"wiki/{urllib.parse.quote(node_token)}")


def build_object_url(obj_type: str | None, obj_token: str | None) -> str | None:
    if not obj_type or not obj_token:
        return None
    return build_lark_resource_url(f"{urllib.parse.quote(obj_type)}/{urllib.parse.quote(obj_token)}")


def raise_for_lark_failure(action: str, status: int, payload: dict[str, object], raw_text: str) -> None:
    code = payload_code(payload)
    message = payload_message(payload)
    body = payload if payload else raw_text
    if status >= 400 or code not in {None, 0}:
        suffix = []
        if code is not None:
            suffix.append(f"code={code}")
        if message:
            suffix.append(f"msg={message}")
        detail = ", ".join(suffix)
        raise SystemExit(f"{action} failed: status={status}{', ' + detail if detail else ''} body={body}")


def require_env_or_arg(value: str | None, env_name: str, flag_name: str) -> str:
    if value:
        return value
    env_value = os.getenv(env_name)
    if env_value:
        return env_value
    raise SystemExit(f"{flag_name} is required, or set {env_name} in the environment")


def resolve_contact_email(value: str | None) -> str | None:
    if value is not None:
        return value.strip() or None
    for env_name in ("MY_LARK_EMAIL", "FEISHU_EMAIL", "LARK_EMAIL"):
        env_value = os.getenv(env_name)
        if env_value and env_value.strip():
            return env_value.strip()
    return None


def search_users_by_query(token: str, query: str) -> list[dict[str, object]]:
    url = "https://open.feishu.cn/open-apis/search/v1/user"
    status, payload, text = http_json(
        f"{url}?{urllib.parse.urlencode({'query': query, 'offset': 0, 'limit': 10})}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    if status >= 400 or payload.get("code") not in {None, 0}:
        return []
    data = payload.get("data", {})
    users = data.get("users", [])
    return users if isinstance(users, list) else []


def resolve_user_open_id_by_query(query: str, *, bearer_token: str | None = None) -> str:
    trimmed = query.strip()
    if not trimmed:
        raise SystemExit("user query is empty")

    search_tokens: list[str] = []
    if bearer_token:
        search_tokens.append(bearer_token)
    env_user_token = os.getenv("MY_LARK_USER_ACCESS_TOKEN", "").strip()
    if env_user_token and env_user_token not in search_tokens:
        search_tokens.append(env_user_token)
    if not search_tokens:
        raise SystemExit(
            "Resolving a user by email/name requires a search-capable user token. "
            "Pass --user-access-token or set MY_LARK_USER_ACCESS_TOKEN first."
        )

    def normalize(value: object) -> str:
        return str(value).strip().casefold() if value is not None else ""

    matches_by_open_id: dict[str, dict[str, object]] = {}
    for token in search_tokens:
        for user in search_users_by_query(token, trimmed):
            open_id = user.get("open_id")
            if isinstance(open_id, str) and open_id.strip():
                matches_by_open_id.setdefault(open_id.strip(), user)
        if matches_by_open_id:
            break

    if not matches_by_open_id:
        raise SystemExit(f"No GFeishu user found for query: {trimmed}")

    exact_matches = []
    needle = normalize(trimmed)
    for user in matches_by_open_id.values():
        candidates = (
            normalize(user.get("email")),
            normalize(user.get("name")),
            normalize(user.get("en_name")),
            normalize(user.get("user_id")),
            normalize(user.get("open_id")),
        )
        if needle in candidates:
            exact_matches.append(user)

    candidate_users = exact_matches or list(matches_by_open_id.values())
    if len(candidate_users) > 1:
        summary = [
            {
                "name": user.get("name"),
                "email": user.get("email"),
                "open_id": user.get("open_id"),
            }
            for user in candidate_users[:5]
        ]
        raise SystemExit(
            "Multiple GFeishu users matched the query. Refine the name/email or pass an explicit open_id. "
            f"Candidates: {summary}"
        )

    chosen = candidate_users[0]
    open_id = chosen.get("open_id")
    if not isinstance(open_id, str) or not open_id.strip():
        raise SystemExit(f"Matched user does not contain open_id: {chosen}")
    return open_id.strip()


def normalize_node_id(node_id: str | None) -> str | None:
    if not node_id:
        return None
    return node_id.replace("-", ":")


def extract_ref(ref: str) -> dict[str, object]:
    parsed = urllib.parse.urlparse(ref)
    if parsed.scheme and parsed.netloc:
        query = urllib.parse.parse_qs(parsed.query)
        node_id = normalize_node_id(query.get("node-id", [None])[0])
        parts = [part for part in parsed.path.split("/") if part]
        kind = parts[0] if parts else "unknown"
        token = parts[1] if len(parts) > 1 else None
        if kind == "design" and len(parts) > 2:
            token = parts[1]
        return {
            "kind": kind,
            "token": token,
            "node_id": node_id,
            "document_id": token,
            "url": ref,
        }
    token_match = re.match(r"^(docx|wiki|sheets|base|slides|file)[A-Za-z0-9_-]+$", ref)
    if token_match:
        kind = token_match.group(1)
        return {
            "kind": kind,
            "token": ref,
            "node_id": None,
            "document_id": ref,
            "url": None,
        }
    return {
        "kind": "unknown",
        "token": ref,
        "node_id": None,
        "document_id": ref,
        "url": None,
    }


def extract_folder_token(ref_or_token: str) -> str:
    parsed = urllib.parse.urlparse(ref_or_token)
    if parsed.scheme and parsed.netloc:
        match = re.search(r"/drive/folder/([A-Za-z0-9_-]+)", parsed.path)
        if match:
            return match.group(1)
    return ref_or_token.strip()


def fetch_wiki_node(token: str, bearer_token: str, obj_type: str = "wiki") -> dict[str, object]:
    url = (
        "https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node?"
        f"{urllib.parse.urlencode({'token': token, 'obj_type': obj_type})}"
    )
    status, payload, text = http_json(url, headers={"Authorization": f"Bearer {bearer_token}"})
    if status >= 400 or payload.get("code") not in {None, 0}:
        raise SystemExit(f"wiki node resolve failed: status={status} body={payload or text}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SystemExit(f"wiki node missing data: {payload}")
    node = data.get("node")
    if not isinstance(node, dict):
        raise SystemExit(f"wiki node missing node: {payload}")
    return node


def resolve_target_for_api(target: dict[str, object], bearer_token: str) -> dict[str, object]:
    kind = target.get("kind")
    token = target.get("token")
    if kind != "wiki" or not isinstance(token, str):
        resolved = dict(target)
        resolved["resolved_kind"] = target.get("kind")
        resolved["resolved_document_id"] = target.get("document_id")
        return resolved
    node = fetch_wiki_node(token, bearer_token)
    obj_token = node.get("obj_token")
    obj_type = node.get("obj_type")
    if not isinstance(obj_token, str) or not obj_token:
        raise SystemExit(f"wiki node does not point to a document object: {node}")
    resolved = dict(target)
    resolved["resolved_from_wiki"] = True
    resolved["resolved_kind"] = obj_type if isinstance(obj_type, str) and obj_type else "docx"
    resolved["resolved_document_id"] = obj_token
    resolved["wiki_node"] = node
    return resolved


def resolve_task_state_dir(explicit_dir: str | None = None) -> pathlib.Path:
    raw_dir = explicit_dir or os.getenv("FEISHU_DOC_TASK_DIR") or str(pathlib.Path.home() / ".g-feishu-doc-tasks")
    task_dir = pathlib.Path(raw_dir).expanduser().resolve()
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def task_state_path(task_id: str, explicit_dir: str | None = None) -> pathlib.Path:
    safe_task_id = re.sub(r"[^A-Za-z0-9._-]+", "_", task_id.strip())
    return resolve_task_state_dir(explicit_dir) / f"{safe_task_id}.json"


def write_task_state(task_id: str, payload: dict[str, object], explicit_dir: str | None = None) -> pathlib.Path:
    path = task_state_path(task_id, explicit_dir)
    serialized = {
        **payload,
        "task_id": task_id,
        "updated_at": int(time.time()),
    }
    path.write_text(json.dumps(serialized, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def read_task_state(task_id: str, explicit_dir: str | None = None) -> dict[str, object] | None:
    path = task_state_path(task_id, explicit_dir)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
