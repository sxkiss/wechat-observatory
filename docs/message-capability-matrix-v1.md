# Message Capability Matrix v1

This document is the implementation baseline for closing WeChat message
inbound and outbound support. It intentionally separates observed inbound
parsing, outbound action execution, and verification so each message type can
advance without weakening the safety contract.

## Principles

- Every outbound action must be acknowledged only after a local WeChat message
  record is observed, not merely because a reflective call returned.
- Every inbound media or XML payload must preserve enough raw evidence to be
  re-parsed later without exposing credentials or account identifiers in logs.
- Unsupported fields are explicit. They must be returned as `unsupported` or
  left unmapped with evidence instead of being silently dropped.
- The first stable protocol shape is `MessageEnvelope v1`; current database
  fields remain compatible while richer structures are staged in JSON payloads.
- External adapters should discover the stable surface through `GET /api/v1/capabilities` before assuming a message kind is sendable.
- `GET /api/v1/messages` and `GET /api/v1/ws` return `PublicMessageEnvelope` objects; admin-only endpoints may still expose storage views for troubleshooting.
- v1 send endpoints return `PublicSendResponse`; `GET /api/v1/outbox/{id}` returns `PublicOutboxEnvelope` without `payload_json` or module-only execution fields.
- For reliable adapter sync, use `GET /api/v1/messages?after_id=<last_seen_id>` to backfill missed messages before connecting `GET /api/v1/ws`; use `before_id` only for older history pagination.

## Verification Levels

| Level | Meaning |
| --- | --- |
| `static` | Code builds and unit tests cover request/queue/ACK semantics, but no device proof yet. |
| `db-verified` | A real device produced the expected local WeChat `message` row after the action. |
| `user-confirmed` | The user also confirmed the received content in WeChat. |
| `sample-only` | One or more real samples work, but the shape is not broad enough to call stable. |
| `parse-only` | Inbound recognition/parsing is allowed; outbound is intentionally unsupported. |

## Envelope

| Field | Purpose |
| --- | --- |
| `kind` | Stable capability kind: `text`, `image`, `voice`, `video`, `file`, `emoji`, `location`, `appmsg`, `chat_history`, `payment`, `system`. |
| `wechat_type` | Raw WeChat `message.type`. |
| `appmsg_type` | Parsed appmsg subtype for `wechat_type=49`. |
| `text` | Display text or caption. |
| `xml` | Raw XML for appmsg/system payloads, redacted before external display. |
| `media[]` | Zero or more media assets, including thumbnail/original variants. `media[].opaque=true` means the file is a WeChat-local opaque attachment and may not be directly previewable. |
| `refs` | Quoted, forwarded, room sender, or source-message references. |
| `unsupported[]` | Known fields or behaviors that are not yet mapped. |
| `evidence` | Source table, column, file path, or reflected class/method used to derive the field. |

## Capability Matrix

| Kind | WeChat type | Inbound status | Outbound status | Verification | Next work |
| --- | ---: | --- | --- | --- | --- |
| `text` | `1` | Stable | Stable | `user-confirmed`; legacy `/api/send/text` remains compatible. | Keep compatibility tests. |
| `image` | `3` | Stable with media upload | Stable | `user-confirmed`; ACK requires observed outgoing `message.type=3`. | Keep ACK/poll dedup between placeholder and observed event. |
| `voice` | `34` | Stable AMR/SILK resolver with `voice2` fallback | Stable for real AMR/SILK payloads | `user-confirmed` for audible outbound audio; latest inbound AMR sample stored media URL and size after fallback. | Keep broader AMR/SILK samples, duration metadata, and group/private playback in regression. |
| `video` | `43`, `62` | Stable with media upload | Stable | `user-confirmed`; receive playback regression fixed; send ACK requires outgoing `message.type IN (43,62)`. | Keep thumbnail/path fallback coverage. |
| `file` | `49` / `1090519089` | Stable for common file appmsg and observed outgoing file-transfer rows | Stable for arbitrary file upload | `user-confirmed`; outbound file send may create WeChat `message.type=1090519089`, while inbound appmsg files remain `49` / appmsg `6`. | Broaden file subtype samples and file-name edge cases. |
| `emoji` | `47` | Structured parser for emoji XML; CDN URL and MD5 are the stable source, local `media_url` is best-effort and may be opaque | Stable for private/group local-source forwarding and allowlisted group direct `emoji_md5` | `db-verified`; private outbox `49`, group outbox `50`, and allowlisted direct-md5 group outbox `52` produced outgoing `message.type=47`, `media_kind=emoji`. Fresh inbound samples produced normalized `appmsg.url` plus opaque local media for some records. | Add private direct-md5 sample and broaden emoji package/source variants. |
| `location` | `48` | Structured XML parser for latitude/longitude/label/POI fields | Stable typed action | `user-confirmed`; ACK requires outgoing `message.type=48`. | Verify more real inbound location variants and map any edge XML attributes. |
| `quote` | `822083633` plus text fallback | Structured quote parser | Works for prepared quote metadata; sample-limited | `sample-only`; direct quote sends succeeded, failures also exist for incomplete metadata. | Group quote matrix and stricter source-record validation. |
| `appmsg.link` | `49` / appmsg `5` | Structured parser | Stable typed builder | `db-verified`; outbox sample ACKed `sent`, subtype `link`. | Add admin/debug form only if needed; otherwise leave API-first. |
| `appmsg.mini_program` | `49` / appmsg `33/36` | Structured parser | Source forwarding works; direct builder sample-limited | `db-verified` for source forwarding and public API contract check. | Validate direct construction with known username/page path/icon samples. |
| `chat_history` | `49` / appmsg `19` | Basic parser | Source/original forwarding only | `sample-only`; forwarded records ACK as `sent`, but nested item summary is not normalized. | Persist nested record summary; keep outbound limited to forwarding existing records. |
| `system` | `10000` and variants | Filtered/limited | Non-goal | `parse-only`. | Keep excluded unless needed for state sync. |
| `payment` | `419430449`, `436207665`; `49` / appmsg `2000/2001` | Parse-only classifier for transfer/red packet with sensitive fields redacted | Non-goal | `sample-only`; real inbound high-bit payment types observed and code covered by static fixtures. | Keep validating safe samples; keep outbound payment automation unsupported. |
| `unknown-business` | high-bit/custom types | Stored with raw evidence when available | Unsupported | `sample-only`; observed types include several unclassified numeric values. | Classify from real samples before adding protocol names. |

