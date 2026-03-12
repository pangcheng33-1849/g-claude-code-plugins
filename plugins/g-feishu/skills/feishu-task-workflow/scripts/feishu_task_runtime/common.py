from __future__ import annotations

"""Shared parsing and normalization helpers for the task workflow runtime."""

import json
import pathlib
import re
import sys
import datetime as dt
DAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
LOCAL_TZ = dt.datetime.now().astimezone().tzinfo or dt.timezone.utc


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def fail(message: str, *, api_alias: str | None = None, auth_mode: str | None = None, response: object | None = None) -> None:
    payload: dict[str, object] = {"error": message}
    if api_alias:
        payload["api_alias"] = api_alias
    if auth_mode:
        payload["auth_mode"] = auth_mode
    if response is not None:
        payload["response"] = response
    print_json(payload)
    raise SystemExit(1)


def read_input(path: str | None) -> str:
    if path:
        return pathlib.Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def load_json_value(inline_json: str | None, file_path: str | None, *, default: object) -> object:
    value = default
    if file_path:
        try:
            value = json.loads(pathlib.Path(file_path).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"JSON file not found: {file_path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON file {file_path}: {exc.msg}") from exc
    if inline_json:
        try:
            value = json.loads(inline_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid inline JSON: {exc.msg}") from exc
    return value


def merge_objects(base: dict[str, object], extra: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    merged.update(extra)
    return merged


def normalize_bool(value: str | bool | None) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y"}:
        return True
    if lowered in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Unsupported boolean value: {value}")


def format_date(date_value: dt.date) -> str:
    return date_value.isoformat()


def extract_due_date(text: str) -> str | None:
    iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if iso_match:
        return iso_match.group(1)
    if re.search(r"\btomorrow\b", text, re.IGNORECASE):
        return format_date(dt.date.today() + dt.timedelta(days=1))
    in_days_match = re.search(r"\bin\s+(\d+)\s+days?\b", text, re.IGNORECASE)
    if in_days_match:
        return format_date(dt.date.today() + dt.timedelta(days=int(in_days_match.group(1))))
    weekday_match = re.search(
        r"\b(?:by|due|on)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        text,
        re.IGNORECASE,
    )
    if weekday_match:
        today = dt.date.today()
        current = today.weekday()
        target = DAY_NAMES[weekday_match.group(1).lower()]
        delta = target - current
        if delta <= 0:
            delta += 7
        return format_date(today + dt.timedelta(days=delta))
    return None


def extract_assignee(text: str) -> str | None:
    match = re.search(r"@([A-Za-z0-9._-]+)", text)
    return match.group(1) if match else None


def extract_todos(content: str) -> list[dict[str, object]]:
    todos: list[dict[str, object]] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        checklist = re.match(r"^-\s+\[([ xX])\]\s+(.+)$", line)
        if checklist:
            text = checklist.group(2).strip()
            todos.append(
                {
                    "text": text,
                    "completed": checklist.group(1).lower() == "x",
                    "due_date": extract_due_date(text),
                    "assignee": extract_assignee(text),
                }
            )
            continue
        todo_line = re.match(r"^TODO:?\s+(.+)$", line, re.IGNORECASE)
        if todo_line:
            text = todo_line.group(1).strip()
            todos.append(
                {
                    "text": text,
                    "completed": False,
                    "due_date": extract_due_date(text),
                    "assignee": extract_assignee(text),
                }
            )
    return todos


def due_payload(due_date: str | None) -> dict[str, str | bool] | None:
    if not due_date:
        return None
    due_dt = dt.datetime.fromisoformat(due_date).replace(hour=23, minute=59, second=59, tzinfo=dt.timezone.utc)
    return {
        "timestamp": str(int(due_dt.timestamp() * 1000)),
        "is_all_day": True,
    }


def build_payloads(todos: list[dict[str, object]]) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for todo in todos:
        payload: dict[str, object] = {
            "summary": todo["text"],
            "description": todo["text"],
        }
        due = due_payload(todo.get("due_date"))
        if due:
            payload["due"] = due
        assignee = todo.get("assignee")
        if assignee:
            payload["assignee_hint"] = assignee
        if todo.get("completed"):
            payload["completed_hint"] = True
        payloads.append(payload)
    return payloads


def parse_time_value(value: str, *, field: str) -> dict[str, str | bool]:
    stripped = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stripped):
        date_value = dt.date.fromisoformat(stripped)
        hour = 23 if field == "due" else 0
        minute = 59 if field == "due" else 0
        second = 59 if field == "due" else 0
        date_time = dt.datetime.combine(date_value, dt.time(hour, minute, second), tzinfo=LOCAL_TZ)
        return {"timestamp": str(int(date_time.timestamp() * 1000)), "is_all_day": True}
    try:
        date_time = dt.datetime.fromisoformat(stripped)
    except ValueError as exc:
        raise ValueError(f"Unsupported {field} format: {value}") from exc
    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=LOCAL_TZ)
    return {"timestamp": str(int(date_time.timestamp() * 1000)), "is_all_day": False}


def current_timestamp_ms() -> str:
    return str(int(dt.datetime.now(tz=dt.timezone.utc).timestamp() * 1000))
