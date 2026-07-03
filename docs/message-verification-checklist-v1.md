# Message Verification Checklist v1

Use this checklist before promoting any message kind in
`message-capability-matrix-v1.md`. The goal is to prove behavior without
leaking private data or confusing one successful sample with a stable
capability.

## Preflight

- Confirm the Android module version under test is installed.
- Confirm the target WeChat user/profile is the intended clone user.
- Confirm the gateway health endpoint is healthy.
- Confirm `go test ./...` passes before and after documentation or code changes.
- Confirm the test target is a private test peer or a group where sending test
  content is acceptable.
- For real sends, create the outbox with the stable target ID: friend `wxid`
  or room id ending with `@chatroom`. Contact search and UTF-8/UTF-8MB4 name
  matching are only for discovering or confirming that ID before the send. Do
  not infer the target from the latest message alone, and do not send by
  display name.

## Inbound Verification

For each inbound sample, record only sanitized evidence:

- `device` is present, but redacted in docs/fixtures.
- `owner_wxid` is present, but redacted.
- `direction=recv`.
- `chat_record_id` is non-zero when available.
- Raw `message_type` is preserved.
- Normalized `kind` or `appmsg_subtype` is populated when known.
- Media samples either have a stored `media_url` or explicitly explain why the
  attachment is unavailable.
- XML samples preserve structural evidence such as tag names and type numbers,
  but not keys, tokens, account identifiers, or full text.
- Unknown types include `unsupported` and `evidence` instead of being silently
  treated as text.

## Outbound Verification

For each outbound action, do not mark it `sent` unless all of these are true:

- The outbox row is created with the expected `kind`.
- The module leases the outbox row.
- The Android executor returns ACK `sent`.
- The local WeChat DB contains a new outgoing row after the action started.
- The outgoing row has the expected `message.type`.
- The outgoing row belongs to the expected target conversation.
- The target conversation has a matching allowlist contact row when the test is
  user-scoped.
- Failed actions produce ACK `failed` with a clear reason.

For user-facing confidence, also confirm:

- The user sees the message in WeChat, when safe to ask.
- Media opens, plays, or downloads correctly.
- The Web admin view does not regress existing inbound media display.

## Required Evidence By Kind

| Kind | Required local DB proof | Additional proof |
| --- | --- | --- |
| `text` | `message.type=1`, `isSend=1`, target talker | Legacy `/api/send/text` compatibility. |
| `image` | `message.type=3`, `isSend=1`, target talker | Media preview opens in Web and WeChat. |
| `voice` | `message.type=34`, `isSend=1`, target talker | Playback and duration metadata. Inbound samples must also prove `media_kind=voice`, non-empty `media_url`, `media_mime` of `audio/amr` or `audio/silk`, and `media_size > 0`. |
| `video` | `message.type IN (43,62)`, `isSend=1`, target talker | Playback works after upload/download. |
| `file` | `message.type=49`, appmsg file subtype, target talker | File name and download/open behavior. |
| `emoji` | `message.type=47`, `isSend=1`, target talker | Source md5 or source record evidence. Inbound samples should preserve MD5/type/len/CDN URL in `appmsg`; local media is best-effort and must be marked opaque when it is an octet-stream WeChat file. |
| `location` | `message.type=48`, `isSend=1`, target talker | Label/POI and coordinates are plausible. |
| `quote` | `message.type=822083633`, target talker | Source record and sender references are correct. |
| `appmsg.link` | `message.type=49`, appmsg type `5` | URL/title/description are preserved. |
| `appmsg.mini_program` | `message.type=49`, appmsg type `33` or `36` | Username/page path/icon samples if direct-built. |
| `chat_history` | `message.type=49`, appmsg type `19` | Nested record summary redacted and parseable. |
| `payment` | inbound only | No outbound action. Redact payment fields. |

## Promotion Gates

| From | To | Gate |
| --- | --- | --- |
| `static` | `db-verified` | At least one real-device local DB proof. |
| `db-verified` | `user-confirmed` | User confirms rendered content or media behavior. |
| `sample-only` | `db-verified` | Required metadata is present, not just ACK success. |
| `parse-only` | outbound-capable | Requires a separate design review, except payment which remains non-goal. |

## Regression Anchors

Use these anchors when checking that a previously fixed behavior still works:

| Anchor | Required evidence |
| --- | --- |
| `voice.inbound.media-fallback` | A fresh inbound `message.type=34` row stores `media_kind=voice`, `media_mime=audio/amr` or `audio/silk`, `media_size > 0`, and `media_url`; Android logs may show an initial hint miss followed by a successful `voice media fallback` / `media retry uploaded` sequence. |
| `voice.outbound.audible` | A confirmed-send voice action uses a real AMR/SILK sample, ACKs `sent`, creates an outgoing `message.type=34` row, and the recipient can play non-empty audio. |
| `emoji.inbound.structured-opaque` | A fresh inbound `message.type=47` row exposes `appmsg.title` as MD5, `appmsg.url` as a normalized CDN URL when present, and optional local `media[]`; octet-stream local emoji media is marked `opaque=true`. |

## Failure Handling

Keep failed samples when they teach the contract:

- Missing media URL or empty download should ACK `failed`.
- Unsupported `kind` should ACK `failed`.
- Missing source record or source record with the wrong type should ACK
  `failed`.
- Payment outbound requests should be rejected before execution.
- Any reflective call without local DB proof must not become `sent`.

Do not delete useful failed rows from the database merely to make the dashboard
look clean. Use them to tighten validation and fixture expectations.

## Redaction Review

Before committing or sharing any fixture or log excerpt, verify it does not
contain:

- real `wxid`, room id, phone number, alias, nickname, device id, or API key;
- real chat text;
- media base64 or raw media bytes;
- full XML from WeChat;
- CDN auth keys, AES keys, cookies, sessions, credentials, or payment tokens;
- transaction ids, payment amounts, or payer/payee identifiers.
