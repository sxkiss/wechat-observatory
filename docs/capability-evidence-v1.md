# Capability Evidence v1

This document explains why each public capability currently has its advertised
status. It is generated from the current implementation review and the latest
read-only database evidence collected on 2026-07-03. It does not contain API
keys, wxids, room ids, chat text, raw XML, media base64, cookies, tokens, or
payment details.

## Evidence Policy

- Runtime truth is `GET /api/v1/capabilities`.
- Sendability evidence must include an outbox terminal state and, when
  applicable, a matching local WeChat message row.
- User-visible stability requires either explicit user confirmation or a narrow
  documented scope.
- Failed samples are not deleted from the ledger. They prove unsupported or
  incomplete payloads return explicit failures instead of silently succeeding.
- Payment, red packet, transfer, and system capabilities are intentionally
  inbound-only or parse-only in v1.

## Current Runtime Surface

| Capability | Send endpoint | Inbound | Outbound | Verification |
| --- | --- | --- | --- | --- |
| `text` | `/api/v1/messages/text` | `stable` | `stable` | `user_confirmed` |
| `image` | `/api/v1/messages/image` | `stable` | `stable` | `user_confirmed` |
| `video` | `/api/v1/messages/video` | `stable` | `stable` | `user_confirmed` |
| `voice` | `/api/v1/messages/voice` | `stable` | `stable` | `user_confirmed` |
| `file` | `/api/v1/messages/file` | `stable` | `stable` | `user_confirmed` |
| `emoji` | `/api/v1/messages/emoji` | `structured` | `stable` | `db_verified` |
| `location` | `/api/v1/messages/location` | `structured` | `stable` | `user_confirmed` |
| `quote` | `/api/v1/messages/quote` | `structured` | `sample_only` | `sample_only` |
| `link` | `/api/v1/messages/link` | `structured` | `stable` | `db_verified` |
| `mini_program` | `/api/v1/messages/mini-program` | `structured` | `source_forward_stable` | `db_verified` |
| `chat_history` | `/api/v1/messages/chat-history` | `basic` | `source_forward_only` | `sample_only` |
| `payment` | none | `parse_only` | `unsupported` | `sample_only` |
| `system` | none | `parse_only` | `non_goal` | `parse_only` |
| `unknown-business` | none | `preserved` | `unsupported` | `sample_only` |

## Outbound Evidence Snapshot

| Kind | Sent / Failed outboxes | Latest sent outbox | Latest message evidence | Status rationale |
| --- | ---: | ---: | --- | --- |
| `text` | `23 / 0` | `56` | outgoing `message.type=1` rows exist; legacy rows may not all carry `chat_record_id` | Stable and user-confirmed; legacy `/api/send/text` compatibility remains. |
| `image` | `6 / 3` | `69` | `chat_record_id=9623`, `message.type=3`, media `image/png` | Stable; latest public contract send produced media metadata and outbound record. |
| `video` | `4 / 3` | `70` | `chat_record_id=9626`, `message.type=43`, media `video/mp4` | Stable after playback regression fix; keep thumbnail/path fallback coverage. |
| `voice` | `4 / 0` | `71` | `chat_record_id=9627`, `message.type=34`, media `audio/amr` | Stable for real AMR/SILK payloads; audible outbound sample was user-confirmed. |
| `file` | `1 / 2` | `61` | `chat_record_id=9576`, outgoing file-transfer row `message.type=1090519089` | Stable for the typed upload path; failed samples document invalid or older payload paths. |
| `emoji` | `4 / 0` | `52` | `chat_record_id=9149`, `message.type=47`, `media_kind=emoji` | Stable for source forwarding and allowlisted local direct-md5 group sample. |
| `location` | `2 / 0` | `60` | `chat_record_id=9527`, `message.type=48` | User-confirmed typed location action. |
| `quote` | `4 / 3` | `38` | `chat_record_id=8097`, `message.type=822083633`, appmsg `57` | Sample-only because incomplete metadata still fails and group quote coverage is thin. |
| `link` | `3 / 0` | `62` | `chat_record_id=9577`, `message.type=49`, appmsg `5` | DB-verified typed builder and source-compatible schema. |
| `mini_program` | `4 / 0` | `72` | `chat_record_id=9628`, `message.type=49`, appmsg `33` | Source forwarding is stable; direct construction still needs real username/page/icon samples. |
| `chat_history` | `6 / 0` | `44` | `chat_record_id=8269`, `message.type=49`, appmsg `19` | Source/original forwarding works; nested record summary is not normalized enough for stable. |

