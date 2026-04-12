# IP Diagnosis Skill Design

Date: 2026-04-12
Status: Draft approved in chat, written for repo review
Target repo: `/Users/pangcheng/Workspace/g-claude-code-plugins`
Target location: `skills/ip-diagnosis/`

## Goal

Create a pure instruction-based skill for `macOS + Chrome` that diagnoses network egress and browser-visible IP exposure, then produces a detailed fixed-format operations report.

The skill must not mention any specific downstream service. It should help a user answer:

- What are the current `IPv4` and `IPv6` public egress addresses?
- What country/region, ASN, and organization do those addresses map to?
- Is there a split between `IPv4` and `IPv6` egress or geography?
- Does the browser expose extra addresses through server-side observation or `WebRTC`?
- What concrete remediation steps follow from the observed facts?

## Non-Goals

- No custom diagnostic script in the first version
- No support promise beyond `macOS + Chrome`
- No service-specific allowlist, product logic, or account troubleshooting
- No generic “chatty” diagnosis flow; the default output is a fixed report

## User-Facing Behavior

When triggered, the skill should:

1. Check required dependencies
2. Install missing dependencies before diagnosis, including `playwright-cli`
3. Run local shell checks
4. Query external IP information sources for `IPv4` and `IPv6`
5. Open Chrome and inspect `https://webbrowsertools.com/ip-address/`
6. Produce a fixed-format report
7. Provide remediation steps tied to observed issues
8. Include source links so the user can verify the results directly

## Skill Form

This is a pure `SKILL.md` implementation.

Expected contents:

- `skills/ip-diagnosis/SKILL.md`

The skill prompt, not a custom script, defines the exact workflow, command order, reporting template, and judgment rules.

## Inputs and Triggers

Trigger when the user asks to:

- diagnose network egress
- check `IPv4` / `IPv6`
- inspect IP leakage or browser exposure
- compare command-line results with browser-observed results
- validate VPN or proxy routing consistency
- produce a network diagnosis report

The skill should assume the current machine is the diagnosis target unless the user states otherwise.

## Required Dependencies

The skill must check for:

- `curl`
- `dig`
- `jq`
- `python3`
- `playwright-cli`

If `playwright-cli` is missing, the skill should install it first, then verify that it is runnable before continuing.

The skill should treat dependency installation as part of the default path, not as an optional side task.

## Diagnostic Workflow

### 1. Dependency Check

Check each required command with a shell lookup. If missing:

- install the missing dependency
- verify the install succeeded
- only then continue

### 2. Local Network State

Collect at minimum:

- public `IPv4`
- public `IPv6`
- `DNS` resolvers
- default route
- `utun` presence and state
- local interface `IPv6` observations relevant to `en0`, `en1`, and `utun*`

Purpose:

- determine whether there is an independently usable public `IPv6`
- detect signs that `IPv4` and `IPv6` may be routed differently
- detect signs that a tunnel only partially owns traffic

### 3. External Egress Validation

Use at least two source types to validate `IPv4` and `IPv6`.

For each protocol family, attempt to collect:

- IP address
- country / region
- ASN
- organization

The skill should not treat a single failed source as definitive. If a `-6` query fails, it must keep checking with other sources before concluding that there is no independent public `IPv6`.

### 4. Browser Cross-Validation

Use `playwright-cli` with Chrome to inspect:

