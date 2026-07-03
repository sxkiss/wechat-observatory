# Protocol Capability Review - 2026-07-03

This review is based on the remote source of truth at
`/root/wechat-observatory`, the live gateway at `127.0.0.1:8088`, and the
current MySQL data in `app_wechat_observatory`. It is a protocol readiness
review only: no messages were sent, no database rows were changed, and no
destructive operations were run.

Update after P0 closure: the public capabilities contract now describes the
real nested `MessageEnvelope v1` fields such as `media[]`, `media[].opaque`,
`appmsg`, and `location`, and voice/emoji/chat-history status wording has been
aligned with the current evidence. The remaining gaps below are kept as
historical review context and follow-up planning.

## Executive Summary

The project is now past the "can only send text" stage. The core WeChat bridge
can receive and send the major message families needed by an external adapter:
text, image, video, voice, file, emoji, location, quote, link, mini program,
and chat history forwarding.

The next bottleneck is not another message type. The next bottleneck is
protocol consistency:

- `/api/v1/messages` already returns a nested `PublicMessageEnvelope` with
  `kind`, `subtype`, `media[]`, `appmsg`, `location`, `unsupported`, and
  `evidence`.
- `GET /api/v1/capabilities` still describes some old flat field names such as
  `appmsg_subtype`, `media_url`, `media_kind`, and `location_latitude`.
- The docs matrix is stronger than the live capability endpoint in a few
  places, especially voice verification.
- Unknown and generic appmsg samples are preserved, but `appmsg_xml_missing`
  remains the largest unresolved parser signal.

The safest next step is to tighten the public protocol surface before adding
more runtime behavior.

## Evidence Sources

- `git status --short` shows the remote worktree is dirty. This review did not
  revert, format, or overwrite unrelated files.
- `GET /api/v1/capabilities` returned protocol `wechat-observatory` version
  `v1`.
- `GET /api/v1/messages` was paged read-only through the local gateway and
  returned 5,649 public message envelopes.
- `bridge_message_events` was read with aggregate SQL only.
- `bridge_module_outbox` was read with aggregate SQL only.

## Inbound Coverage

| Kind | Public API count | Current state | Notes |
| --- | ---: | --- | --- |
| `text` | 3,275 | Stable | Large sample base. Historical rows have no evidence, which is expected. |
| `image` | 1,519 | Stable | Recent rows include `image/jpeg` and media size. Older rows can miss MIME. |
| `emoji` | 443 | Structured | Recent rows expose MD5/CDN evidence; opaque local files are marked `media[].opaque=true`. |
| `appmsg/link` | 35 | Structured | Title, URL, app name, and thumbnail media are exposed when present. |
| `appmsg/mini_program` | 31 | Structured | Source forwarding is verified; direct construction still needs more real samples. |
| `chat_history` | 65 | Basic structured | Top-level card is parsed; nested item summary is not normalized enough yet. |
| `video` | 30 | Stable | Receive playback issue was fixed; current media extraction is usable. |
| `voice` | 21 | Usable | Latest real sample stored `audio/amr` with non-zero size. Duration/variant metadata still needs hardening. |
| `appmsg/quote` | 17 | Structured, sample-limited | Private quote works; group quote matrix still needs broader proof. |
| `file` | 12 | Stable for common file rows | File transfer rows and appmsg file rows are both represented. |
| `location` | 8 | Structured for parsed XML | Some older rows only have media-style fallback; recent structured rows are correct. |
| `payment/*` | 5 | Parse-only | Red packet and transfer are recognized safely. Outbound remains unsupported. |
| `system` | 7 | Parse-only | Kept out of v1 send scope. |
| `unknown` | 31 | Preserved | Raw `message_type`, `unsupported`, and `evidence` are preserved for later classification. |

## Outbound Coverage

`bridge_module_outbox` contains successful real-device samples for the main v1
actions:

