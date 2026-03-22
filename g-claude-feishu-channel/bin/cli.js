#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

// ── Paths ──
const STATE_DIR = path.join(os.homedir(), ".claude", "channels", "feishu", "sandbox-profile");
const ACTIVE_FILE = path.join(STATE_DIR, "active");
const CUSTOM_PROFILES_DIR = path.join(STATE_DIR, "profiles");
const PRESET_PROFILES_DIR = path.join(__dirname, "..", "profiles");
const PRESETS = new Set(["default", "dev", "dangerously-open"]);

// ── Helpers ──
function loadJson(filePath) {
  try { return JSON.parse(fs.readFileSync(filePath, "utf-8")); }
  catch { return {}; }
}

function saveJson(filePath, data) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + "\n", "utf-8");
}

function settingsPath() {
  return path.join(process.cwd(), ".claude", "settings.local.json");
}

function profilePath(name) {
  const custom = path.join(CUSTOM_PROFILES_DIR, `${name}.json`);
  if (fs.existsSync(custom)) return custom;
  return path.join(PRESET_PROFILES_DIR, `${name}.json`);
}

function loadProfile(name) {
  const p = profilePath(name);
  if (!fs.existsSync(p)) {
    console.error(`Profile not found: ${name}`);
    console.error(`Available: ${listProfiles().join(", ")}`);
    process.exit(1);
  }
  return loadJson(p);
}

function listProfiles() {
  const names = new Set();
  for (const f of fs.readdirSync(PRESET_PROFILES_DIR))
    if (f.endsWith(".json")) names.add(f.replace(".json", ""));
  if (fs.existsSync(CUSTOM_PROFILES_DIR))
    for (const f of fs.readdirSync(CUSTOM_PROFILES_DIR))
      if (f.endsWith(".json")) names.add(f.replace(".json", ""));
  return [...names].sort();
}

function getActive() {
  if (!fs.existsSync(ACTIVE_FILE)) return { name: null, path: null };
  const line = fs.readFileSync(ACTIVE_FILE, "utf-8").trim();
  if (!line) return { name: null, path: null };
  const name = path.basename(line, ".json");
  return { name, path: line };
}

function setActive(name, filePath) {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  if (name && filePath) {
    fs.writeFileSync(ACTIVE_FILE, path.resolve(filePath) + "\n", "utf-8");
  } else if (fs.existsSync(ACTIVE_FILE)) {
    fs.unlinkSync(ACTIVE_FILE);
  }
}

// ── Profile rule operations ──
function removeProfileRules(settings, profile) {
  delete settings.sandbox;

  const profilePerms = profile.permissions || {};
  const profileAllow = new Set(profilePerms.allow || []);
  const profileDeny = new Set(profilePerms.deny || []);

  if (settings.permissions) {
    const perms = settings.permissions;
    if (perms.allow && profileAllow.size)
      perms.allow = perms.allow.filter(r => !profileAllow.has(r));
    if (perms.allow && perms.allow.length === 0) delete perms.allow;

    if (perms.deny && profileDeny.size)
      perms.deny = perms.deny.filter(r => !profileDeny.has(r));
    if (perms.deny && perms.deny.length === 0) delete perms.deny;

    if (profilePerms.defaultMode && perms.defaultMode === profilePerms.defaultMode)
      delete perms.defaultMode;

    if (Object.keys(perms).length === 0) delete settings.permissions;
  }
  return settings;
}

function addProfileRules(settings, profile) {
  if (profile.sandbox) settings.sandbox = profile.sandbox;

  const profilePerms = profile.permissions || {};
  if (Object.keys(profilePerms).length === 0) return settings;

  if (!settings.permissions) settings.permissions = {};
  const perms = settings.permissions;

  if (profilePerms.allow) {
    const existing = new Set(perms.allow || []);
    perms.allow = [...(perms.allow || [])];
    for (const rule of profilePerms.allow)
      if (!existing.has(rule)) perms.allow.push(rule);
  }

  if (profilePerms.deny) {
    const existing = new Set(perms.deny || []);
    perms.deny = [...(perms.deny || [])];
    for (const rule of profilePerms.deny)
      if (!existing.has(rule)) perms.deny.push(rule);
  }

  if (profilePerms.defaultMode)
    perms.defaultMode = profilePerms.defaultMode;

  return settings;
}

// ── Commands ──
function cmdList() {
  const active = getActive();
  const profiles = listProfiles().map(name => ({
    name,
    preset: PRESETS.has(name),
    ...(name === active.name ? { active: true } : {}),
  }));
  const sp = settingsPath();
  const settings = loadJson(sp);
  console.log(JSON.stringify({
    active_profile: active.name,
    active_profile_path: active.path,
    profiles,
    current_sandbox: settings.sandbox || null,
    current_permissions_allow: (settings.permissions || {}).allow || null,
    current_permissions_deny: (settings.permissions || {}).deny || null,
    settings_file: sp,
  }, null, 2));
}

