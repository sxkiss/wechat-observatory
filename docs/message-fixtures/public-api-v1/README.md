# Public API Message Fixtures v1

These JSON files are sanitized examples for external adapters using `/api/v1`.
They describe the stable request/response/envelope shape, not real production
traffic. Values in angle brackets are placeholders and must not be copied as
real credentials or identifiers.

## Files

- `index.json` lists every fixture.
- `*.json` files each contain one message kind or subtype.

## Rules

- Do not use display names as send targets; use wxid or room id from contacts.
- Treat send responses as queued, then poll `status_url` until `sent` or
  `failed`.
- Media examples use `/api/media/...`; API Key access is device-scoped.
- Payment and system fixtures are parse-only and have no outbound request.
