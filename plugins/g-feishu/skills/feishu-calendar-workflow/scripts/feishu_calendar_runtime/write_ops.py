"""Write-oriented calendar command handlers for create, update, and delete."""

from __future__ import annotations

import argparse
import os
import urllib.parse

from .common import (
    calendar_request,
    ensure_success,
    load_json_value,
    normalize_result,
    parse_time_expression,
    resolve_calendar_id,
    resolve_token,
    search_users_by_query,
    time_payload,
    print_json,
    fail,
)


def build_event_data(args: argparse.Namespace) -> dict[str, object]:
    start = parse_time_expression(args.start, args.timezone)
    end = parse_time_expression(args.end, args.timezone)
    event_data: dict[str, object] = {
        "summary": args.summary,
        "description": args.description or args.summary,
        "start_time": time_payload(start, args.timezone),
        "end_time": time_payload(end, args.timezone),
        "need_notification": True if args.need_notification is None else args.need_notification,
        "attendee_ability": args.attendee_ability,
    }
    if args.location:
        event_data["location"] = {"name": args.location}
    if args.visibility:
        event_data["visibility"] = args.visibility
    if args.reminder_minutes:
        event_data["reminders"] = [{"minutes": minute} for minute in args.reminder_minutes]
    extra = load_json_value(args.extra_json, args.extra_json_file)
    if extra:
        event_data.update(extra)
    return event_data


def resolve_attendee_open_ids(*, args: argparse.Namespace, token: str, auth_mode: str) -> list[str]:
    explicit_open_ids = [value.strip() for value in getattr(args, "attendee_open_id", []) if value and value.strip()]
    if explicit_open_ids:
        return list(dict.fromkeys(explicit_open_ids))

    query_candidates: list[str] = [
        value.strip() for value in getattr(args, "attendee_query", []) if value and value.strip()
    ]
    query_candidates.extend(
        value.strip() for value in getattr(args, "attendee_email", []) if value and value.strip()
    )
    env_email = os.environ.get("MY_LARK_EMAIL", "").strip()
    if env_email:
        query_candidates.append(env_email)
    query_candidates = list(dict.fromkeys(query_candidates))
    if not query_candidates:
        return []

    search_tokens: list[str] = [token]

    resolved: list[str] = []
    for query in query_candidates:
        matches: dict[str, dict[str, object]] = {}
        for search_token in search_tokens:
            users = search_users_by_query(token=search_token, query=query)
            for user in users:
                open_id = user.get("open_id")
                if isinstance(open_id, str) and open_id.strip():
                    matches.setdefault(open_id.strip(), user)
            if matches:
                break
        if not matches:
            raise SystemExit(f"Could not resolve attendee query to an open_id: {query}")
        exact_matches = []
        needle = query.strip().casefold()
        for user in matches.values():
            candidates = (
                str(user.get("email") or "").strip().casefold(),
                str(user.get("name") or "").strip().casefold(),
                str(user.get("en_name") or "").strip().casefold(),
                str(user.get("open_id") or "").strip().casefold(),
                str(user.get("user_id") or "").strip().casefold(),
            )
            if needle in candidates:
                exact_matches.append(user)
        candidate_users = exact_matches or list(matches.values())
        if len(candidate_users) > 1:
            raise SystemExit(
                "Multiple Feishu users matched attendee query. Refine the name/email or pass --attendee-open-id. "
                f"Query={query!r} candidates={[{'name': u.get('name'), 'email': u.get('email'), 'open_id': u.get('open_id')} for u in candidate_users[:5]]}"
            )
        resolved.append(str(candidate_users[0]["open_id"]))
    return list(dict.fromkeys(resolved))


