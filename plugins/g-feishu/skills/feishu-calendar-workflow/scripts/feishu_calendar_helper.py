#!/usr/bin/env python3
from __future__ import annotations

"""CLI entrypoint and parser wiring for the Feishu calendar workflow helper."""

import argparse
from feishu_calendar_runtime.common import (
    add_calendar_arg,
    add_common_event_args,
    add_create_defaults_args,
    add_token_args,
    add_update_defaults_args,
)
from feishu_calendar_runtime.read_ops import (
    cmd_freebusy,
    cmd_get_event,
    cmd_list_calendars,
    cmd_list_events,
)
from feishu_calendar_runtime.write_ops import (
    cmd_create_event,
    cmd_delete_event,
    cmd_update_event,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Feishu calendar workflow helper with real Calendar v4 API commands. "
        "create-event defaults to tenant token first; other commands remain user-first. "
        "Use Agent Skill feishu-auth-and-scopes to obtain or refresh tokens first."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_calendars = subparsers.add_parser(
        "list-calendars",
        help="List calendars visible to the current identity and identify the primary calendar.",
    )
    add_token_args(list_calendars)
    list_calendars.add_argument("--page-size", type=int, default=50, help="Calendar API requires page_size >= 50.")
    list_calendars.add_argument("--page-token")
    list_calendars.set_defaults(func=cmd_list_calendars)

    list_events = subparsers.add_parser(
        "list-events",
        help="List events from a calendar. Defaults to the primary calendar when --calendar-id is omitted.",
    )
    add_token_args(list_events)
    add_calendar_arg(list_events)
    list_events.add_argument("--page-size", type=int, default=50)
    list_events.add_argument("--page-token")
    list_events.set_defaults(func=cmd_list_events)

    create_event = subparsers.add_parser(
        "create-event",
        help="Create a real calendar event. Defaults to the primary calendar when --calendar-id is omitted.",
    )
    add_token_args(create_event)
    add_calendar_arg(create_event)
    create_event.add_argument("--summary", required=True)
    create_event.add_argument("--description")
    create_event.add_argument("--start", required=True)
    create_event.add_argument("--end", required=True)
    create_event.add_argument("--extra-json", help="Inline JSON merged into event_data.")
    create_event.add_argument("--extra-json-file", help="JSON file merged into event_data.")
    add_common_event_args(create_event)
    add_create_defaults_args(create_event)
    create_event.set_defaults(func=cmd_create_event)

    get_event = subparsers.add_parser(
        "get-event",
        help="Get a real calendar event by event_id. Defaults to the primary calendar when --calendar-id is omitted.",
    )
    add_token_args(get_event)
    add_calendar_arg(get_event)
    get_event.add_argument("--event-id", required=True)
    get_event.set_defaults(func=cmd_get_event)

    update_event = subparsers.add_parser(
        "update-event",
        help="Patch a calendar event. Provide one or more --set-* fields.",
    )
    add_token_args(update_event)
    add_calendar_arg(update_event)
    update_event.add_argument("--event-id", required=True)
    update_event.add_argument("--set-summary")
    update_event.add_argument("--set-description")
    update_event.add_argument("--set-start")
    update_event.add_argument("--set-end")
    update_event.add_argument("--set-location")
    update_event.add_argument("--set-visibility", choices=["default", "public", "private"])
    update_event.add_argument("--set-reminder-minutes", type=int, action="append", default=[], help="Reminder minutes before the event; can repeat.")
    update_event.add_argument("--extra-json", help="Inline JSON merged into the patch body.")
    update_event.add_argument("--extra-json-file", help="JSON file merged into the patch body.")
    update_event.add_argument("--timezone", default="Asia/Shanghai")
    add_update_defaults_args(update_event)
    update_event.set_defaults(func=cmd_update_event)

    delete_event = subparsers.add_parser(
        "delete-event",
        help="Delete a calendar event by event_id. Defaults to the primary calendar when --calendar-id is omitted.",
    )
    add_token_args(delete_event)
    add_calendar_arg(delete_event)
    delete_event.add_argument("--event-id", required=True)
    delete_event.set_defaults(func=cmd_delete_event)

    freebusy = subparsers.add_parser(
        "freebusy",
        help="Call the real freebusy API. The helper sends one request per user_id because the API expects a singular user_id field.",
    )
    add_token_args(freebusy)
    freebusy.add_argument("--start", required=True)
    freebusy.add_argument("--end", required=True)
    freebusy.add_argument("--timezone", default="Asia/Shanghai")
    freebusy.add_argument("--user-id-type", default="open_id", choices=["open_id", "user_id", "union_id"])
    freebusy.add_argument("--user-id", action="append", default=[], required=True, help="User identifier; repeat for multiple users.")
    freebusy.set_defaults(func=cmd_freebusy)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