## Outbound Action Plan

| Phase | Scope | Notes |
| --- | --- | --- |
| 1 | `text`, `image` | Complete. Image uses WeChat SendMsgMgr image path and DB verification. |
| 2 | Dedup and event normalization | Merge ACK placeholders with later observed message events by local chat record id. |
| 3 | `video` | Complete for observed device path; keep DB verification and thumbnail fallback. |
| 4 | `file` | Complete for typed appmsg file action, not arbitrary XML. |
| 5 | `voice` | Stable for real AMR/SILK via VoiceMsgSendTask; inbound AMR media capture verified with `voice2` fallback. Keep duration and variant samples in regression. |
| 6 | `appmsg.link` and selected XML | Link typed builder verified on device; mini program source forwarding verified. Direct mini program construction still needs real samples. |
| 7 | `chat_history` | Inbound parser and forwarding existing records only. |
| 8 | `location` | Typed action uses WeChat LocationMsgSendTask and DB verification; real-device send verified. |
| 9 | `emoji` | Structured inbound XML and typed outbound action are implemented; private/group source forwarding and group direct-md5 sending verified with outgoing `message.type=47`. |

## Current Evidence Snapshot

Last reviewed: 2026-07-03. Detailed per-capability evidence lives in
[Capability Evidence v1](capability-evidence-v1.md).

- Remote `go test ./...` passes.
- Gateway container `docker-gateway-1` is healthy on port `8088`.
- Real device outbox contains `sent` samples for `text`, `image`, `video`,
  `voice`, `file`, `location`, `emoji`, `link`, `mini_program`,
  `chat_history`, and `quote`.
- Public API contract check sent `image`, `video`, `voice`, and
  `mini_program` to an allowlisted test room using stable room id targeting;
  all four reached `sent` and produced outbound message records.
- Inbound voice media is verified after the Android fallback fix: a fresh
  `message.type=34` sample stored `media_kind=voice`, `media_mime=audio/amr`,
  non-zero `media_size`, and a media URL after `voice2` fallback selection.
- The Android async upload fix removed the observed post-send
  `NetworkOnMainThreadException`, `handle insert failed`, and
  `async upload failed` log errors in the latest run.
- Emoji source forwarding is verified in both private chat and group chat:
  private outbox `49` produced `chat_record_id=8474`; group outbox `50`
  produced `chat_record_id=9091`.
- Emoji direct-md5 group send is verified against a name-allowlisted target:
  outbox `52` produced `chat_record_id=9149` with `message.type=47`.
- Emoji inbound XML now exposes `appmsg.title` as MD5, `appmsg.url` as a
  normalized CDN URL, and optional best-effort `media[]`; local WeChat emoji
  files may be opaque and are marked with `media[].opaque=true`.
- Existing failed samples remain useful and should not be deleted; they show
  where missing metadata or unsupported payload shapes must produce explicit
  `failed` ACKs.

## Non-goals For v1

- No arbitrary raw XML outbound endpoint.
- No automatic mass sending or broadcast workflows.
- No token, cookie, wxid, media base64, or chat text in logs.
- No schema-breaking migration without separate approval.
