#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

// ── Paths ──
const crypto = require("crypto");
const STATE_DIR = path.join(os.homedir(), ".claude", "channels", "feishu", "sandbox-profile");
const ACTIVE_DIR = path.join(STATE_DIR, "active");
const CUSTOM_PROFILES_DIR = path.join(STATE_DIR, "profiles");
const PRESET_PROFILES_DIR = path.join(__dirname, "..", "profiles");
const PRESETS = new Set(["default", "dev", "dangerously-open"]);

function projectHash() {
  return crypto.createHash("md5").update(process.cwd()).digest("hex").slice(0, 12);
}

function activeFilePath() {
  return path.join(ACTIVE_DIR, `${projectHash()}.json`);
}

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
  const f = activeFilePath();
  if (!fs.existsSync(f)) return { name: null, path: null };
  const data = loadJson(f);
  return { name: data.profile || null, path: data.profile_path || null };
}

function setActive(name, filePath) {
  const f = activeFilePath();
  fs.mkdirSync(ACTIVE_DIR, { recursive: true });
  if (name && filePath) {
    saveJson(f, {
      project: process.cwd(),
      profile: name,
      profile_path: path.resolve(filePath),
    });
  } else if (fs.existsSync(f)) {
    fs.unlinkSync(f);
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
  console.log(JSON.stringify({
    active_profile: active.name,
    profiles,
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

  // Try to find the profile data for precise rule removal
  const old = getActive();
  let profileData = null;

  // 1. From active record
  if (old.name) {
    if (old.path && fs.existsSync(old.path)) profileData = loadJson(old.path);
    else {
      const fallback = profilePath(old.name);
      if (fs.existsSync(fallback)) profileData = loadJson(fallback);
    }
  }

  // 2. No active or file missing — try matching sandbox config to a preset
  if (!profileData && settings.sandbox) {
    for (const preset of PRESETS) {
      const p = path.join(PRESET_PROFILES_DIR, `${preset}.json`);
      if (!fs.existsSync(p)) continue;
      const data = loadJson(p);
      if (data.sandbox && JSON.stringify(data.sandbox) === JSON.stringify(settings.sandbox)) {
        profileData = data;
        break;
      }
    }
  }

  // Apply removal
  if (profileData) {
    settings = removeProfileRules(settings, profileData);
  } else {
    // Force clean all sandbox-related config
    delete settings.sandbox;
    if (settings.permissions) {
      delete settings.permissions.allow;
      delete settings.permissions.deny;
      delete settings.permissions.defaultMode;
      if (Object.keys(settings.permissions).length === 0) delete settings.permissions;
    }
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

function cmdDelete(name, args = {}) {
  if (PRESETS.has(name)) {
    console.error(`Cannot delete preset profile: ${name}`);
    process.exit(1);
  }
  const target = path.join(CUSTOM_PROFILES_DIR, `${name}.json`);
  if (!fs.existsSync(target)) {
    console.error(`Custom profile not found: ${name}`);
    process.exit(1);
  }
  // Find all projects using this profile
  const affectedProjects = [];
  if (fs.existsSync(ACTIVE_DIR)) {
    for (const f of fs.readdirSync(ACTIVE_DIR)) {
      if (!f.endsWith(".json")) continue;
      const data = loadJson(path.join(ACTIVE_DIR, f));
      if (data.profile === name) {
        affectedProjects.push({ file: f, project: data.project, profilePath: data.profile_path });
      }
    }
  }

  if (affectedProjects.length > 0) {
    console.error(`Profile '${name}' is currently active in ${affectedProjects.length} project(s):`);
    for (const p of affectedProjects) {
      console.error(`  - ${p.project}`);
    }
    console.error(`\nUse --force to reset these projects and delete the profile.`);
    if (!args.force) process.exit(1);

    // Force mode: reset each affected project's settings
    const profileData = loadJson(target);
    for (const p of affectedProjects) {
      const projectSettings = path.join(p.project, ".claude", "settings.local.json");
      if (fs.existsSync(projectSettings)) {
        let settings = loadJson(projectSettings);
        settings = removeProfileRules(settings, profileData);
        saveJson(projectSettings, settings);
      }
      fs.unlinkSync(path.join(ACTIVE_DIR, p.file));
    }
  }

  fs.unlinkSync(target);

  console.log(JSON.stringify({
    action: "delete",
    profile: name,
    affected_projects: affectedProjects.map(p => p.project),
    message: `Profile '${name}' deleted.${affectedProjects.length ? ` Reset ${affectedProjects.length} project(s).` : ""}`,
  }, null, 2));
}

// ── Interactive mode ──

const PROFILE_DESCRIPTIONS = {
  "default": "安全模式（飞书频道日常使用）",
  "dev": "开发模式（完整开发工具）",
  "dangerously-open": "无限制（仅信任环境）",
};

async function interactiveSandbox() {
  const { intro, outro, select, text, isCancel, cancel, note } = require("@clack/prompts");
  const active = getActive();

  intro("🔒 Sandbox Profile Manager");

  note(
    `Profile:  ${active.name || "(none)"}\nSettings: ${settingsPath()}`,
    "Current status"
  );

  const action = await select({
    message: "Select action",
    options: [
      { value: "apply", label: "Apply profile", hint: "switch sandbox mode" },
      { value: "show", label: "Show current config" },
      { value: "show-profile", label: "Show a profile template" },
      { value: "reset", label: "Reset", hint: "remove sandbox config" },
      { value: "create", label: "Create custom profile" },
      { value: "delete", label: "Delete custom profile" },
    ],
  });
  if (isCancel(action)) { cancel("Cancelled."); process.exit(0); }

  if (action === "apply") {
    const profiles = listProfiles();
    const name = await select({
      message: "Select profile to apply",
      options: profiles.map(n => ({
        value: n,
        label: n,
        hint: `${n === active.name ? "(active) " : ""}${PROFILE_DESCRIPTIONS[n] || "custom"}`,
      })),
    });
    if (isCancel(name)) { cancel("Cancelled."); process.exit(0); }
    cmdApply(name);
    outro(`Profile '${name}' applied.`);

  } else if (action === "show") {
    cmdShow();
    outro("Done.");

  } else if (action === "show-profile") {
    const profiles = listProfiles();
    const name = await select({
      message: "Select profile to view",
      options: profiles.map(n => ({
        value: n,
        label: n,
        hint: PROFILE_DESCRIPTIONS[n] || "custom",
      })),
    });
    if (isCancel(name)) { cancel("Cancelled."); process.exit(0); }
    cmdShow(name);
    outro("Done.");

  } else if (action === "reset") {
    cmdReset();
    outro("Sandbox configuration removed.");

  } else if (action === "create") {
    const name = await text({ message: "New profile name" });
    if (isCancel(name) || !name) { cancel("Cancelled."); process.exit(0); }
    const profiles = listProfiles();
    const base = await select({
      message: "Base profile",
      options: profiles.map(n => ({
        value: n,
        label: n,
        hint: PROFILE_DESCRIPTIONS[n] || "custom",
      })),
      initialValue: "dev",
    });
    if (isCancel(base)) { cancel("Cancelled."); process.exit(0); }
    cmdCreate(name, base);
    outro(`Profile '${name}' created from '${base}'.`);

  } else if (action === "delete") {
    const customs = listProfiles().filter(n => !PRESETS.has(n));
    if (customs.length === 0) {
      outro("No custom profiles to delete.");
      return;
    }
    const name = await select({
      message: "Select custom profile to delete",
      options: customs.map(n => ({ value: n, label: n })),
    });
    if (isCancel(name)) { cancel("Cancelled."); process.exit(0); }
    cmdDelete(name, { force: true });
    outro(`Profile '${name}' deleted.`);
  }
}

// ── Main ──
const args = process.argv.slice(2);
const cmd = args[0];

if (cmd === "sandbox") {
  const sub = args[1];
  if (!sub) {
    // No subcommand → interactive mode
    interactiveSandbox().catch(e => { console.error(e); process.exit(1); });
  }
  else if (sub === "--help" || sub === "-h") {
    console.log(`Sandbox profile manager

Usage:
  sandbox                        Interactive mode (arrow keys)
  sandbox list                   List profiles and current config
  sandbox show [name]            Show current config or a profile
  sandbox apply <name>           Apply a sandbox profile
  sandbox reset                  Remove sandbox configuration
  sandbox create <name> [base]   Create custom profile (default base: dev)
  sandbox delete <name>          Delete custom profile

Presets:
  default           安全模式 — 只读命令 + skill 脚本，飞书域名白名单
  dev               开发模式 — 完整开发工具，全域名放开
  dangerously-open  无限制 — 关闭 sandbox + bypassPermissions`);
  }
  else if (sub === "list") cmdList();
  else if (sub === "show") cmdShow(args[2]);
  else if (sub === "apply") { if (!args[2]) { console.error("Usage: sandbox apply <name>"); process.exit(1); } cmdApply(args[2]); }
  else if (sub === "reset") cmdReset();
  else if (sub === "create") { if (!args[2]) { console.error("Usage: sandbox create <name> [base]"); process.exit(1); } cmdCreate(args[2], args[3]); }
  else if (sub === "delete") { if (!args[2]) { console.error("Usage: sandbox delete <name> [--force]"); process.exit(1); } cmdDelete(args[2], { force: args.includes("--force") }); }
  else { console.error(`Unknown sandbox command: ${sub}\nAvailable: list, show, apply, reset, create, delete`); process.exit(1); }
} else if (!cmd || cmd === "--help" || cmd === "-h") {
  console.log(`g-claude-feishu-channel — CLI tools for feishu-channel

Usage:
  g-claude-feishu-channel sandbox              Interactive sandbox profile manager
  g-claude-feishu-channel sandbox list         List profiles and current config
  g-claude-feishu-channel sandbox show [name]  Show current config or a profile
  g-claude-feishu-channel sandbox apply <name> Apply a sandbox profile
  g-claude-feishu-channel sandbox reset        Remove sandbox configuration
  g-claude-feishu-channel sandbox create <n>   Create custom profile (base: dev)
  g-claude-feishu-channel sandbox delete <n>   Delete custom profile

Profiles: default, dev, dangerously-open`);
} else {
  console.error(`Unknown command: ${cmd}\nRun with --help for usage.`);
  process.exit(1);
}
