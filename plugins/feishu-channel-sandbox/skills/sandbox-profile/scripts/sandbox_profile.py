#!/usr/bin/env python3
"""Manage Claude Code native sandbox profiles.

Applies/removes sandbox + permissions rules to .claude/settings.local.json
using a delete-then-add pattern to ensure clean profile switching.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

STATE_DIR = pathlib.Path.home() / ".claude" / "channels" / "feishu" / "sandbox-profile"
ACTIVE_FILE = STATE_DIR / "active"
PRESETS = {"default", "dev", "dangerously-open"}


def profiles_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent / "profiles"


def print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def load_json(path: pathlib.Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_json(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_active_profile() -> str | None:
    if ACTIVE_FILE.exists():
        name = ACTIVE_FILE.read_text(encoding="utf-8").strip()
        return name if name else None
    return None


def set_active_profile(name: str | None) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if name:
        ACTIVE_FILE.write_text(name + "\n", encoding="utf-8")
    elif ACTIVE_FILE.exists():
        ACTIVE_FILE.unlink()


def load_profile(name: str) -> dict:
    path = profiles_dir() / f"{name}.json"
    if not path.exists():
        print(f"Profile not found: {name}", file=sys.stderr)
        print(f"Available: {', '.join(list_profiles())}", file=sys.stderr)
        sys.exit(1)
    return load_json(path)


def list_profiles() -> list[str]:
    return sorted(
        p.stem for p in profiles_dir().glob("*.json")
    )


def settings_path(shared: bool) -> pathlib.Path:
    if shared:
        return pathlib.Path(".claude/settings.json")
    return pathlib.Path(".claude/settings.local.json")


def remove_profile_rules(settings: dict, profile: dict) -> dict:
    """Remove rules that came from a profile."""
    # Remove sandbox entirely
    settings.pop("sandbox", None)

    # Remove specific allow/deny rules from the profile
    profile_perms = profile.get("permissions", {})
    profile_allow = set(profile_perms.get("allow", []))
    profile_deny = set(profile_perms.get("deny", []))

    if "permissions" in settings:
        perms = settings["permissions"]
        if "allow" in perms and profile_allow:
            perms["allow"] = [r for r in perms["allow"] if r not in profile_allow]
            if not perms["allow"]:
                del perms["allow"]
        if "deny" in perms and profile_deny:
            perms["deny"] = [r for r in perms["deny"] if r not in profile_deny]
            if not perms["deny"]:
                del perms["deny"]
        # Clean up empty permissions object (keep if has other keys like defaultMode)
        if not perms:
            del settings["permissions"]

    return settings


def add_profile_rules(settings: dict, profile: dict) -> dict:
    """Add rules from a profile."""
    # Add sandbox
    if "sandbox" in profile:
        settings["sandbox"] = profile["sandbox"]

    # Add permissions
    profile_perms = profile.get("permissions", {})

    if profile_perms:
        if "permissions" not in settings:
            settings["permissions"] = {}
        perms = settings["permissions"]

        # Add allow rules (deduplicate)
        if "allow" in profile_perms:
            existing = set(perms.get("allow", []))
            new_rules = profile_perms["allow"]
            merged = list(perms.get("allow", []))
            for rule in new_rules:
                if rule not in existing:
                    merged.append(rule)
            perms["allow"] = merged

        # Add deny rules (deduplicate)
        if "deny" in profile_perms:
            existing = set(perms.get("deny", []))
            new_rules = profile_perms["deny"]
            merged = list(perms.get("deny", []))
            for rule in new_rules:
                if rule not in existing:
                    merged.append(rule)
            perms["deny"] = merged

        # Add defaultMode if present
        if "defaultMode" in profile_perms:
            perms["defaultMode"] = profile_perms["defaultMode"]

    return settings


def cmd_list(args: argparse.Namespace) -> None:
    active = get_active_profile()
    profiles = list_profiles()
    result = {
        "active_profile": active,
        "profiles": [],
    }
    for name in profiles:
        entry = {"name": name, "preset": name in PRESETS}
        if name == active:
            entry["active"] = True
        result["profiles"].append(entry)

    # Show current sandbox config
    path = settings_path(False)
    settings = load_json(path)
    result["current_sandbox"] = settings.get("sandbox")
    result["current_permissions_allow"] = (settings.get("permissions") or {}).get("allow")
    result["current_permissions_deny"] = (settings.get("permissions") or {}).get("deny")
    result["settings_file"] = str(path)

    print_json(result)


def cmd_show(args: argparse.Namespace) -> None:
    if args.name == "current":
        path = settings_path(False)
        settings = load_json(path)
        print_json({
            "settings_file": str(path),
            "active_profile": get_active_profile(),
            "sandbox": settings.get("sandbox"),
            "permissions": settings.get("permissions"),
        })
    else:
        profile = load_profile(args.name)
        print_json({"profile": args.name, "config": profile})


def cmd_apply(args: argparse.Namespace) -> None:
    new_profile = load_profile(args.name)
    shared = getattr(args, "shared", False)
    path = settings_path(shared)
    settings = load_json(path)

    # Step 1: Remove old profile's rules
    old_name = get_active_profile()
    if old_name:
        old_profile_path = profiles_dir() / f"{old_name}.json"
        if old_profile_path.exists():
            old_profile = load_json(old_profile_path)
            settings = remove_profile_rules(settings, old_profile)
        else:
            # Old profile file gone, remove sandbox anyway
            settings.pop("sandbox", None)

    # Step 2: Add new profile's rules
    settings = add_profile_rules(settings, new_profile)

    # Step 3: Save
    save_json(path, settings)
    set_active_profile(args.name)

    print_json({
        "action": "apply",
        "profile": args.name,
        "settings_file": str(path),
        "previous_profile": old_name,
        "sandbox_enabled": (settings.get("sandbox") or {}).get("enabled"),
        "message": f"Profile '{args.name}' applied. Claude Code will reload automatically.",
    })


def cmd_reset(args: argparse.Namespace) -> None:
    shared = getattr(args, "shared", False)
    path = settings_path(shared)
    settings = load_json(path)

    old_name = get_active_profile()
    if old_name:
        old_profile_path = profiles_dir() / f"{old_name}.json"
        if old_profile_path.exists():
            old_profile = load_json(old_profile_path)
            settings = remove_profile_rules(settings, old_profile)
        else:
            settings.pop("sandbox", None)

    save_json(path, settings)
    set_active_profile(None)

    print_json({
        "action": "reset",
        "settings_file": str(path),
        "previous_profile": old_name,
        "message": "Sandbox configuration removed.",
    })


def cmd_create(args: argparse.Namespace) -> None:
    name = args.name
    if name in PRESETS:
        print(f"Cannot overwrite preset profile: {name}", file=sys.stderr)
        sys.exit(1)

    base = args.base or "dev"
    base_profile = load_profile(base)
    target = profiles_dir() / f"{name}.json"
    save_json(target, base_profile)

    print_json({
        "action": "create",
        "profile": name,
        "base": base,
        "path": str(target),
        "message": f"Profile '{name}' created from '{base}'. Edit the file to customize.",
    })


def cmd_delete(args: argparse.Namespace) -> None:
    name = args.name
    if name in PRESETS:
        print(f"Cannot delete preset profile: {name}", file=sys.stderr)
        sys.exit(1)

    target = profiles_dir() / f"{name}.json"
    if not target.exists():
        print(f"Profile not found: {name}", file=sys.stderr)
        sys.exit(1)

    # If deleting the active profile, reset first
    if get_active_profile() == name:
        set_active_profile(None)

    target.unlink()
    print_json({
        "action": "delete",
        "profile": name,
        "message": f"Profile '{name}' deleted.",
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Claude Code sandbox profiles.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="List available profiles and current config.")

    show = subparsers.add_parser("show", help="Show a profile or current config.")
    show.add_argument("name", help="Profile name or 'current'.")

    apply_cmd = subparsers.add_parser("apply", help="Apply a profile to settings.")
    apply_cmd.add_argument("name", help="Profile name to apply.")
    apply_cmd.add_argument("--shared", action="store_true", help="Write to .claude/settings.json instead of .local.")

    reset_cmd = subparsers.add_parser("reset", help="Remove sandbox config from settings.")
    reset_cmd.add_argument("--shared", action="store_true", help="Reset .claude/settings.json instead of .local.")

    create_cmd = subparsers.add_parser("create", help="Create a custom profile.")
    create_cmd.add_argument("name", help="New profile name.")
    create_cmd.add_argument("base", nargs="?", default="dev", help="Base profile (default: dev).")

    delete_cmd = subparsers.add_parser("delete", help="Delete a custom profile.")
    delete_cmd.add_argument("name", help="Profile name to delete.")

    args = parser.parse_args()

    if args.command is None or args.command == "list":
        cmd_list(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "apply":
        cmd_apply(args)
    elif args.command == "reset":
        cmd_reset(args)
    elif args.command == "create":
        cmd_create(args)
    elif args.command == "delete":
        cmd_delete(args)


if __name__ == "__main__":
    main()
