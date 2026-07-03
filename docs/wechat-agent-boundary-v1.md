# WeChat Agent Boundary v1

This document describes the project boundary before a stable external protocol
is finalized. The goal is to keep `wechat-observatory` focused on WeChat
message observation and action execution, while allowing other systems to adapt
to it without adding framework-specific code here.

## Product Boundary

`wechat-observatory` owns:

- Observing inbound WeChat messages from the Android client.
- Normalizing message type, direction, conversation, sender, media, appmsg, and
  evidence fields.
- Accepting outbound actions for supported message kinds.
- Executing those actions inside WeChat through the Android module.
- Returning `sent` only after local WeChat evidence is observed.
- Returning explicit `failed` ACKs for unsupported, incomplete, or unverifiable
  actions.
- Preserving raw evidence safely enough for later parser improvements.

`wechat-observatory` does not own:

- AllBot-specific adapters.
- Adapters for other bot frameworks.
- Business workflow orchestration.
- Plugin marketplaces or third-party plugin lifecycles.
- Payment automation for red packets or transfers.
- Mass sending or broadcast tooling.

## Deployment Boundary

The Android LSPosed module is the core WeChat Agent. The current Go gateway is a
reference transport, persistence layer, and Web debugging/admin surface.

```text
WeChat client
  <-> Android module / WeChat Agent
  <-> current HTTP outbox + webhook contract
  <-> Go gateway reference implementation
  <-> Web admin / storage / debug tooling
```

External systems should not need code changes inside this repository. They can
either:

- implement the same module-facing HTTP contract, or
- consume the Go gateway's public/admin APIs, depending on their trust boundary.

The project should avoid adding first-party adapters for every framework. A
framework adapter belongs in that framework's repository or a separate package.

## Current Contract Surfaces

These surfaces are implementation contracts today. They are not yet frozen as a
versioned public protocol.

| Surface | Direction | Purpose |
| --- | --- | --- |
| `POST /module/register` | Agent -> server | Report device, owner wxid, runtime readiness, and API key identity. |
| `POST /webhook/module/message` | Agent -> server | Push observed inbound/outbound message events. |
| `POST /module/outbox/poll` | Agent <- server | Pull pending outbound actions. |
| `GET /module/outbox/ws` | Agent <- server | Optional lower-latency outbox transport. |
| `POST /module/outbox/ack` | Agent -> server | Report action result as `sent` or `failed`. |
| `POST /api/send/text` | external/admin -> gateway | Legacy text send API. |
| `POST /api/send/action` | external/admin -> gateway | Typed action API for media/appmsg/location/emoji variants. |

## Stable Semantics Before Stable Schema

The next stabilization target is semantics, not field cosmetics.

Stable now:

- `sent` means local WeChat evidence was observed.
- `failed` means the module could not execute or verify the action.
- Unknown action kinds must fail explicitly.
- Media outbound actions must use stored media URLs or bounded uploads.
- Sensitive values must not appear in logs, docs, samples, or fixtures.

Not stable yet:

- Exact public names for every envelope field.
- Complete AppMsg subtype taxonomy.
- Complete handling of high-bit and business message types.
- Direct construction of every XML/appmsg variant.
- Web UI coverage for every action kind.

## Capability Ownership

| Area | Owner in this repo | Adapter responsibility |
| --- | --- | --- |
| WeChat raw type detection | Android module + Go normalization | Treat raw type as evidence, not business API. |
| Message kind naming | This repo | Map kind names into framework-specific events. |
| Media storage URL | Go gateway reference implementation | Re-host or fetch media according to adapter trust boundary. |
| Outbound action validation | Go gateway + Android module | Build valid actions and surface failed ACKs to users. |
| Framework event model | Out of scope | Implement in AllBot or other framework adapters. |
| Payment handling | Parse-only in this repo | Do not request outbound payment actions. |

## Recommended Near-Term Order

1. Keep updating `docs/message-capability-matrix-v1.md` after every real-device
   test.
2. Add sanitized entries to `docs/message-sample-catalog-v1.md` before adding
   new message kinds.
3. Promote only heavily tested fields into a future `MessageEnvelope v1`.
4. Split Android executor code by capability once the current behavior is
   captured by samples.
5. Publish an external contract only after sample fixtures can prove
   compatibility.

This order keeps the project lightweight: the core remains WeChat message
handling, while external systems adapt to the documented behavior.
