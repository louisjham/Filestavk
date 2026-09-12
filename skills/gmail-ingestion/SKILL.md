---
name: gmail-ingestion
description: >
  Ingest emails from the attorney's Gmail account using the official Google Gmail API
  (OAuth 2.0, gmail.readonly scope). Emails become Document records, auto-classified.
---

# Gmail Ingestion Skill

## Purpose
Pull emails from the attorney's Gmail that are relevant to client cases.
Each email becomes a Document record with full body + headers.

## Authentication
- Uses Google's official Gmail API -- no scraping, no ToS violations
- OAuth 2.0 with gmail.readonly scope only
- Token stored encrypted in data/gmail_token.json (gitignored)
- Refresh handled automatically by google-auth library

## One-Time Setup
1. Create Google Cloud project at https://console.cloud.google.com
2. Enable Gmail API
3. Create OAuth 2.0 Desktop client credentials
4. Download credentials.json -> place at backend/data/gmail_credentials.json
5. In Filestavk Settings -> Gmail, click Connect Gmail
6. Complete OAuth consent screen
7. Token stored; subsequent runs use refresh token

## Workflow
1. User opens Ingestion -> Gmail tab
2. Enter search query (e.g. from:prosecutor@nuecesco.com 2024-CR-1234)
3. Optionally link results to a case
4. Click Start Ingestion
5. Backend: messages.list(q=query) -> for each message -> messages.get() -> extract body -> save Document
6. Dedup: check metadata_json for existing gmail_id before saving
7. Auto-classify on save using Bayesian classifier
8. UI polls /ingestion/jobs/{id} for progress

## Document Fields Set on Ingest
- doc_type: email
- source: gmail
- content_text: plain text body
- metadata_json: {gmail_id, from, to, subject, date, thread_id}
- classification_label: (auto)

## Gmail Search Query Examples
- from:prosecutor@nuecesco.com
- subject:CR-2024-1234
- after:2024/01/01 label:cases
- is:unread from:court

## Error Handling
- GmailNotAuthenticatedError -> prompt re-auth
- GmailQuotaError -> pause 60s then retry
- GmailParseError -> save with error flag, continue loop

## Deduplication Query
SELECT id FROM documents WHERE source='gmail'
AND json_extract(metadata_json, '$.gmail_id') = ?
