# Message Fixtures v1

These files are sanitized compatibility fixtures for the current
`wechat-observatory` behavior. They intentionally avoid real identifiers,
chat text, raw XML values, API keys, media base64, cookies, and payment
payloads.

Fixtures are used to answer three questions:

- What minimal input should an external caller or module event provide?
- What normalized fields should the gateway/agent emit?
- What evidence is required before the capability can be called verified?

They are not yet a frozen public protocol. Promote fields into a formal
protocol only after multiple real samples match the fixture shape.
## Public API Fixtures

External adapter request/response examples live in `../public-api-v1/`. This directory remains the implementation sample ledger.
