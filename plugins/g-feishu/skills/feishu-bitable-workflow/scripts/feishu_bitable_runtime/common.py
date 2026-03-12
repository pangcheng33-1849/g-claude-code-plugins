from __future__ import annotations

"""Small JSON/CLI helpers shared by Bitable runtime modules."""

import json
import pathlib


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def fail(
    message: str,
    *,
    api_alias: str | None = None,
    auth_mode: str | None = None,
    response: object | None = None,
) -> None:
    payload: dict[str, object] = {"error": message}
    if api_alias:
        payload["api_alias"] = api_alias
    if auth_mode:
        payload["auth_mode"] = auth_mode
    if response is not None:
        payload["response"] = response
    print_json(payload)
    raise SystemExit(1)


def parse_bool(value: str | bool | None) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y"}:
        return True
    if lowered in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Unsupported boolean value: {value}")


def load_json_value(inline_json: str | None, file_path: str | None, *, default: object) -> object:
    value = default
    if file_path:
        value = json.loads(pathlib.Path(file_path).read_text(encoding="utf-8"))
    if inline_json:
        value = json.loads(inline_json)
    return value


def normalize_json_list(value: object, *, name: str) -> list[object]:
    if not isinstance(value, list):
        fail(f"{name} must be a JSON array.")
    return value


def normalize_json_object(value: object, *, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        fail(f"{name} must be a JSON object.")
    return value


def load_string_list(values: list[str] | None, inline_json: str | None, file_path: str | None, *, name: str) -> list[str]:
    if values:
        return values
    if inline_json or file_path:
        loaded = normalize_json_list(load_json_value(inline_json, file_path, default=[]), name=name)
        return [str(item) for item in loaded]
    return []
