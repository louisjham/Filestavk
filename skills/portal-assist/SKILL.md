---
name: portal-assist
description: >
  Manual-assist browser automation skill for looking up client and case records on the
  Nueces County Tyler Technologies Odyssey portal (Smart Search) with human-in-the-loop CAPTCHA bypass.
  STRICT: one action at a time, human confirmation required, no loops, no unattended runs.
---

# Portal Assist Skill

## Purpose
Assist the attorney in looking up a client's court record on the Nueces County Odyssey Public Portal
(`https://portal-txnueces.tylertech.cloud/Portal/Home/Dashboard/29`) by driving a locally-running headed browser session.
The attorney remains in full control at all times. This skill does NOT scrape, does NOT bulk-collect, and does NOT run unattended.

## Legal and Ethical Constraints

- Tyler Technologies ToS prohibit bulk automated access. This skill is scoped to
  single, on-demand lookups that mirror normal human browsing behaviour.
- No auto-retry. If a lookup fails, the skill stops and reports the error.
- No loops. The skill processes exactly one case number or client name per invocation.
- Full audit log written to `portal_audit_log` in the DB.
- Human-in-the-loop: user solves the visual CAPTCHA challenge at `Dashboard/29`.

## Supported Search Modes
- **Case Number** (e.g. `2024-CR-0001`, `CR-2023-001`) — primary
- **Party Name** (formatted as `Last, First Middle`, e.g. `Smith, John`)

## Workflow
1. User opens Portal Assist page in Filestavk UI (`/ingestion/portal`)
2. User selects or types a Case Number or Party Name
3. User clicks "Start Portal Lookup"
4. Backend `portal_service` launches headed Chromium to `https://portal-txnueces.tylertech.cloud/Portal/Home/Dashboard/29`
5. Human solves the visual CAPTCHA puzzle in the browser window and clicks Next
6. Backend detects the active Smart Search input field:
   a. Fills search term (Case Number or `Last, First Middle`)
   b. Checks the "are you human" / verification box
   c. Clicks Submit
7. Backend waits for results / case detail page to load
8. Backend captures full page HTML and text into indestructible `documents` table (`doc_type='court_record_lookup'`, `source='nueces_odyssey_portal'`)
9. Backend parses structured case metadata, charges, and register of actions (hearings/filings) into `cases` and `events` tables
10. Browser closes immediately and audit log is recorded
11. UI displays success summary with links to view the case and document

## Error Handling
- `TimeoutError` — user took longer than 3 minutes to solve CAPTCHA or page failed to load
- `JobCancelled` — user clicked Cancel Lookup in UI
- All errors are recorded in `portal_audit_log.error_message`
