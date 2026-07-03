#!/usr/bin/env python3
"""Unit tests for public API documentation validation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import validate_public_api_docs as docs


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def public_security() -> list[dict[str, list[Any]]]:
    return [
        {"BridgeAPIKeyHeader": []},
        {"BridgeAPIKeyQuery": []},
        {"BridgePasswordHeader": []},
        {"BridgePasswordQuery": []},
    ]


def minimal_spec(paths: dict[str, Any] | None = None) -> dict[str, Any]:
    openapi_paths = {
        "/api/v1/capabilities": {"get": {"security": public_security()}},
        "/api/v1/messages": {"get": {"security": public_security()}},
        "/api/v1/messages/text": {
            "post": {
                "security": public_security(),
                "requestBody": {
                    "content": {
                        "application/json": {
                            "example": {"wx_ids": ["target-a"], "text": "hello"},
                        }
                    }
                }
            }
        },
        "/api/v1/messages/action": {"post": {"security": public_security()}},
        "/api/v1/outbox/{id}": {"get": {"security": public_security()}},
        "/api/v1/contacts": {"get": {"security": public_security()}},
        "/api/v1/modules/status": {"get": {"security": public_security()}},
        "/api/v1/ws": {"get": {"security": public_security()}},
        "/api/media/{media_path}": {
            "get": {
                "security": [{"BridgeAPIKeyHeader": []}],
                "responses": {"403": {"description": "media_forbidden"}},
            }
        },
    }
    if paths:
        openapi_paths.update(paths)
    return {
        "paths": openapi_paths,
        "components": {
            "responses": {
                "SendQueuedResponse": {"content": {"application/json": {"examples": {"ok": {}}}}},
                "MessageListResponse": {"content": {"application/json": {"examples": {"ok": {}}}}},
                "OutboxItemResponse": {"content": {"application/json": {"examples": {"ok": {}}}}},
                "ErrorResponse": {"content": {"application/json": {"example": {"code": "owner_wxid_unbound media_forbidden cursor_conflict"}}}},
            }
        },
    }


def openapi_go(spec: dict[str, Any] | None = None, html_terms: list[str] | None = None) -> str:
    terms = html_terms or docs.REQUIRED_HTML_TERMS
    html = "\n".join([*terms, *(f"/docs/{doc}" for doc in docs.REQUIRED_DOCS)])
    doc_files = "\n".join(f'"{doc}",' for doc in docs.REQUIRED_DOCS)
    return "\n".join(
        [
            f"const openAPIDocsHTML = `{html}`",
            f"const openAPIJSONDocument = `{json.dumps(spec or minimal_spec(), ensure_ascii=False)}`",
            f"var publicDocFiles = []string{{{doc_files}}}",
        ]
    )


class PublicAPIDocsValidatorTests(unittest.TestCase):
    def test_validate_openapi_accepts_required_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "openapi.go"
            write(path, openapi_go())

            with patch.object(docs, "OPENAPI_GO", path):
                self.assertEqual(docs.validate_openapi(), {"paths": len(minimal_spec()["paths"]), "doc_links": len(docs.REQUIRED_DOCS)})

    def test_validate_openapi_rejects_media_without_api_key_security(self) -> None:
        spec = minimal_spec()
        spec["paths"]["/api/media/{media_path}"]["get"]["security"] = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "openapi.go"
            write(path, openapi_go(spec))

            with patch.object(docs, "OPENAPI_GO", path):
                with self.assertRaisesRegex(SystemExit, "BridgeAPIKeyHeader"):
                    docs.validate_openapi()

    def test_validate_openapi_rejects_public_v1_operation_without_public_auth_scheme(self) -> None:
        spec = minimal_spec()
        spec["paths"]["/api/v1/messages"]["get"]["security"] = [
            {"BridgeAPIKeyHeader": []},
            {"BridgePasswordHeader": []},
            {"BridgePasswordQuery": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "openapi.go"
            write(path, openapi_go(spec))

            with patch.object(docs, "OPENAPI_GO", path):
                with self.assertRaisesRegex(SystemExit, "BridgeAPIKeyQuery"):
                    docs.validate_openapi()

    def test_module_contract_kind_endpoint_expands_to_all_message_paths(self) -> None:
        openapi_paths = {path: {} for path in docs.PUBLIC_MESSAGE_KIND_PATHS}
        with tempfile.TemporaryDirectory() as tmp:
            contract = Path(tmp) / "module-contract.md"
            write(contract, "`POST /api/v1/messages/{kind}`")

            with patch.object(docs, "DOCS_MODULE_CONTRACT", contract):
                docs.validate_public_endpoint_docs(openapi_paths)
                with self.assertRaisesRegex(SystemExit, "/api/v1/messages/image"):
                    docs.validate_public_endpoint_docs({"/api/v1/messages/text": {}})

    def test_docs_api_links_reject_broken_local_markdown_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = Path(tmp) / "docs" / "api.md"
            write(api, "[ok](adapter.md)\n[remote](https://example.test/guide.md)")
            write(api.parent / "adapter.md", "# ok")

            with patch.object(docs, "DOCS_API", api):
                self.assertEqual(docs.validate_docs_api_links(), 2)
            api.write_text("[missing](missing.md)", encoding="utf-8")
            with patch.object(docs, "DOCS_API", api):
                with self.assertRaisesRegex(SystemExit, "broken link"):
                    docs.validate_docs_api_links()

    def test_dockerfile_must_copy_all_public_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dockerfile = Path(tmp) / "Dockerfile"
            copied = "\n".join(
                f"COPY docs/{doc} /usr/share/wechat-observatory/docs/{doc}"
                for doc in ["api.md", *docs.REQUIRED_DOCS]
            )
            write(dockerfile, copied)

            with patch.object(docs, "DOCKERFILE", dockerfile):
                docs.validate_docker_docs_copy()
            dockerfile.write_text(copied.replace("protocol-stability-review-v1.md", "missing.md"), encoding="utf-8")
            with patch.object(docs, "DOCKERFILE", dockerfile):
                with self.assertRaisesRegex(SystemExit, "protocol-stability-review-v1.md"):
                    docs.validate_docker_docs_copy()


if __name__ == "__main__":
    unittest.main()
