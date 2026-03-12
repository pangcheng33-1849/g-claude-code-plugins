from __future__ import annotations

"""Normalize business-friendly record values to Feishu Bitable API payloads."""

import datetime as dt

from .common import normalize_json_object
from .field_types import resolve_field_type


DEFAULT_TIMEZONE = dt.timezone(dt.timedelta(hours=8), name="Asia/Shanghai")


def coerce_datetime_to_millis(value: object) -> object:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if not isinstance(value, str):
        return value
    raw = value.strip()
    if not raw:
        return value
    if raw.isdigit():
        return int(raw)
    iso = raw.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(iso)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=DEFAULT_TIMEZONE)
    return int(parsed.timestamp() * 1000)


def extract_plain_text(value: object) -> object:
    if not isinstance(value, list):
        return value
    if not all(isinstance(item, dict) for item in value):
        return value
    parts: list[str] = []
    for item in value:
        text = item.get("text")
        if text is None:
            return value
        parts.append(str(text))
    return "".join(parts)


def normalize_person_value(value: object) -> object:
    if isinstance(value, str):
        return [{"id": value}]
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        normalized: list[object] = []
        for item in value:
            if isinstance(item, str):
                normalized.append({"id": item})
            else:
                normalized.append(item)
        return normalized
    return value


def normalize_attachment_value(value: object) -> object:
    if isinstance(value, str):
        return [{"file_token": value}]
    if isinstance(value, dict):
        if "file_token" in value:
            return [value]
        return value
    if isinstance(value, list):
        normalized: list[object] = []
        for item in value:
            if isinstance(item, str):
                normalized.append({"file_token": item})
            else:
                normalized.append(item)
        return normalized
    return value


def normalize_link_value(value: object) -> object:
    if isinstance(value, str):
        return {"text": value, "link": value}
    if isinstance(value, dict):
        if "link" in value:
            text = value.get("text") or value.get("link")
            return {"text": text, "link": value.get("link")}
        if "url" in value:
            text = value.get("text") or value.get("url")
            return {"text": text, "link": value.get("url")}
    return value


def normalize_multi_select_value(value: object) -> object:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item.get("name", "")) if isinstance(item, dict) and "name" in item else str(item) for item in value]
    return value


def normalize_select_value(value: object) -> object:
    if isinstance(value, dict) and "name" in value:
        return str(value["name"])
    return value


def normalize_checkbox_value(value: object) -> object:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
    return value


def normalize_number_value(value: object) -> object:
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return value
        try:
            if "." in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return value
    return value


def normalize_record_field_value(value: object, field_schema: dict[str, object]) -> object:
    field_type = resolve_field_type(field_schema.get("type")) if field_schema.get("type") is not None else None
    if field_type == 1:
        return extract_plain_text(value)
    if field_type == 2:
        return normalize_number_value(value)
    if field_type == 3:
        return normalize_select_value(value)
    if field_type == 4:
        return normalize_multi_select_value(value)
    if field_type == 5:
        return coerce_datetime_to_millis(value)
    if field_type == 7:
        return normalize_checkbox_value(value)
    if field_type == 11:
        return normalize_person_value(value)
    if field_type == 13:
        return str(value) if value is not None else value
    if field_type == 15:
        return normalize_link_value(value)
    if field_type == 17:
        return normalize_attachment_value(value)
    return value


def normalize_record_fields(fields: dict[str, object], schema_map: dict[str, dict[str, object]]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for field_name, value in fields.items():
        schema = schema_map.get(field_name)
        normalized[field_name] = normalize_record_field_value(value, schema) if schema else value
    return normalized


def normalize_record_item(record: dict[str, object], schema_map: dict[str, dict[str, object]]) -> dict[str, object]:
    fields = record.get("fields")
    if isinstance(fields, dict):
        normalized = dict(record)
        normalized["fields"] = normalize_record_fields(fields, schema_map)
        return normalized
    return record


def normalize_record_batch_input(records: list[object], schema_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in records:
        record = normalize_json_object(item, name="record")
        updated = dict(record)
        fields = updated.get("fields")
        if isinstance(fields, dict):
            updated["fields"] = normalize_record_fields(fields, schema_map)
        normalized.append(updated)
    return normalized


def normalize_record_output_item(record: dict[str, object], schema_map: dict[str, dict[str, object]]) -> dict[str, object]:
    normalized = dict(record)
    fields = normalized.get("fields")
    if isinstance(fields, dict):
        normalized["fields"] = normalize_record_fields(fields, schema_map)
    return normalized


def normalize_record_output_list(records: list[object], schema_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in records:
        record = normalize_json_object(item, name="record")
        normalized.append(normalize_record_output_item(record, schema_map))
    return normalized


def normalize_record_filter(filter_value: object | None) -> object | None:
    if not isinstance(filter_value, dict):
        return filter_value
    conditions = filter_value.get("conditions")
    if not isinstance(conditions, list):
        return filter_value
    normalized_conditions = []
    for condition in conditions:
        if not isinstance(condition, dict):
            normalized_conditions.append(condition)
            continue
        if condition.get("operator") in {"isEmpty", "isNotEmpty"} and "value" not in condition:
            updated = dict(condition)
            updated["value"] = []
            normalized_conditions.append(updated)
        else:
            normalized_conditions.append(condition)
    updated_filter = dict(filter_value)
    updated_filter["conditions"] = normalized_conditions
    return updated_filter
