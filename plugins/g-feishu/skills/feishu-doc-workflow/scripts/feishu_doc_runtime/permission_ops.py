from __future__ import annotations

"""Document permission member CRUD helpers."""

import json
import urllib.parse

from .common import http_json, raise_for_lark_failure


def grant_permission_member(
    *,
    token: str,
    doc_type: str,
    member_id: str,
    member_type: str = "email",
    bearer_token: str,
    perm: str = "full_access",
    need_notification: bool = False,
) -> dict[str, object]:
    query = urllib.parse.urlencode(
        {
            "type": doc_type,
            "need_notification": "true" if need_notification else "false",
        }
    )
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/members?{query}",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        data=json.dumps(
            {
                "member_id": member_id,
                "member_type": member_type,
                "perm": perm,
            },
            ensure_ascii=True,
        ).encode("utf-8"),
    )
    raise_for_lark_failure("grant permission member", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def update_permission_member(
    *,
    token: str,
    doc_type: str,
    member_id: str,
    member_type: str,
    perm: str,
    bearer_token: str,
    need_notification: bool = False,
) -> dict[str, object]:
    query = urllib.parse.urlencode(
        {
            "type": doc_type,
            "need_notification": "true" if need_notification else "false",
        }
    )
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/members/{urllib.parse.quote(member_id, safe='')}?{query}",
        method="PUT",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        data=json.dumps(
            {
                "member_type": member_type,
                "perm": perm,
            },
            ensure_ascii=True,
        ).encode("utf-8"),
    )
    raise_for_lark_failure("update permission member", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def remove_permission_member(
    *,
    token: str,
    doc_type: str,
    member_id: str,
    member_type: str,
    bearer_token: str,
) -> dict[str, object]:
    query = urllib.parse.urlencode(
        {
            "type": doc_type,
            "member_type": member_type,
        }
    )
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/members/{urllib.parse.quote(member_id, safe='')}?{query}",
        method="DELETE",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        data=json.dumps(
            {
                "member_type": member_type,
            },
            ensure_ascii=True,
        ).encode("utf-8"),
    )
    raise_for_lark_failure("remove permission member", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def transfer_permission_owner(
    *,
    token: str,
    doc_type: str,
    member_id: str,
    member_type: str,
    bearer_token: str,
    need_notification: bool = False,
    old_owner_perm: str | None = None,
    remove_old_owner: bool = False,
    stay_put: bool = False,
) -> dict[str, object]:
    query_dict: dict[str, str] = {
        "type": doc_type,
        "need_notification": "true" if need_notification else "false",
        "remove_old_owner": "true" if remove_old_owner else "false",
        "stay_put": "true" if stay_put else "false",
    }
    if old_owner_perm:
        query_dict["old_owner_perm"] = old_owner_perm
    query = urllib.parse.urlencode(query_dict)
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/members/transfer_owner?{query}",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        data=json.dumps(
            {
                "member_id": member_id,
                "member_type": member_type,
            },
            ensure_ascii=True,
        ).encode("utf-8"),
    )
    raise_for_lark_failure("transfer permission owner", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}