- [webbrowsertools IP Address](https://webbrowsertools.com/ip-address/)

The skill should read and report, as available:

- `IP Addresses`
- `From Server Response`
- `Remote Data`
- `Remote IP Services`
- `Via WebRTC`

Expected server-response fields include:

- `HTTP_CLIENT_IP`
- `HTTP_CONNECTING_IP`
- `HTTP_COUNTRY_CODE`
- `HTTP_X_FORWARDED`
- `HTTP_X_CLUSTER_CLIENT_IP`
- `HTTP_FORWARDED_FOR`
- `HTTP_FORWARDED`

Expected remote-service fields may include:

- `ipapi.co`
- `hostip.info`
- `ipify.org [IPv4]`
- `ipify.org [IPv6]`
- `ipecho.net`

Expected `WebRTC` rows may include multiple STUN sources. The skill should copy as many concrete rows as are visible rather than summarizing them away.

### 5. Judgment

The report must distinguish:

- observed facts
- interpretation
- remediation

It must not convert a guess into a confirmed conclusion.

### 6. Remediation

Recommendations must be tied to the observation:

- split `IPv4` / `IPv6` geography
- missing or unusable `IPv6`
- browser-only exposure via `WebRTC`
- server-visible public address that is expected for direct site access
- inconsistent ASN / organization / geography across sources

## Fixed Report Format

The skill must output these sections in order.

### 1. Conclusion

- overall state: `normal` / `risk remains` / `abnormal`
- one-line summary of the main issue

### 2. Local Checks

- public `IPv4`
- public `IPv6`
- `DNS`
- default route
- `utun` status
- local interface `IPv6` observations
- whether an independent public `IPv6` was confirmed

### 3. External Egress

For `IPv4`:

- IP
- country / region
- ASN
- organization
- source 1 result
- source 2 result

For `IPv6`:

- IP
- country / region
- ASN
- organization
- source 1 result
- source 2 result

If a source fails, the report must state whether the failure means:

- fetch failed
- timed out
- blocked
- no independent public `IPv6` was confirmed
- result remains uncertain

### 4. Browser Cross-Validation

Include:

- [webbrowsertools IP Address](https://webbrowsertools.com/ip-address/)
- top-level `IP Addresses` result
- all visible `From Server Response` rows
- all visible `Remote IP Services` rows
- all visible `Via WebRTC` rows

### 5. Consistency Judgment

Explicitly answer:

- Are `IPv4` and `IPv6` geographically consistent?
- Does browser-observed data match command-line egress?
- Is there evidence of browser-only exposure?
- Is there evidence of `WebRTC` private-address leakage?
- Is there evidence of `WebRTC` extra public-address exposure?

### 6. Solutions

Each recommendation must include:

- applicable condition
- action
- why that action addresses the observed issue

If `IPv4` and `IPv6` are geographically inconsistent, the solution set should explicitly include the `macOS` commands for disabling `IPv6` on the active network service and restoring it later.

If browser-side `WebRTC` exposure is present, the solution set may include the user-approved Chrome extension:

- [WebRTC Protect - Protect IP Leak](https://chromewebstore.google.com/detail/webrtc-protect-protect-ip/bkmmlbllpjdpgcgdohbaghfaecnddhni)

The design should treat that extension as a `WebRTC` mitigation only, not a fix for server-visible direct-connect IPs.

### 7. Verification Links

Always include:

- [webbrowsertools IP Address](https://webbrowsertools.com/ip-address/)

Also include the external source URLs or domains used in the report so the user can re-check them manually.

When `WebRTC` exposure is part of the diagnosis, also include the extension link above so the user can choose that mitigation path.

## Judgment Rules

### Server Response vs Browser Leak

If the page shows a public IP under `From Server Response`, that is expected for direct site access and is not, by itself, a browser leak.

### WebRTC Leak

Treat browser exposure as a `WebRTC` leak only when `Via WebRTC` reveals:

- a private address
- an extra public IP not otherwise expected
- an abnormal `IPv6` or geography mismatch

### Geography Split

If `IPv4` and `IPv6` resolve to different countries or materially different regions, report a geography split risk.

### Failed IPv6 Checks

If `IPv6` queries fail while local interfaces still show `IPv6`, report `IPv6 status uncertain` rather than claiming that `IPv6` is absent.

### Source Conflicts

If sources disagree on ASN, organization, or geography, report the disagreement and ask the user to treat the result as needing re-check.

### No Independent Public IPv6

If no independent public `IPv6` is confirmed, report exactly that. Do not rewrite it as “`IPv6` normal”.

## Page-Specific Notes for `webbrowsertools`

This page contains both dynamic results and static explanatory content.

The skill should prefer the dynamic result sections for diagnosis:

- `IP Addresses`
- `From Server Response`
- `Remote IP Services`
- `Via WebRTC`

The static explanation under `How can I get my IP address` is still useful as a rationale reference because it explicitly documents the three detection categories:

- server response
- remote services
- `WebRTC`

## Acceptance Criteria

The first usable version is acceptable if:

1. A triggered run checks and installs missing dependencies before diagnosis
2. The run collects both local and external egress evidence
3. The run opens Chrome with `playwright-cli` and reads `webbrowsertools` result sections
4. The report includes detailed rows from `webbrowsertools`, not just a short summary
5. The report includes links for user self-verification
6. The report never labels normal server-visible public IP observation as a browser leak
7. The report clearly separates fact, judgment, and recommendation

## Open Implementation Decisions

The implementation phase still needs to choose:

- the exact installation command(s) for `playwright-cli`
- the preferred external IP information sources
- keep the implementation as `SKILL.md` only, unless future complexity justifies a separate reference file
- whether to add `agents/openai.yaml` metadata for UI surfacing
