from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOKEN_ENDPOINT = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
TENANT_TOKEN_ENDPOINT = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
DEVICE_AUTHORIZATION_ENDPOINT = "https://accounts.feishu.cn/oauth/v1/device_authorization"
DEFAULT_CACHE_ROOT = Path(os.getenv("FEISHU_AUTH_CACHE_DIR", str(Path.home() / ".feishu-auth-cache")))
USER_TOKEN_SKEW_SECONDS = 120
REFRESH_TOKEN_SKEW_SECONDS = 300


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def now_epoch() -> int:
    return int(time.time())


def iso_utc(epoch: int | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, Any], str]:
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(text) if text else {}
            except json.JSONDecodeError:
                payload = {}
            return response.status, payload, text
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(text) if text else {}
        except json.JSONDecodeError:
            payload = {}
        return exc.code, payload, text


def mask_secret(value: str | None, *, head: int = 6, tail: int = 4) -> str | None:
    if not value:
        return None
    if len(value) <= head + tail + 3:
        return "***"
    return f"{value[:head]}...{value[-tail:]}"


def sanitize_cache_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-") or "default"


def cache_root() -> Path:
    DEFAULT_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(DEFAULT_CACHE_ROOT, 0o700)
    except OSError:
        pass
    return DEFAULT_CACHE_ROOT


def load_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