| Kind | Sent samples | Failed samples | Current state |
| --- | ---: | ---: | --- |
| `text` | 24 | 0 | Stable. |
| `image` | 8 | 3 | Stable now; failures are older WeChat 8.0.74 verification guards. |
| `video` | 5 | 3 | Stable now; failures are older verification/no-record attempts. |
| `voice` | 7 | 0 | Implemented and usable; needs more regression samples. |
| `file` | 5 | 2 | Stable now; older failures are no outgoing file record observed. |
| `emoji` | 4 | 0 | Stable for tested source/direct MD5 paths. |
| `location` | 3 | 0 | Stable typed action. |
| `quote` | 4 | 3 | Works with complete metadata; validation/error semantics need tightening. |
| `link` | 4 | 0 | Stable typed builder/source path. |
| `mini_program` | 4 | 0 | Source forwarding stable; direct builder remains sample-limited. |
| `chat_history` | 6 | 0 | Source/original forwarding only. |

Existing failed rows should stay in place because they are useful regression
evidence for explicit `failed` ACK behavior.

## Protocol Gaps

### P0 - Public envelope contract mismatch

`GET /api/v1/messages` returns nested fields:

- `subtype`
- `media[]`
- `appmsg`
- `location`

`GET /api/v1/capabilities` still documents older flat names:

- `appmsg_subtype`
- `media_url`
- `media_kind`
- `appmsg_title`
- `location_latitude`
- `location_longitude`

This is the main issue to fix before telling external adapters to rely on the
protocol. The endpoint behavior is better than the contract description, so the
fix should update the contract/docs/tests, not reshape the runtime envelope.

### P0 - Capability status drift

The docs matrix and the live capabilities endpoint disagree in a few places:

- Voice is described as stable/user-confirmed in the docs matrix, but the live
  capability endpoint reports `inbound_status=basic`,
  `outbound_status=implemented`, `verification=db_verified`.
- Emoji docs include the new opaque media semantics; the live capability entry
  should mention `media[].opaque` and CDN/MD5 as the stable source.
- Chat history is correctly marked limited, but the capability entry should
  clearly say outbound is forwarding-only and nested item normalization is not
  complete.

### P1 - `appmsg_xml_missing` remains the largest unresolved unsupported signal

The public API saw `appmsg_xml_missing` as the top unsupported item. These rows
are preserved instead of guessed, which is good, but the parser needs one more
investigation pass:

- confirm whether raw XML is genuinely absent from the WeChat DB row;
- confirm whether Android can read another column or related table for those
  appmsg rows;
- classify which appmsg variants are affected.

### P1 - Quote and mini program need stricter send modes

Quote and mini program sending are useful, but they should be separated into
clear modes:

- `source_chat_record_id` forwarding mode: stable where verified.
- direct builder mode: only stable for the exact fields verified by samples.
- incomplete metadata: reject before queueing when possible; otherwise ACK
  `failed` with a precise reason.

### P1 - Media metadata needs final normalization

Recent media rows are good, but historical and edge rows can have missing MIME
or ambiguous local files. The protocol should keep this simple:

- expose `media[].kind`, `mime`, `name`, `url`, `size`, `opaque`;
- never promise browser preview from MIME alone;
- for emoji, prefer `appmsg.title`/MD5 and `appmsg.url` over local opaque files.

## Recommended Next Work

1. Update `GET /api/v1/capabilities` so the envelope contract matches the real
   `PublicMessageEnvelope`.
2. Add/adjust tests that assert capabilities mention `media[]`, `appmsg`,
   `location`, and `media[].opaque`.
3. Align `docs/message-capability-matrix-v1.md`,
   `docs/adapter-quickstart-v1.md`, and OpenAPI wording with the live envelope.
4. Add a small sanitized sample catalog generated from real public envelopes:
   text, image, video, voice, file, link, mini program, quote, location, emoji,
   chat history, payment parse-only, unknown preserved.
5. Investigate `appmsg_xml_missing` with read-only DB/log inspection before
   adding any new parser behavior.

## Stop Line

Do not start AllBot integration yet. The project should first publish a stable
and internally consistent WeChat protocol surface. Once the v1 envelope,
capabilities, samples, and failure semantics are aligned, external frameworks
can adapt to this project without adding another gateway layer.
