from __future__ import annotations

"""Field type aliases and property builders for common Bitable field kinds."""

import argparse

from .common import fail, load_json_value, normalize_json_list, normalize_json_object, parse_bool


FIELD_TYPE_ALIASES = {
    "text": 1,
    "number": 2,
    "single_select": 3,
    "single-select": 3,
    "multi_select": 4,
    "multi-select": 4,
    "date": 5,
    "datetime": 5,
    "checkbox": 7,
    "person": 11,
    "user": 11,
    "phone": 13,
    "link": 15,
    "url": 15,
    "attachment": 17,
}

FIELD_TYPE_PRIMARY_NAMES = {
    1: "text",
    2: "number",
    3: "single_select",
    4: "multi_select",
    5: "datetime",
    7: "checkbox",
    11: "person",
    13: "phone",
    15: "link",
    17: "attachment",
}


def resolve_field_type(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    alias = FIELD_TYPE_ALIASES.get(raw.lower())
    if alias is None:
        supported = ", ".join(sorted(set(FIELD_TYPE_ALIASES)))
        fail(f"Unsupported field type alias: {value}. Supported aliases: {supported}")
    return alias


def field_type_alias(field_type: object) -> str | None:
    try:
        return FIELD_TYPE_PRIMARY_NAMES.get(int(field_type))
    except (TypeError, ValueError):
        return None


def has_field_property_overrides(args: argparse.Namespace) -> bool:
    return any(
        [
            getattr(args, "property_json", None),
            getattr(args, "property_file", None),
            getattr(args, "options_json", None),
            getattr(args, "options_file", None),
            getattr(args, "options", None),
            getattr(args, "formatter", None),
            getattr(args, "date_formatter", None),
            getattr(args, "auto_fill", None) is not None,
        ]
    )


def normalize_select_options(value: object, *, name: str) -> list[dict[str, object]]:
    options = normalize_json_list(value, name=name)
    normalized: list[dict[str, object]] = []
    for item in options:
        if isinstance(item, str):
            normalized.append({"name": item})
            continue
        option = normalize_json_object(item, name=f"{name} item")
        if "name" not in option:
            fail(f"Every {name} item must include a name.")
        normalized.append(option)
    return normalized


def build_field_property(
    args: argparse.Namespace,
    *,
    field_type: int,
    base_property: object | None = None,
    creating: bool,
) -> object | None:
    explicit_property = load_json_value(getattr(args, "property_json", None), getattr(args, "property_file", None), default=None)
    if explicit_property is not None:
        return explicit_property

    property_dict = dict(base_property) if isinstance(base_property, dict) else {}

    if field_type in {3, 4}:
        options_value = None
        if getattr(args, "options_json", None) or getattr(args, "options_file", None):
            options_value = load_json_value(args.options_json, args.options_file, default=[])
        elif getattr(args, "options", None):
            options_value = args.options
        elif creating and not property_dict.get("options"):
            fail("single_select and multi_select fields require options. Use --option, --options-json, or --property-json.")
        if options_value is not None:
            property_dict["options"] = normalize_select_options(options_value, name="options")
        return property_dict

    if field_type == 2 and getattr(args, "formatter", None):
        property_dict["formatter"] = args.formatter
        return property_dict

    if field_type == 5:
        if getattr(args, "date_formatter", None):
            property_dict["date_formatter"] = args.date_formatter
        if getattr(args, "auto_fill", None) is not None:
            property_dict["auto_fill"] = parse_bool(args.auto_fill)
        return property_dict or None

    return property_dict or base_property


def build_field_schema_map(fields: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    schema: dict[str, dict[str, object]] = {}
    for item in fields:
        field_name = item.get("field_name")
        if isinstance(field_name, str) and field_name:
            schema[field_name] = item
    return schema


def normalize_field_item(field: dict[str, object]) -> dict[str, object]:
    normalized = dict(field)
    normalized["type_alias"] = field_type_alias(field.get("type"))
    return normalized


def strip_field_property_if_forbidden(field_payload: dict[str, object]) -> dict[str, object]:
    field_type = field_payload.get("type")
    if field_type in {7, 15} and "property" in field_payload:
        cleaned = dict(field_payload)
        cleaned.pop("property", None)
        return cleaned
    return field_payload
