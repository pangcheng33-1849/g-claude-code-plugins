"""Read-oriented calendar command handlers and freebusy queries."""

from __future__ import annotations

import argparse

from .common import (
    calendar_request,
    ensure_success,
    normalize_result,
    parse_time_expression,
    print_json,
    resolve_calendar_id,
    resolve_token,
    utc_rfc3339,
)


def cmd_list_calendars(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="list-calendars",
    )
    response = calendar_request(
        method="GET",
        path="/calendar/v4/calendars",
        token=token,
        query={"page_size": args.page_size, "page_token": args.page_token},
    )
    ensure_success(response, api_alias="calendar_v4_calendars_list", auth_mode=auth_mode)
    calendars = response.get("data", {}).get("calendar_list", [])
    primary = next((item for item in calendars if item.get("type") == "primary"), None)
    print_json(
        normalize_result(
            api_alias="calendar_v4_calendars_list",
            auth_mode=auth_mode,
            response=response,
            calendar_count=len(calendars),
            primary_calendar_id=primary.get("calendar_id") if isinstance(primary, dict) else None,
            calendars=calendars,
        )
    )


def cmd_list_events(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="list-events",
    )
    calendar_id, primary_meta = resolve_calendar_id(token=token, auth_mode=auth_mode, calendar_id=args.calendar_id)
    response = calendar_request(
        method="GET",
        path=f"/calendar/v4/calendars/{calendar_id}/events",
        token=token,
        query={"page_size": args.page_size, "page_token": args.page_token},
    )
    ensure_success(response, api_alias="calendar_v4_calendarEvent_list", auth_mode=auth_mode)
    items = response.get("data", {}).get("items", [])
    print_json(
        normalize_result(
            api_alias="calendar_v4_calendarEvent_list",
            auth_mode=auth_mode,
            response=response,
            calendar_id=calendar_id,
            primary_calendar_resolved=primary_meta,
            event_count=len(items),
            events=items,
        )
    )


def cmd_get_event(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="get-event",
    )
    calendar_id, primary_meta = resolve_calendar_id(token=token, auth_mode=auth_mode, calendar_id=args.calendar_id)
    response = calendar_request(
        method="GET",
        path=f"/calendar/v4/calendars/{calendar_id}/events/{args.event_id}",
        token=token,
    )
    ensure_success(response, api_alias="calendar_v4_calendarEvent_get", auth_mode=auth_mode)
    event = response.get("data", {}).get("event", {})
    print_json(
        normalize_result(
            api_alias="calendar_v4_calendarEvent_get",
            auth_mode=auth_mode,
            response=response,
            calendar_id=calendar_id,
            primary_calendar_resolved=primary_meta,
            event_id=args.event_id,
            event=event,
        )
    )


def cmd_freebusy(args: argparse.Namespace) -> None:
    token, auth_mode = resolve_token(
        user_access_token=args.user_access_token,
        tenant_access_token=args.tenant_access_token,
        use_tenant_token=args.use_tenant_token,
        command_name="freebusy",
    )
    start = parse_time_expression(args.start, args.timezone)
    end = parse_time_expression(args.end, args.timezone)
    results: list[dict[str, object]] = []
    for user_id in args.user_id:
        response = calendar_request(
            method="POST",
            path="/calendar/v4/freebusy/list",
            token=token,
            query={"user_id_type": args.user_id_type},
            body={
                "time_min": utc_rfc3339(start),
                "time_max": utc_rfc3339(end),
                "user_id": user_id,
            },
        )
        ensure_success(response, api_alias="calendar_v4_freebusy_list", auth_mode=auth_mode)
        freebusy_list = response.get("data", {}).get("freebusy_list", [])
        busy_count = sum(len(item.get("free_busy_time", [])) for item in freebusy_list)
        results.append(
            {
                "user_id": user_id,
                "busy_block_count": busy_count,
                "freebusy_list": freebusy_list,
            }
        )
    print_json(
        normalize_result(
            api_alias="calendar_v4_freebusy_list",
            auth_mode=auth_mode,
            response={"code": 0, "msg": "success", "data": {"results": results}},
            timezone=args.timezone,
            time_min=utc_rfc3339(start),
            time_max=utc_rfc3339(end),
            user_id_type=args.user_id_type,
            result_count=len(results),
            results=results,
        )
    )

