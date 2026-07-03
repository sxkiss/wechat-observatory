# Message Sample Catalog v1

This catalog tracks real-device sample coverage without exposing private
identifiers, chat text, raw payment data, API keys, cookies, media base64, or
full XML payloads. It is a working ledger for implementation quality, not a
stable public protocol.

## Redaction Rules

- Replace every `wxid`, room id, device id, API key, token, cookie, and account
  identifier with a role label such as `<owner>`, `<peer>`, `<room>`, or
  `<device>`.
- Do not store chat text unless it is synthetic and explicitly marked as such.
- Do not store raw media bytes, base64, CDN auth keys, AES keys, or payment
  payloads.
- XML samples may keep tag names, appmsg type numbers, and non-sensitive
  structural fields; values must be shortened or replaced with placeholders.
- Every sample must state its evidence source: local WeChat DB row, outbox ACK,
  gateway event, or user confirmation.

## Verification Levels

| Level | Meaning |
| --- | --- |
| `static` | Build/test coverage only. |
| `db-verified` | Real device produced the expected local WeChat DB row. |
| `user-confirmed` | User confirmed the message rendered/played correctly. |
| `sample-only` | One or more samples work, but coverage is not broad. |
| `parse-only` | Inbound recognition only; outbound is unsupported by design. |

## Current Sample Ledger

| Sample ID | Kind | Direction | Evidence | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `text.private.basic` | `text` | outbound | outbox ACK + local DB | `user-confirmed` | Legacy `/api/send/text` remains compatible. |
| `image.private.basic` | `image` | inbound/outbound | media upload + local DB | `user-confirmed` | Covers common image file path and Web preview. |
| `video.private.basic` | `video` | inbound/outbound | media upload + local DB | `user-confirmed` | Receive playback regression fixed; send verified. |
| `file.private.basic` | `file` | inbound/outbound | appmsg file + local DB | `user-confirmed` | File name and download path need more edge samples. |
| `voice.private.amr` | `voice` | inbound/outbound | media upload + local DB + user confirmation | `user-confirmed` | Outbound audible AMR/SILK sample was confirmed; latest inbound AMR sample stored media URL and size after `voice2` fallback. Keep duration and SILK variants in regression. |
| `location.private.basic` | `location` | inbound/outbound | outbox ACK + local DB + parser fixture | `user-confirmed` | Inbound XML now maps coordinates, scale, label, POI name, info URL, POI id, and POI tips. |
| `emoji.private.source-forward` | `emoji` | outbound | outbox `49` + local DB msg `8474` | `db-verified` | Source-message forwarding works for private chat; direct-md5 still needs samples. |
| `emoji.group.source-forward` | `emoji` | outbound | outbox `50` + local DB msg `9091` | `db-verified` | Source-message forwarding works for group chat. |
| `emoji.group.direct-md5` | `emoji` | outbound | outbox `52` + local DB msg `9149` | `db-verified` | Direct MD5 send works for a locally available emoji in a name-allowlisted group chat. |
| `link.private.basic` | `appmsg.link` | outbound | outbox ACK + local DB | `db-verified` | Typed builder works for title/description/url/app name. |
| `mini_program.private.source-forward` | `appmsg.mini_program` | outbound | source forwarding + local DB | `db-verified` | Direct field builder needs real username/page/icon samples. |
| `quote.private.basic` | `quote` | outbound | outbox ACK + local DB | `sample-only` | Some failures remain when quote metadata is incomplete. |
| `chat_history.private.source-forward` | `chat_history` | outbound | source forwarding + local DB | `sample-only` | Nested item summary is not normalized yet. |
| `system.basic` | `system` | inbound | stored event | `parse-only` | Keep non-actionable unless needed for state sync. |
| `payment.red_packet` | `payment` | inbound | real `message_type=436207665` sample + appmsg type `2001` fixture | `sample-only` | Parse-only; title, description, URL, app name, raw XML, amount, and participant metadata are redacted. |
| `payment.transfer` | `payment` | inbound | real `message_type=419430449` sample + appmsg type `2000` fixture | `sample-only` | Parse-only; title, description, URL, app name, raw XML, amount, and participant metadata are redacted. |
| `unknown.high-bit` | `unknown-business` | inbound | stored numeric message types | `sample-only` | Classify only after safe, redacted inspection. |

## Minimal Sanitized Fixture Shape

Use this shape when turning a ledger entry into a fixture. Keep fixtures small
and deterministic.

```json
{
  "sample_id": "emoji.private.source-forward",
  "kind": "emoji",
  "direction": "outbound",
  "wechat_type": 47,
  "verification": "db-verified",
  "input": {
    "action_kind": "emoji",
    "source_chat_record_id": "<source-local-id>"
  },
  "expected": {
    "ack_status": "sent",
    "message_kind": "emoji",
    "message_type": 47,
    "media_kind": "emoji",
    "evidence": [
      "outbox.kind=emoji",
      "wechat.local_db.message.type=47"
    ]
  },
  "redactions": [
    "owner_wxid",
    "target_wxid",
    "emoji_md5",
    "raw_xml"
  ]
}
```

Implementation-level fixture files live under `docs/message-fixtures/v1/`.
Public API fixtures live under `docs/message-fixtures/public-api-v1/`. Each
fixture is a sanitized contract example, not a production transcript.

## Promotion Rules

- A sample can move from `sample-only` to `db-verified` only when an outgoing or
  incoming local WeChat DB row proves the expected `message.type` and target
  conversation.
- A sample can move to `user-confirmed` only after the user confirms the content
  rendered, played, or downloaded correctly in WeChat.
- A message kind is not stable until direct chat and group chat behavior are
  either both verified or the limitation is explicitly documented.
- Payment-related samples never become outbound-capable in v1.