function cmdShow(name) {
  if (!name) {
    const sp = settingsPath();
    const settings = loadJson(sp);
    const active = getActive();
    console.log(JSON.stringify({
      settings_file: sp,
      active_profile: active.name,
      active_profile_path: active.path,
      sandbox: settings.sandbox || null,
      permissions: settings.permissions || null,
    }, null, 2));
  } else {
    const profile = loadProfile(name);
    console.log(JSON.stringify({
      profile: name,
      path: path.resolve(profilePath(name)),
      config: profile,
    }, null, 2));
  }
}

function cmdApply(name) {
  const newProfile = loadProfile(name);
  const newPath = profilePath(name);
  const sp = settingsPath();
  let settings = loadJson(sp);

  // Step 1: Remove old profile rules
  const old = getActive();
  if (old.name) {
    let oldData = null;
    if (old.path && fs.existsSync(old.path)) oldData = loadJson(old.path);
    else {
      const fallback = profilePath(old.name);
      if (fs.existsSync(fallback)) oldData = loadJson(fallback);
    }
    if (oldData) settings = removeProfileRules(settings, oldData);
    else delete settings.sandbox;
  }

  // Step 2: Add new profile rules
  settings = addProfileRules(settings, newProfile);

  // Step 3: Save
  saveJson(sp, settings);
  setActive(name, newPath);

  console.log(JSON.stringify({
    action: "apply",
    profile: name,
    profile_path: path.resolve(newPath),
    settings_file: sp,
    previous_profile: old.name,
    sandbox_enabled: (settings.sandbox || {}).enabled,
    message: `Profile '${name}' applied. Claude Code will reload automatically.`,
  }, null, 2));
}

function cmdReset() {
  const sp = settingsPath();
  let settings = loadJson(sp);

  const old = getActive();
  if (old.name) {
    let oldData = null;
    if (old.path && fs.existsSync(old.path)) oldData = loadJson(old.path);
    else {
      const fallback = profilePath(old.name);
      if (fs.existsSync(fallback)) oldData = loadJson(fallback);
    }
    if (oldData) settings = removeProfileRules(settings, oldData);
    else delete settings.sandbox;
  }

  saveJson(sp, settings);
  setActive(null);

  console.log(JSON.stringify({
    action: "reset",
    settings_file: sp,
    previous_profile: old.name,
    message: "Sandbox configuration removed.",
  }, null, 2));
}

function cmdCreate(name, base) {
  if (PRESETS.has(name)) {
    console.error(`Cannot overwrite preset profile: ${name}`);
    process.exit(1);
  }
  const baseProfile = loadProfile(base || "dev");
  const target = path.join(CUSTOM_PROFILES_DIR, `${name}.json`);
  saveJson(target, baseProfile);

  console.log(JSON.stringify({
    action: "create",
    profile: name,
    base: base || "dev",
    path: target,
    message: `Profile '${name}' created from '${base || "dev"}'. Edit the file to customize.`,
  }, null, 2));
}

function cmdDelete(name) {
  if (PRESETS.has(name)) {
    console.error(`Cannot delete preset profile: ${name}`);
    process.exit(1);
  }
  const target = path.join(CUSTOM_PROFILES_DIR, `${name}.json`);
  if (!fs.existsSync(target)) {
    console.error(`Custom profile not found: ${name}`);
    process.exit(1);
  }
  const active = getActive();
  if (active.name === name) setActive(null);
  fs.unlinkSync(target);

  console.log(JSON.stringify({
    action: "delete",
    profile: name,
    message: `Profile '${name}' deleted.`,
  }, null, 2));
}

// ── Main ──
const args = process.argv.slice(2);
const cmd = args[0];

if (cmd === "sandbox") {
  const sub = args[1];
  if (!sub || sub === "list") cmdList();
  else if (sub === "show") cmdShow(args[2]);
  else if (sub === "apply") { if (!args[2]) { console.error("Usage: sandbox apply <name>"); process.exit(1); } cmdApply(args[2]); }
  else if (sub === "reset") cmdReset();
  else if (sub === "create") { if (!args[2]) { console.error("Usage: sandbox create <name> [base]"); process.exit(1); } cmdCreate(args[2], args[3]); }
  else if (sub === "delete") { if (!args[2]) { console.error("Usage: sandbox delete <name>"); process.exit(1); } cmdDelete(args[2]); }
  else { console.error(`Unknown sandbox command: ${sub}\nAvailable: list, show, apply, reset, create, delete`); process.exit(1); }
} else if (!cmd || cmd === "--help" || cmd === "-h") {
  console.log(`g-claude-feishu-channel — CLI tools for feishu-channel

Usage:
  g-claude-feishu-channel sandbox list              List profiles and current config
  g-claude-feishu-channel sandbox show [name]       Show current config or a profile
  g-claude-feishu-channel sandbox apply <name>      Apply a sandbox profile
  g-claude-feishu-channel sandbox reset             Remove sandbox configuration
  g-claude-feishu-channel sandbox create <n> [base] Create custom profile
  g-claude-feishu-channel sandbox delete <name>     Delete custom profile

Profiles: default, dev, dangerously-open`);
} else {
  console.error(`Unknown command: ${cmd}\nRun with --help for usage.`);
  process.exit(1);
}
