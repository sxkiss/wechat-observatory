# WeChat Protocol Core Review v1

Last reviewed: 2026-07-02.

This project should stay centered on the WeChat phone agent protocol, not on a
large bot platform, a web console product, or an adapter hub. The hard problem
is reliable message capture, message execution, media handling, structure
normalization, and ACK truthfulness on a real WeChat device.

## Product Boundary

| Layer | Role | Priority |
| --- | --- | --- |
| Android LSPosed module | Executes WeChat-native receive/send/media/appmsg work. | Core |
| Go gateway | Normalizes protocol objects, stores media, queues actions, records ACK state. | Core |
| Web admin | Debug console for status, manual sends, and failure inspection. | Support |
| External frameworks | Call this protocol from outside the project. | Out of tree |

The gateway remains the public protocol endpoint because it provides stable
auth, queueing, storage, replay, and offline behavior. The phone module should
not become a public HTTP server.

## Current Core Shape

| Object | Current source | Notes |
| --- | --- | --- |
| `MessageEvent` | `internal/bridge/events.go` | Inbound/outbound envelope with raw type, kind, appmsg fields, media, unsupported, and evidence. |
| `SendActionRequest` | `internal/bridge/events.go` | Typed outbound action contract. |
| `ModuleOutboxItem` | `internal/bridge/outbox.go` | Device-facing execution item and ACK target. |
| appmsg normalizer | `internal/bridge/appmsg.go` | Parses link/file/mini program/chat history/emoji/quote shapes and records structural evidence. |
| Android executor | `android-module/.../HookEntry.java` | Dispatches action kind and ACKs only after local DB verification for implemented send paths. |

## Capability Truth

Use `docs/message-capability-matrix-v1.md` as the promotion source of truth.
Do not promote a kind just because the request validator accepts it. A kind is
stable only when it has request validation, outbox payload, Android execution,
local WeChat DB verification, ACK semantics, and at least one reviewed sample.

Status summary:

| Area | Direction |
| --- | --- |
| Text/image/video/file/location/link/emoji | Keep stable path guarded by tests and DB verification. |
| Voice | Keep implemented but collect more playback and duration evidence. |
| Quote/chat history/mini program | Treat as structured but sample-limited; avoid broad stability claims. |
| Payment/red packet/transfer | Inbound parse-only when recognizable; outbound remains non-goal. |
| Unknown types | Preserve as explicit `unsupported` with `evidence`; never silently drop. |

## Immediate Engineering Rule

Every new WeChat type must answer these before being called supported:

- What raw `message.type` and optional `appmsg.type` identify it?
- What fields are normalized into the protocol object?
- What evidence proves each field?
- What outbound action, if any, is allowed?
- What exact local DB row proves ACK `sent`?
- What data must be redacted or marked `unsupported`?

## Next Core Work

1. Keep tightening inbound normalization for unknown, system, payment, and
   appmsg edge cases.
2. Add fixture-driven tests for each new real sample before expanding outward.
3. Keep external `/api/v1` thin: it should expose the protocol, not create a
   second product surface.
