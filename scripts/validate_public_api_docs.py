#!/usr/bin/env python3
"""Validate the public API documentation surface."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_GO = ROOT / "internal" / "bridge" / "openapi.go"
DOCS_API = ROOT / "docs" / "api.md"
DOCS_MODULE_CONTRACT = ROOT / "docs" / "module-contract.md"
DOCKERFILE = ROOT / "Dockerfile"
REQUIRED_DOCS = [
    "adapter-quickstart-v1.md",
    "public-api-errors-v1.md",
    "public-api-message-samples-v1.md",
    "public-api-python-client-v1.md",
    "protocol-stability-review-v1.md",
]
REQUIRED_PATHS = [
    "/api/v1/capabilities",
    "/api/v1/messages",
    "/api/v1/messages/text",
    "/api/v1/messages/action",
    "/api/v1/outbox/{id}",
    "/api/v1/contacts",
    "/api/v1/modules/status",
    "/api/media/{media_path}",
    "/api/v1/ws",
]
PUBLIC_MESSAGE_KIND_PATHS = [
    "/api/v1/messages/text",
    "/api/v1/messages/image",
    "/api/v1/messages/video",
    "/api/v1/messages/voice",
    "/api/v1/messages/file",
    "/api/v1/messages/emoji",
    "/api/v1/messages/location",
    "/api/v1/messages/quote",
    "/api/v1/messages/link",
    "/api/v1/messages/mini-program",
    "/api/v1/messages/chat-history",
]
REQUIRED_ERROR_CODES = ["owner_wxid_unbound", "media_forbidden", "cursor_conflict"]
PUBLIC_AUTH_SCHEMES = {"BridgeAPIKeyHeader", "BridgeAPIKeyQuery", "BridgePasswordHeader", "BridgePasswordQuery"}
REQUIRED_HTML_TERMS = [
    "外部适配快速路径",
    "Adapter Quickstart",
    "Public API Errors",
    "Public API Message Samples",
    "Public API Python Client",
    "/api/v1",
    "/module/...",
]


def fail(message: str) -> None:
    raise SystemExit(message)


def extract_raw_const(source: str, name: str) -> str:
    pattern = re.compile(r"const\s+" + re.escape(name) + r"\s*=\s*`(.*?)`", re.S)
    match = pattern.search(source)
    if not match:
        fail(f"missing raw const {name}")
    return match.group(1)


def require_path(obj: dict[str, Any], keys: list[str], label: str) -> Any:
    current: Any = obj
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            fail(f"missing {label}: {'.'.join(keys)}")
        current = current[key]
    return current


def validate_openapi() -> dict[str, Any]:
    source = OPENAPI_GO.read_text(encoding="utf-8")
    html = extract_raw_const(source, "openAPIDocsHTML")
    spec = json.loads(extract_raw_const(source, "openAPIJSONDocument"))

    for term in REQUIRED_HTML_TERMS:
        if term not in html:
            fail(f"/docs HTML missing {term}")
    for doc in REQUIRED_DOCS:
        if f"/docs/{doc}" not in html:
            fail(f"/docs HTML missing link for {doc}")
        if f'"{doc}"' not in source:
            fail(f"publicDocFiles missing {doc}")

    paths = require_path(spec, ["paths"], "OpenAPI paths")
    for path in REQUIRED_PATHS:
        if path not in paths:
            fail(f"OpenAPI path missing: {path}")
    validate_public_operation_security(paths)

    media_get = require_path(spec, ["paths", "/api/media/{media_path}", "get"], "media GET")
    security = media_get.get("security") or []
    if not any("BridgeAPIKeyHeader" in item for item in security if isinstance(item, dict)):
        fail("media GET must allow BridgeAPIKeyHeader")
    responses = media_get.get("responses") or {}
    if "403" not in responses:
        fail("media GET must document 403 media_forbidden")

    text_body = require_path(spec, ["paths", "/api/v1/messages/text", "post", "requestBody", "content", "application/json"], "text request body")
    if "example" not in text_body:
        fail("text request body must include example")

    for response_name in ["SendQueuedResponse", "MessageListResponse", "OutboxItemResponse", "ErrorResponse"]:
        content = require_path(spec, ["components", "responses", response_name, "content", "application/json"], response_name)
        if response_name != "ErrorResponse" and "examples" not in content:
            fail(f"{response_name} must include examples")
    spec_text = json.dumps(spec, ensure_ascii=False, sort_keys=True)
    for code in REQUIRED_ERROR_CODES:
        if code not in spec_text:
            fail(f"OpenAPI missing error code example: {code}")
    return {"paths": len(paths), "doc_links": len(REQUIRED_DOCS)}


def validate_public_operation_security(paths: dict[str, Any]) -> None:
    for path, methods in paths.items():
        if not path.startswith("/api/v1/"):
            continue
        if not isinstance(methods, dict):
            fail(f"OpenAPI path {path} must be an object")
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                fail(f"OpenAPI operation {method.upper()} {path} must be an object")
            security = operation.get("security") or []
            schemes = {
                scheme
                for item in security
                if isinstance(item, dict)
                for scheme in item
            }
            missing = sorted(PUBLIC_AUTH_SCHEMES - schemes)
            if missing:
                fail(f"OpenAPI operation {method.upper()} {path} missing public auth scheme(s): {', '.join(missing)}")


def validate_docs_api_links() -> int:
    text = DOCS_API.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", text)
    if not links:
        fail("docs/api.md has no local Markdown links")
    for link in links:
        if link.startswith(("http://", "https://")):
            continue
        path = (DOCS_API.parent / link).resolve()
        if not path.is_file():
            fail(f"docs/api.md broken link: {link}")
    return len(links)


def validate_public_endpoint_docs(openapi_paths: dict[str, Any]) -> None:
    text = DOCS_MODULE_CONTRACT.read_text(encoding="utf-8")
    advertised = set(re.findall(r"`(?:GET|POST|DELETE|PATCH|PUT)\s+([^`]+)`", text))
    for endpoint in advertised:
        if not endpoint.startswith("/api/v1/"):
            continue
        if endpoint == "/api/v1/messages/{kind}":
            missing = [path for path in PUBLIC_MESSAGE_KIND_PATHS if path not in openapi_paths]
            if missing:
                fail(f"module-contract advertises /api/v1/messages/{{kind}} but OpenAPI misses: {', '.join(missing)}")
            continue
        if endpoint not in openapi_paths:
            fail(f"module-contract advertises public endpoint not in OpenAPI: {endpoint}")


def validate_docker_docs_copy() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    for doc in ["api.md", *REQUIRED_DOCS]:
        if f"/usr/share/wechat-observatory/docs/{doc}" not in text:
            fail(f"Dockerfile does not copy public doc: {doc}")


def validate_fixtures() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_public_api_fixtures.py")],
        cwd=str(ROOT),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def main() -> None:
    openapi_summary = validate_openapi()
    spec = json.loads(extract_raw_const(OPENAPI_GO.read_text(encoding="utf-8"), "openAPIJSONDocument"))
    validate_public_endpoint_docs(require_path(spec, ["paths"], "OpenAPI paths"))
    link_count = validate_docs_api_links()
    validate_docker_docs_copy()
    validate_fixtures()
    print(json.dumps({"ok": True, "openapi": openapi_summary, "docs_api_links": link_count}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
