from __future__ import annotations

"""Schema lookup helpers shared by field, record, and view commands."""

from .api import ensure_success, request_json
from .common import fail
from .field_types import build_field_schema_map


def list_fields_raw(*, token: str, auth_mode: str, app_token: str, table_id: str) -> list[dict[str, object]]:
    response = request_json(
        method="GET",
        path=f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
        token=token,
        query={"page_size": 100},
    )
    ensure_success(response, api_alias="bitable_v1_app_table_field_list", auth_mode=auth_mode)
    return response.get("data", {}).get("items", [])


def resolve_field_defaults(
    *,
    token: str,
    auth_mode: str,
    app_token: str,
    table_id: str,
    field_id: str,
    field_name: str | None,
    field_type: int | None,
    property_value: object | None,
) -> tuple[str, int, object | None]:
    if field_name is not None and field_type is not None:
        return field_name, field_type, property_value
    current_fields = list_fields_raw(token=token, auth_mode=auth_mode, app_token=app_token, table_id=table_id)
    current_field = next((item for item in current_fields if item.get("field_id") == field_id), None)
    if current_field is None:
        fail(
            f"Field {field_id} not found. Use list-fields to inspect the table schema first.",
            api_alias="bitable_v1_app_table_field_list",
            auth_mode=auth_mode,
        )
    final_name = field_name if field_name is not None else str(current_field.get("field_name", ""))
    final_type = field_type if field_type is not None else int(current_field.get("type"))
    final_property = property_value if property_value is not None else current_field.get("property")
    return final_name, final_type, final_property


def load_table_schema_map(*, token: str, auth_mode: str, app_token: str, table_id: str) -> dict[str, dict[str, object]]:
    return build_field_schema_map(list_fields_raw(token=token, auth_mode=auth_mode, app_token=app_token, table_id=table_id))


def create_view_raw(
    *,
    token: str,
    app_token: str,
    table_id: str,
    view_name: str,
    view_type: str = "grid",
) -> dict[str, object]:
    return request_json(
        method="POST",
        path=f"/bitable/v1/apps/{app_token}/tables/{table_id}/views",
        token=token,
        body={"view_name": view_name, "view_type": view_type},
    )