def resolve_user_visible_app_link(
    *,
    event_id: str,
    attendee_open_ids: list[str],
    user_access_token: str | None = None,
) -> tuple[str | None, dict[str, object] | None]:
    if not user_access_token:
        return None, {"reason": "No user access token provided. Pass --user-access-token to enable user-visible link resolution."}

    calendars_response = calendar_request(
        method="GET",
        path="/calendar/v4/calendars",
        token=user_access_token,
        query={"page_size": 50},
    )
    if calendars_response.get("code") != 0:
        return None, {
            "reason": calendars_response.get("msg") or "calendar list failed for user token",
            "response": calendars_response,
        }
    calendar_list = calendars_response.get("data", {}).get("calendar_list", [])
    user_calendar = next((item for item in calendar_list if item.get("type") == "primary"), None) or (calendar_list[0] if calendar_list else None)
    if not user_calendar or not user_calendar.get("calendar_id"):
        return None, {"reason": "No user-visible calendar found for the provided user access token."}

    calendar_id = str(user_calendar["calendar_id"])
    response = calendar_request(
        method="GET",
        path=f"/calendar/v4/calendars/{urllib.parse.quote(calendar_id, safe='')}/events/{urllib.parse.quote(event_id, safe='')}",
        token=user_access_token,
    )
    if response.get("code") != 0:
        return None, {
            "reason": response.get("msg") or "calendar event get failed for user token",
            "response": response,
            "calendar_id": calendar_id,
        }
    event = response.get("data", {}).get("event", {})
    return (
        event.get("app_link"),
        {
            "calendar_id": calendar_id,
            "calendar_meta": user_calendar,
            "event_id": event.get("event_id"),
            "self_rsvp_status": event.get("self_rsvp_status"),
        },
    )


def create_event_attendees(
    *,
    calendar_id: str,
    event_id: str,
    attendee_open_ids: list[str],
    token: str,
    auth_mode: str,
    need_notification: bool = True,
) -> dict[str, object]:
    response = calendar_request(
        method="POST",
        path=f"/calendar/v4/calendars/{urllib.parse.quote(calendar_id, safe='')}/events/{urllib.parse.quote(event_id, safe='')}/attendees",
        token=token,
        query={"user_id_type": "open_id"},
        body={
            "attendees": [
                {"type": "user", "user_id": open_id, "is_optional": False}
                for open_id in attendee_open_ids
            ],
            "need_notification": need_notification,
        },
    )
    if response.get("code") != 0:
        fail(
            "calendar_v4_calendarEventAttendee_create failed after event creation. "
            "The event was created, but attendees were not added.",
            api_alias="calendar_v4_calendarEventAttendee_create",
            auth_mode=auth_mode,
            response=response,
        )
    return response


def build_update_data(args: argparse.Namespace) -> dict[str, object]:
    event_data: dict[str, object] = {}
    if args.set_summary is not None:
        event_data["summary"] = args.set_summary
    if args.set_description is not None:
        event_data["description"] = args.set_description
    if args.set_start is not None:
        event_data["start_time"] = time_payload(parse_time_expression(args.set_start, args.timezone), args.timezone)
    if args.set_end is not None:
        event_data["end_time"] = time_payload(parse_time_expression(args.set_end, args.timezone), args.timezone)
    if args.set_location is not None:
        event_data["location"] = {"name": args.set_location}
    if args.set_visibility is not None:
        event_data["visibility"] = args.set_visibility
    if args.set_reminder_minutes:
        event_data["reminders"] = [{"minutes": minute} for minute in args.set_reminder_minutes]
    if args.set_need_notification is not None:
        event_data["need_notification"] = args.set_need_notification
    if args.set_attendee_ability is not None:
        event_data["attendee_ability"] = args.set_attendee_ability
    extra = load_json_value(args.extra_json, args.extra_json_file)
    if extra:
        event_data.update(extra)
    return event_data


