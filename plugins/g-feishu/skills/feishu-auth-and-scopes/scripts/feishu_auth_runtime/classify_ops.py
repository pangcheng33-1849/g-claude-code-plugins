from __future__ import annotations


ERROR_RULES = [
    (
        "missing_app_credentials",
        (
            "app_secret",
            "app secret",
            "app_id",
            "invalid app credential",
            "missing app credential",
        ),
        "application_owner",
        "Configure app_id and app_secret before requesting any token.",
    ),
    (
        "missing_tenant_token",
        (
            "tenant_access_token",
            "tenant token",
            "tenant_access",
        ),
        "tenant_admin",
        "Fetch a tenant access token first and retry with that bearer token.",
    ),
    (
        "missing_user_token",
        (
            "user_access_token",
            "user token",
            "authorization code",
            "oauth code",
            "refresh token",
        ),
        "current_user",
        "Finish the user OAuth flow and exchange the code or refresh_token for a user_access_token.",
    ),
    (
        "oauth_callback_misconfigured",
        (
            "redirect_uri",
            "callback",
            "redirect uri",
            "code verifier",
            "state mismatch",
        ),
        "application_owner",
        "Check redirect URI, state handling, and the OAuth callback route.",
    ),
    (
        "scope_insufficient",
        (
            "scope",
            "permission denied",
            "forbidden",
            "403",
            "insufficient permission",
        ),
        "application_owner_or_user",
        "Compare the required scope with the app scope set and the current user grant.",
    ),
]


def classify_operation(operation: str) -> dict[str, object]:
    text = operation.lower()
    if any(token in text for token in ("task", "todo", "calendar", "event", "freebusy", "attendee", "schedule")):
        return {
            "identity": "user",
            "recommended_token": "user_access_token",
            "reason": "Task and calendar operations typically act on a user's own workspace objects.",
            "likely_scopes": ["task:task:write", "calendar:calendar.event:create"],
        }
    if any(token in text for token in ("oauth", "authorize", "login", "consent", "auth code")):
        return {
            "identity": "user",
            "recommended_token": "authorization_code -> user_access_token",
            "reason": "OAuth flows produce user-granted tokens.",
            "likely_scopes": [],
        }
    if any(token in text for token in ("bitable", "record", "table", "doc", "wiki", "drive", "sheet", "file", "comment")):
        return {
            "identity": "tenant_or_user",
            "recommended_token": "tenant_access_token or user_access_token",
            "reason": "Docs and bitable work can be tenant-driven or user-driven depending on ownership and sharing.",
            "likely_scopes": ["base:record:create", "docs:document.content:read"],
        }
    if any(token in text for token in ("scope", "callback", "secret", "app manage", "self_manage", "app permission")):
        return {
            "identity": "app",
            "recommended_token": "app credentials first",
            "reason": "Application management questions are owned by the app itself rather than a tenant user.",
            "likely_scopes": ["application:application:self_manage"],
        }
    return {
        "identity": "tenant",
        "recommended_token": "tenant_access_token",
        "reason": "Default to tenant-level access when the action is not clearly user-owned.",
        "likely_scopes": [],
    }


def classify_error(text: str) -> dict[str, object]:
    lowered = text.lower()
    for bucket, needles, owner, next_action in ERROR_RULES:
        if any(needle in lowered for needle in needles):
            return {
                "bucket": bucket,
                "fix_owner": owner,
                "next_action": next_action,
            }
    return {
        "bucket": "unknown",
        "fix_owner": "human_review",
        "next_action": "Collect the raw error text, endpoint, token type, and required scope before retrying.",
    }