## Inbound Evidence Snapshot

| Kind | Latest structural evidence | Count observed | Status rationale |
| --- | --- | ---: | --- |
| `text` | `message.type=1` | `1506` normalized rows plus older raw rows | Stable. |
| `image` | `message.type=3`, media upload rows | `730` normalized rows plus older raw rows | Stable with media upload. |
| `video` | `message.type=43` | `18` normalized rows plus older raw rows | Stable after receive playback fix. |
| `voice` | latest `message.type=34` sample stored `media_kind=voice`, `media_mime=audio/amr`, `media_size=4948`, and a media URL after the Android voice fallback selected a `voice2` file | `22` normalized rows, `8` with media URLs in the current DB snapshot | Stable for inbound AMR media capture; keep AMR/SILK and duration edge cases in regression. |
| `file` | file-transfer `message.type=1090519089`; appmsg file paths exist | `1` latest normalized file-transfer row plus appmsg file samples | Stable for common file evidence; more file-name edge cases needed. |
| `emoji` | `message.type=47`, emoji XML evidence with MD5, type/len, and normalized CDN URL; selected samples also stored best-effort opaque local media | `198+` normalized rows across structured and legacy shapes | Structured parser; `appmsg` fields are the stable source, while local `media_url` is optional and may be opaque. Outbound direct-md5 remains scope-limited. |
| `location` | `message.type=48` | `5` normalized rows | Structured coordinates and POI fields. |
| `quote` | `message.type=822083633`, appmsg `57` | `12` normalized rows plus older raw rows | Structured parser, but outbound remains sample-only. |
| `link` | `message.type=49`, appmsg `5` | `25` normalized rows | Structured appmsg parser. |
| `mini_program` | `message.type=49`, appmsg `33/36` | `23` normalized rows | Structured appmsg parser. |
| `chat_history` | `message.type=49`, appmsg `19` | `44` normalized rows | Basic nested record parsing; summary normalization incomplete. |
| `payment` | high-bit payment-like types `419430449`, `436207665` observed; payment fixtures cover appmsg `2000/2001` | `5` high-bit rows observed in current DB | Parse-only by design; no outbound automation. |
| `system` | `message.type=10000` | `4` normalized rows plus older raw rows | Parse-only/non-goal unless state sync requires it. |
| `unknown-business` | high-bit/custom types including `42`, `570425393`, `754974769`, `922746929`, `1140850737` | `27` normalized rows | Preserved with raw type evidence until safely classified. |

## Promotion Rules

| From | To | Required evidence |
| --- | --- | --- |
| `implemented` | `stable` | DB proof plus enough playback/render/download samples for both direct and group contexts, or a documented scope limitation. |
| `sample_only` | `db_verified` | Reproducible local WeChat DB row with expected `message.type`, target conversation, and required metadata. |
| `db_verified` | `user_confirmed` | Human confirmation that the recipient sees/plays/opens the expected content. |
| `source_forward_only` | `stable` | Either direct construction is verified or the source-forward-only boundary is explicitly accepted as the stable contract. |
| `preserved` | named kind | Multiple safe samples proving the business meaning without exposing sensitive data. |

## Current Gaps

- `voice`: stable for the verified AMR receive/send path; keep broader AMR/SILK duration and group/private playback samples in regression.
- `emoji`: keep treating local media as best-effort opaque attachment; use structured MD5/CDN fields for adapters.
- `mini_program`: source forwarding is stable; direct field construction still needs known username/page/icon samples.
- `quote`: group quote and incomplete metadata behavior need a tighter compatibility matrix.
- `chat_history`: nested record summaries should be normalized before calling it stable.
- `payment`: keep parse-only and redacted; outbound remains unsupported.
- `unknown-business`: classify only after safe, redacted sample review.