def cmd_create_event(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="create-event",
        prefer_tenant=True,
    )
    attendee_open_ids: list[str] = []
    if "tenant" in auth_mode:
        attendee_open_ids = resolve_attendee_open_ids(args=args, token=token, auth_mode=auth_mode)
        if not attendee_open_ids:
            fail(
                "create-event is running in tenant mode and must add at least one user attendee. "
                "Pass --attendee-open-id, or provide --attendee-query / --attendee-email (or set MY_LARK_EMAIL) "
                "so the helper can resolve a user to open_id via search.",
                api_alias="calendar_v4_calendarEvent_create",
                auth_mode=auth_mode,
            )
    calendar_id, primary_meta = resolve_calendar_id(token=token, auth_mode=auth_mode, calendar_id=args.calendar_id)
    event_data = build_event_data(args)
    response = calendar_request(
        method="POST",
        path=f"/calendar/v4/calendars/{urllib.parse.quote(calendar_id, safe='')}/events",
        token=token,
        body=event_data,
    )
    ensure_success(response, api_alias="calendar_v4_calendarEvent_create", auth_mode=auth_mode)
    event = response.get("data", {}).get("event", {})
    attendee_add_result = None
    if attendee_open_ids:
        attendee_add_result = create_event_attendees(
            calendar_id=calendar_id,
            event_id=str(event.get("event_id")),
            attendee_open_ids=attendee_open_ids,
            token=token,
            auth_mode=auth_mode,
            need_notification=bool(event_data.get("need_notification", True)),
        )
    preferred_app_link = event.get("app_link")
    user_visible_app_link = None
    user_visible_app_link_meta = None
    if "tenant" in auth_mode and attendee_open_ids and event.get("event_id"):
        user_visible_app_link, user_visible_app_link_meta = resolve_user_visible_app_link(
            event_id=str(event.get("event_id")),
            attendee_open_ids=attendee_open_ids,
            user_access_token=args.user_access_token,
        )
        if user_visible_app_link:
            preferred_app_link = user_visible_app_link
    print_json(
        normalize_result(
            api_alias="calendar_v4_calendarEvent_create",
            auth_mode=auth_mode,
            response=response,
            calendar_id=calendar_id,
            primary_calendar_resolved=primary_meta,
            event_id=event.get("event_id"),
            app_link=event.get("app_link"),
            preferred_app_link=preferred_app_link,
            user_visible_app_link=user_visible_app_link,
            user_visible_app_link_meta=user_visible_app_link_meta,
            attendee_open_ids=attendee_open_ids,
            attendee_add_result=attendee_add_result,
            event=event,
        )
    )


def cmd_update_event(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="update-event",
    )
    calendar_id, primary_meta = resolve_calendar_id(token=token, auth_mode=auth_mode, calendar_id=args.calendar_id)
    event_data = build_update_data(args)
    if not event_data:
        fail("update-event requires at least one change field.", api_alias="calendar_v4_calendarEvent_patch", auth_mode=auth_mode)
    response = calendar_request(
        method="PATCH",
        path=f"/calendar/v4/calendars/{urllib.parse.quote(calendar_id, safe='')}/events/{urllib.parse.quote(args.event_id, safe='')}",
        token=token,
        body=event_data,
    )
    ensure_success(response, api_alias="calendar_v4_calendarEvent_patch", auth_mode=auth_mode)
    event = response.get("data", {}).get("event", {})
    print_json(
        normalize_result(
            api_alias="calendar_v4_calendarEvent_patch",
            auth_mode=auth_mode,
            response=response,
            calendar_id=calendar_id,
            primary_calendar_resolved=primary_meta,
            event_id=args.event_id,
            event=event,
        )
    )


def cmd_delete_event(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="delete-event",
    )
    calendar_id, primary_meta = resolve_calendar_id(token=token, auth_mode=auth_mode, calendar_id=args.calendar_id)
    response = calendar_request(
        method="DELETE",
        path=f"/calendar/v4/calendars/{urllib.parse.quote(calendar_id, safe='')}/events/{urllib.parse.quote(args.event_id, safe='')}",
        token=token,
    )
    ensure_success(response, api_alias="calendar_v4_calendarEvent_delete", auth_mode=auth_mode)
    print_json(
        normalize_result(
            api_alias="calendar_v4_calendarEvent_delete",
            auth_mode=auth_mode,
            response=response,
            calendar_id=calendar_id,
            primary_calendar_resolved=primary_meta,
            event_id=args.event_id,
            deleted=True,
        )
    )
