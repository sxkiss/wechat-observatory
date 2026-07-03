#!/usr/bin/env python3
"""Unit tests for the public API contract checker safety logic."""

from __future__ import annotations

import json
import base64
import socket
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import public_api_contract_check as contract
import validate_public_api_fixtures as fixtures


def server_frame(opcode: int, payload: bytes) -> bytes:
    first = 0x80 | opcode
    length = len(payload)
    if length < 126:
        return bytes([first, length]) + payload
    if length < (1 << 16):
        return bytes([first, 126]) + length.to_bytes(2, "big") + payload
    return bytes([first, 127]) + length.to_bytes(8, "big") + payload


class BasicUtilitiesTests(unittest.TestCase):
    def test_absolute_url_joins_relative_paths_without_rewriting_absolute_urls(self) -> None:
        self.assertEqual(
            contract.absolute_url("http://127.0.0.1:8088/", "/api/v1/messages"),
            "http://127.0.0.1:8088/api/v1/messages",
        )
        self.assertEqual(
            contract.absolute_url("http://127.0.0.1:8088/base", "api/v1/messages"),
            "http://127.0.0.1:8088/base/api/v1/messages",
        )
        self.assertEqual(
            contract.absolute_url("https://example.test", "https://cdn.example.test/file"),
            "https://cdn.example.test/file",
        )

    def test_redact_masks_query_header_and_json_secrets(self) -> None:
        raw = (
            'GET /api?api_key=secret-key&token=abc123xyz&session=session-id&auth=auth-key HTTP/1.1\n'
            'X-Bridge-API-Key: bridge-key\n'
            'Authorization: Bearer auth-header\n'
            '{"api_key":"json-key","password":"p4ss-value","cookie":"cookie-value","session":"json-session","auth":"json-auth"}'
        )

        redacted = contract.redact(raw)

        self.assertNotIn("secret-key", redacted)
        self.assertNotIn("bridge-key", redacted)
        self.assertNotIn("abc123xyz", redacted)
        self.assertNotIn("session-id", redacted)
        self.assertNotIn("auth-key", redacted)
        self.assertNotIn("auth-header", redacted)
        self.assertNotIn("json-key", redacted)
        self.assertNotIn("p4ss-value", redacted)
        self.assertNotIn("cookie-value", redacted)
        self.assertNotIn("json-session", redacted)
        self.assertNotIn("json-auth", redacted)
        self.assertIn("api_key=<redacted>", redacted)
        self.assertIn('"api_key":"<redacted>"', redacted)

    def test_api_error_message_redacts_sensitive_body(self) -> None:
        err = contract.APIError(403, '{"api_key":"json-key","password":"p4ss-value"}')

        self.assertEqual(err.status, 403)
        self.assertNotIn("json-key", str(err))
        self.assertNotIn("p4ss-value", str(err))

    def test_request_json_requires_valid_json_object(self) -> None:
        with patch.object(contract, "request_bytes", return_value=(200, b"{")):
            with self.assertRaisesRegex(contract.ContractError, "not valid JSON"):
                contract.request_json("http://127.0.0.1:8088", "key", "GET", "/api")
        with patch.object(contract, "request_bytes", return_value=(200, b"[]")):
            with self.assertRaisesRegex(contract.ContractError, "not a JSON object"):
                contract.request_json("http://127.0.0.1:8088", "key", "GET", "/api")

    def test_check_docs_validates_links_without_requiring_english_copy(self) -> None:
        spec = {
            "paths": {path: {} for path in contract.REQUIRED_OPENAPI_PATHS},
            "x-errors": contract.REQUIRED_ERROR_CODES,
        }
        html = "<html><body>" + "\n".join(contract.REQUIRED_DOC_LINKS) + "<h1>微信观测站 API 协议</h1></body></html>"

        def fake_request(_base_url: str, _api_key: str, _method: str, path: str, **_kwargs):
            if path == "/docs/openapi.json":
                return 200, json.dumps(spec).encode("utf-8")
            if path == "/docs":
                return 200, html.encode("utf-8")
            raise AssertionError(path)

        with patch.object(contract, "request_bytes", side_effect=fake_request):
            summary = contract.check_docs("http://127.0.0.1:8088")

        self.assertTrue(summary["ok"])
        self.assertEqual(summary["openapi_path_count"], len(contract.REQUIRED_OPENAPI_PATHS))

    def test_check_docs_reports_missing_required_doc_links(self) -> None:
        spec = {
            "paths": {path: {} for path in contract.REQUIRED_OPENAPI_PATHS},
            "x-errors": contract.REQUIRED_ERROR_CODES,
        }

        def fake_request(_base_url: str, _api_key: str, _method: str, path: str, **_kwargs):
            if path == "/docs/openapi.json":
                return 200, json.dumps(spec).encode("utf-8")
            if path == "/docs":
                return 200, b"<html><body>/docs/openapi.json</body></html>"
            raise AssertionError(path)

        with patch.object(contract, "request_bytes", side_effect=fake_request):
            with self.assertRaisesRegex(contract.ContractError, "missing required link"):
                contract.check_docs("http://127.0.0.1:8088")

    def test_message_limit_is_bounded_for_live_contract_checks(self) -> None:
        self.assertEqual(contract.normalize_message_limit(1), 1)
        self.assertEqual(contract.normalize_message_limit(contract.MAX_MESSAGE_LIMIT), contract.MAX_MESSAGE_LIMIT)
        with self.assertRaisesRegex(contract.ContractError, "message limit"):
            contract.normalize_message_limit(0)
        with self.assertRaisesRegex(contract.ContractError, "message limit"):
            contract.normalize_message_limit(contract.MAX_MESSAGE_LIMIT + 1)

    def test_message_pages_is_bounded_for_live_contract_checks(self) -> None:
        self.assertEqual(contract.normalize_message_pages(1), 1)
        self.assertEqual(contract.normalize_message_pages(contract.MAX_MESSAGE_PAGES), contract.MAX_MESSAGE_PAGES)
        with self.assertRaisesRegex(contract.ContractError, "message pages"):
            contract.normalize_message_pages(0)
        with self.assertRaisesRegex(contract.ContractError, "message pages"):
            contract.normalize_message_pages(contract.MAX_MESSAGE_PAGES + 1)

    def test_check_messages_uses_configured_limit_and_reports_coverage(self) -> None:
        calls: list[str] = []

        def fake_request(_base_url: str, _api_key: str, _method: str, path: str, **_kwargs):
            calls.append(path)
            if "after_id=1&before_id=2" in path:
                return {"code": "cursor_conflict"}
            return {
                "ok": True,
                "protocol_version": "v1",
                "cursor_field": "id",
                "messages": [{"kind": "text", "direction": "recv", "chat_id": "chat-a", "chat_kind": "direct"}],
            }

        with patch.object(contract, "request_json", side_effect=fake_request):
            summary = contract.check_messages(
                "http://127.0.0.1:8088",
                "key",
                limit=123,
                required_kinds={"text"},
                required_fixture_ids={"public-api-v1.text"},
            )

        self.assertEqual(calls[0], "/api/v1/messages?limit=123")
        self.assertIn("after_id=1&before_id=2", calls[1])
        self.assertEqual(summary["message_limit"], 123)
        self.assertEqual(summary["message_pages_requested"], 1)
        self.assertEqual(summary["message_pages_scanned"], 1)
        self.assertEqual(summary["coverage"]["kind_counts"], {"text": 1})

    def test_check_messages_scans_cursor_pages_for_coverage(self) -> None:
        calls: list[str] = []

        def fake_request(_base_url: str, _api_key: str, _method: str, path: str, **_kwargs):
            calls.append(path)
            if "after_id=1&before_id=2" in path:
                return {"code": "cursor_conflict"}
            if "before_id=10" in path:
                return {
                    "ok": True,
                    "protocol_version": "v1",
                    "cursor_field": "id",
                    "messages": [{"id": "8", "kind": "video", "direction": "recv", "chat_id": "chat-a", "chat_kind": "direct", "media": [{"kind": "video"}]}],
                    "has_more": False,
                }
            return {
                "ok": True,
                "protocol_version": "v1",
                "cursor_field": "id",
                "messages": [{"id": "10", "kind": "text", "direction": "recv", "chat_id": "chat-a", "chat_kind": "direct"}],
                "has_more": True,
                "next_cursor": 10,
                "next_cursor_param": "before_id",
            }

        with patch.object(contract, "request_json", side_effect=fake_request):
            summary = contract.check_messages(
                "http://127.0.0.1:8088",
                "key",
                limit=1,
                pages=2,
                required_fixture_ids={"public-api-v1.text", "public-api-v1.video"},
            )

        self.assertEqual(calls[0], "/api/v1/messages?limit=1")
        self.assertEqual(calls[1], "/api/v1/messages?limit=1&before_id=10")
        self.assertIn("after_id=1&before_id=2", calls[2])
        self.assertEqual(summary["message_count"], 2)
        self.assertEqual(summary["message_pages_requested"], 2)
        self.assertEqual(summary["message_pages_scanned"], 2)
        self.assertFalse(summary["message_has_more"])
        self.assertEqual(summary["coverage"]["media_kind_counts"], {"video": 1})
        self.assertEqual(summary["coverage"]["required_fixtures_present"], ["public-api-v1.text", "public-api-v1.video"])

    def test_check_messages_missing_fixture_details_include_page_context(self) -> None:
        def fake_request(_base_url: str, _api_key: str, _method: str, path: str, **_kwargs):
            if "after_id=1&before_id=2" in path:
                return {"code": "cursor_conflict"}
            return {
                "ok": True,
                "protocol_version": "v1",
                "cursor_field": "id",
                "messages": [{"id": "10", "kind": "text", "direction": "recv", "chat_id": "chat-a", "chat_kind": "direct"}],
                "has_more": False,
            }

        with patch.object(contract, "request_json", side_effect=fake_request):
            with self.assertRaisesRegex(contract.ContractError, "missing required fixture coverage") as raised:
                contract.check_messages(
                    "http://127.0.0.1:8088",
                    "key",
                    limit=1,
                    pages=3,
                    required_fixture_ids={"public-api-v1.video"},
                )

        details = raised.exception.details
        self.assertEqual(details["message_count"], 1)
        self.assertEqual(details["message_limit"], 1)
        self.assertEqual(details["message_pages_requested"], 3)
        self.assertEqual(details["message_pages_scanned"], 1)
        self.assertFalse(details["message_has_more"])
        self.assertEqual(details["message_page_summaries"][0]["message_count"], 1)

    def test_public_summary_message_counts_media_and_diagnostics_without_content(self) -> None:
        summary = contract.public_summary_message(
            {
                "id": 10,
                "kind": "image",
                "direction": "recv",
                "chat_kind": "room",
                "message_type": 3,
                "text": "do not leak full chat body",
                "media": [{"url": "/api/media/a.png"}],
                "appmsg": {"type": 33},
                "location": {"latitude": 1.0},
                "unsupported": ["field-a"],
            }
        )

        self.assertEqual(summary["text_len"], len("do not leak full chat body"))
        self.assertEqual(summary["media_count"], 1)
        self.assertTrue(summary["appmsg_present"])
        self.assertEqual(summary["appmsg_type"], 33)
        self.assertTrue(summary["location_present"])
        self.assertEqual(summary["unsupported_count"], 1)
        self.assertNotIn("do not leak", json.dumps(summary))

    def test_message_coverage_counts_all_recent_protocol_shapes(self) -> None:
        coverage = contract.summarize_message_coverage(
            [
                {
                    "id": 1,
                    "kind": "image",
                    "direction": "recv",
                    "chat_id": "chat-a",
                    "chat_kind": "direct",
                    "message_type": 3,
                    "media": [{"kind": "image", "url": "/api/media/a.png"}],
                    "text": "hidden body",
                },
                {
                    "id": 2,
                    "kind": "appmsg",
                    "direction": "sent",
                    "chat_id": "room-a",
                    "chat_kind": "room",
                    "message_type": 49,
                    "appmsg": {"type": 33, "subtype": "mini_program"},
                    "unsupported": ["field-a"],
                    "evidence": ["raw_xml.appmsg.type=33"],
                },
                {
                    "id": 3,
                    "kind": "location",
                    "direction": "recv",
                    "chat_id": "chat-a",
                    "chat_kind": "direct",
                    "message_type": 48,
                    "location": {"latitude": 1.0, "longitude": 2.0},
                },
            ],
            {"image", "appmsg"},
            {"image"},
            {"mini_program"},
        )

        encoded = json.dumps(coverage, ensure_ascii=False)
        self.assertEqual(coverage["kind_counts"], {"appmsg": 1, "image": 1, "location": 1})
        self.assertEqual(coverage["direction_counts"], {"recv": 2, "sent": 1})
        self.assertEqual(coverage["media_kind_counts"], {"image": 1})
        self.assertEqual(coverage["appmsg_subtype_counts"], {"mini_program": 1})
        self.assertEqual(coverage["media_message_count"], 1)
        self.assertEqual(coverage["appmsg_message_count"], 1)
        self.assertEqual(coverage["location_message_count"], 1)
        self.assertEqual(coverage["unsupported_total"], 1)
        self.assertEqual(coverage["evidence_total"], 1)
        self.assertEqual(coverage["required_media_kinds_present"], ["image"])
        self.assertEqual(coverage["required_appmsg_subtypes_present"], ["mini_program"])
        self.assertIn("public-api-v1.image", coverage["fixture_coverage"]["covered"])
        self.assertIn("public-api-v1.location", coverage["fixture_coverage"]["covered"])
        self.assertIn("public-api-v1.mini-program", coverage["fixture_coverage"]["covered"])
        self.assertIn("public-api-v1.video", coverage["fixture_coverage"]["missing"])
        self.assertEqual(coverage["required_fixtures_present"], [])
        self.assertNotIn("hidden body", encoded)

    def test_message_coverage_can_require_recent_kinds_media_and_appmsg(self) -> None:
        messages = [
            {
                "kind": "text",
                "direction": "recv",
                "chat_id": "chat-a",
                "chat_kind": "direct",
                "media": [{"kind": "image"}],
                "appmsg": {"subtype": "link"},
            }
        ]

        contract.summarize_message_coverage(messages, {"text"})
        with self.assertRaisesRegex(contract.ContractError, "missing required message kind"):
            contract.summarize_message_coverage(messages, {"image"})
        contract.summarize_message_coverage(messages, required_media_kinds={"image"})
        with self.assertRaisesRegex(contract.ContractError, "missing required media kind"):
            contract.summarize_message_coverage(messages, required_media_kinds={"voice"})
        contract.summarize_message_coverage(messages, required_appmsg_subtypes={"link"})
        with self.assertRaisesRegex(contract.ContractError, "missing required appmsg subtype"):
            contract.summarize_message_coverage(messages, required_appmsg_subtypes={"mini_program"})
        contract.summarize_message_coverage(messages, required_fixture_ids={"public-api-v1.text", "public-api-v1.image", "public-api-v1.link"})
        with self.assertRaisesRegex(contract.ContractError, "missing required fixture coverage"):
            contract.summarize_message_coverage(messages, required_fixture_ids={"public-api-v1.video"})

    def test_missing_fixture_requirement_reports_structured_details(self) -> None:
        messages = [
            {
                "kind": "text",
                "direction": "recv",
                "chat_id": "chat-a",
                "chat_kind": "direct",
                "text": "hidden body",
                "media": [{"kind": "image"}],
            }
        ]

        with self.assertRaisesRegex(contract.ContractError, "missing required fixture coverage") as raised:
            contract.summarize_message_coverage(
                messages,
                required_fixture_ids={
                    "public-api-v1.text",
                    "public-api-v1.image",
                    "public-api-v1.video",
                },
            )

        details = raised.exception.details
        encoded = json.dumps(details, ensure_ascii=False)
        self.assertEqual(details["missing_required_fixtures"], ["public-api-v1.video"])
        self.assertEqual(
            details["required_fixture_ids"],
            ["public-api-v1.image", "public-api-v1.text", "public-api-v1.video"],
        )
        self.assertIn("public-api-v1.image", details["fixture_coverage"]["covered"])
        self.assertIn("public-api-v1.video", details["fixture_coverage"]["missing"])
        self.assertNotIn("hidden body", encoded)

    def test_payment_candidates_are_diagnostic_not_fixture_coverage(self) -> None:
        messages = [
            {
                "kind": "unknown",
                "direction": "recv",
                "chat_id": "chat-a",
                "chat_kind": "direct",
                "message_type": 419430449,
            },
            {
                "kind": "appmsg",
                "direction": "recv",
                "chat_id": "chat-a",
                "chat_kind": "direct",
                "message_type": 49,
                "appmsg": {"type": 2001},
            },
        ]

        with self.assertRaisesRegex(contract.ContractError, "missing required fixture coverage") as raised:
            contract.summarize_message_coverage(messages, required_fixture_ids={"public-api-v1.payment"})

        details = raised.exception.details
        fixture_coverage = details["fixture_coverage"]
        self.assertEqual(
            fixture_coverage["payment_candidate_counts"],
            {"appmsg_type.red_packet": 1, "message_type.transfer": 1},
        )
        self.assertEqual(fixture_coverage["payment_candidate_total"], 2)
        self.assertIn("public-api-v1.payment", fixture_coverage["missing"])
        self.assertIn("payment candidates found", details["diagnostics"][0])

    def test_parse_required_coverage_values_normalizes_hyphenated_names(self) -> None:
        self.assertEqual(contract.parse_required_coverage_values("text, chat-history,mini_program"), {"text", "chat_history", "mini_program"})

    def test_parse_required_fixture_ids_accepts_short_and_full_names(self) -> None:
        self.assertEqual(
            contract.parse_required_fixture_ids("image,chat_history,public-api-v1.mini-program"),
            {"public-api-v1.image", "public-api-v1.chat-history", "public-api-v1.mini-program"},
        )
        self.assertEqual(
            contract.parse_required_fixture_ids("all"),
            set(contract.PUBLIC_FIXTURE_COVERAGE_REQUIREMENTS),
        )
        self.assertEqual(
            contract.parse_required_fixture_ids("image,all"),
            set(contract.PUBLIC_FIXTURE_COVERAGE_REQUIREMENTS),
        )
        self.assertEqual(
            contract.parse_required_fixture_ids("all-safe-live"),
            contract.PUBLIC_SAFE_LIVE_FIXTURE_IDS,
        )
        self.assertEqual(
            contract.parse_required_fixture_ids("all_safe"),
            contract.PUBLIC_SAFE_LIVE_FIXTURE_IDS,
        )
        self.assertNotIn("public-api-v1.payment", contract.PUBLIC_SAFE_LIVE_FIXTURE_IDS)
        self.assertIn("public-api-v1.video", contract.PUBLIC_SAFE_LIVE_FIXTURE_IDS)
        with self.assertRaisesRegex(contract.ContractError, "unknown required fixture"):
            contract.parse_required_fixture_ids("not-a-fixture")

    def test_fixture_coverage_summarizes_protocol_samples_without_payloads(self) -> None:
        coverage = contract.summarize_fixture_coverage(
            {"text": 2, "payment": 1},
            {"image": 1, "voice": 1},
            {"link": 1, "chat_history": 1},
            0,
        )

        self.assertIn("public-api-v1.text", coverage["covered"])
        self.assertIn("public-api-v1.image", coverage["covered"])
        self.assertIn("public-api-v1.voice", coverage["covered"])
        self.assertIn("public-api-v1.link", coverage["covered"])
        self.assertIn("public-api-v1.chat-history", coverage["covered"])
        self.assertIn("public-api-v1.payment", coverage["covered"])
        self.assertIn("public-api-v1.location", coverage["missing"])
        self.assertIn("public-api-v1.mini-program", coverage["missing"])
        self.assertEqual(coverage["fixture_count"], len(contract.PUBLIC_FIXTURE_COVERAGE_REQUIREMENTS))

    def test_live_fixture_coverage_mapping_matches_public_fixture_contract(self) -> None:
        self.assertEqual(set(contract.PUBLIC_FIXTURE_COVERAGE_REQUIREMENTS), fixtures.REQUIRED_FIXTURE_IDS)

    def test_contacts_filters_out_non_object_values(self) -> None:
        self.assertEqual(list(contract.contacts({"contacts": [{"wxid": "a"}, "bad", 1, {"wxid": "b"}]})), [{"wxid": "a"}, {"wxid": "b"}])
        self.assertEqual(list(contract.contacts({"contacts": "bad"})), [])

    def test_ws_path_with_query_encodes_and_omits_empty_values(self) -> None:
        self.assertEqual(
            contract.ws_path_with_query("/api/v1/ws", {"replay": "1", "cursor": "", "q": "a b&c"}),
            "/api/v1/ws?replay=1&q=a+b%26c",
        )


class WebSocketFrameTests(unittest.TestCase):
    def test_ws_send_json_writes_masked_text_frame(self) -> None:
        left, right = socket.socketpair()
        try:
            with patch.object(contract.os, "urandom", return_value=b"\x01\x02\x03\x04"):
                contract.ws_send_json(left, {"type": "ping"})

            opcode, payload = contract.ws_recv_frame(right, "client json", bytearray())

            self.assertEqual(opcode, 0x1)
            self.assertEqual(json.loads(payload.decode("utf-8")), {"type": "ping"})
        finally:
            left.close()
            right.close()

    def test_ws_recv_frame_can_read_complete_frame_from_pending_buffer(self) -> None:
        payload = b"x" * 130
        pending = bytearray(server_frame(0x1, payload))
        left, right = socket.socketpair()
        try:
            opcode, got = contract.ws_recv_frame(left, "pending text", pending)

            self.assertEqual(opcode, 0x1)
            self.assertEqual(got, payload)
            self.assertEqual(pending, bytearray())
        finally:
            left.close()
            right.close()

    def test_ws_recv_json_answers_ping_with_pong_before_returning_text(self) -> None:
        left, right = socket.socketpair()
        try:
            right.sendall(server_frame(0x9, b"are-you-there") + server_frame(0x1, b'{"type":"hello","ok":true}'))

            message = contract.ws_recv_json(left, 1, "hello", bytearray())
            opcode, payload = contract.ws_recv_frame(right, "pong", bytearray())

            self.assertEqual(message, {"type": "hello", "ok": True})
            self.assertEqual(opcode, 0xA)
            self.assertEqual(payload, b"are-you-there")
        finally:
            left.close()
            right.close()


def args(**overrides):
    values = {
        "api_key": "test-key",
        "base_url": "http://127.0.0.1:8088",
        "target_wxid": "12345@chatroom",
        "target_query": "",
        "target_name": "有风测试群",
        "target_kind": "room",
        "target_name_contains": "",
        "target_name_exact": "",
        "require_target_contact": False,
        "require_message_kind": "",
        "require_media_kind": "",
        "require_appmsg_subtype": "",
        "message_limit": contract.DEFAULT_MESSAGE_LIMIT,
        "send_profile": "custom",
        "send_kinds": "text,image",
        "image_file": "",
        "image_media_url": "",
        "video_file": "",
        "video_media_url": "",
        "voice_file": "",
        "voice_media_url": "",
        "voice_duration_ms": 1000,
        "file_path": "",
        "file_media_url": "",
        "link_url": "https://example.com/wechat-observatory-contract-check",
        "emoji_source_chat_record_id": 0,
        "emoji_md5": "",
        "emoji_product_id": "",
        "quote_msg_id": 0,
        "quote_chat_record_id": 0,
        "quote_talker": "",
        "quote_sender_wxid": "",
        "mini_program_source_chat_record_id": 0,
        "mini_program_title": "",
        "mini_program_description": "wechat-observatory public API contract check",
        "mini_program_username": "",
        "mini_program_page_path": "",
        "mini_program_appid": "",
        "chat_history_source_chat_record_id": 0,
        "chat_history_source_chat_record_ids": "",
        "chat_history_recorditem_xml": "",
        "chat_history_forward_original": False,
        "location_lat": 39.9042,
        "location_lon": 116.4074,
        "location_label": "Public API contract check",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class TargetSafetyTests(unittest.TestCase):
    def test_require_target_contact_rejects_unresolved_wxid(self) -> None:
        target = {"wxid": "12345@chatroom", "nickname": "有风测试群", "_target_source": "wxid"}
        with self.assertRaisesRegex(contract.ContractError, "not found in contacts"):
            contract.require_target_safety(args(require_target_contact=True), target)

    def test_target_name_contains_checks_resolved_display_name(self) -> None:
        target = {"wxid": "12345@chatroom", "remark": "有风测试群", "_target_source": "contacts_by_wxid"}
        contract.require_target_safety(args(target_name_contains="有风", require_target_contact=True), target)
        with self.assertRaisesRegex(contract.ContractError, "display name"):
            contract.require_target_safety(args(target_name_contains="两碗冰"), target)

    def test_target_name_exact_checks_resolved_display_name(self) -> None:
        target = {"wxid": "12345@chatroom", "remark": "有风测试群", "_target_source": "contacts_by_wxid"}
        contract.require_target_safety(args(target_name_exact="有风测试群"), target)
        with self.assertRaisesRegex(contract.ContractError, "must equal"):
            contract.require_target_safety(args(target_name_exact="有风"), target)

    def test_resolve_target_prefers_contact_match_for_explicit_wxid(self) -> None:
        resolved = {"wxid": "12345@chatroom", "remark": "有风测试群", "chatroom": True, "_target_source": "contacts_by_wxid"}
        with patch.object(contract, "find_target_by_wxid", return_value=resolved):
            self.assertEqual(contract.resolve_target(args()), resolved)

    def test_resolve_target_falls_back_to_wxid_when_contact_is_absent(self) -> None:
        with patch.object(contract, "find_target_by_wxid", return_value=None):
            target = contract.resolve_target(args())
        self.assertEqual(target["_target_source"], "wxid")
        self.assertEqual(target["wxid"], "12345@chatroom")

    def test_target_kind_rejects_room_and_direct_mismatches(self) -> None:
        with self.assertRaisesRegex(contract.ContractError, "room id"):
            contract.ensure_target_kind("wxid_friend", "room")
        with self.assertRaisesRegex(contract.ContractError, "direct"):
            contract.ensure_target_kind("12345@chatroom", "direct")


class DryRunTests(unittest.TestCase):
    def test_contract_check_png_is_visible_size_not_one_pixel(self) -> None:
        blob = base64.b64decode(contract.CONTRACT_CHECK_PNG_BASE64)
        width, height = struct.unpack("!II", blob[16:24])

        self.assertEqual((width, height), (320, 180))
        self.assertGreater(len(blob), 200)

    def test_send_payload_summary_redacts_media_base64_and_targets(self) -> None:
        summary = contract.summarize_send_payload(
            "image",
            {
                "endpoint": "/api/v1/messages/image",
                "wx_ids": ["12345@chatroom"],
                "media_base64": "secret-base64",
                "media_name": "sample.png",
                "media_mime": "image/png",
                "text": "hello",
                "match_text": "hello",
            },
        )
        encoded = json.dumps(summary, ensure_ascii=False)
        self.assertNotIn("secret-base64", encoded)
        self.assertNotIn("12345@chatroom", encoded)
        self.assertTrue(summary["has_media_base64"])
        self.assertEqual(summary["target_count"], 1)
        self.assertEqual(summary["fields"], ["media_mime", "media_name", "text"])

    def test_dry_run_send_checks_builds_payloads_without_queueing(self) -> None:
        resolved = {"wxid": "12345@chatroom", "remark": "有风测试群", "chatroom": True, "_target_source": "contacts_by_wxid"}
        with patch.object(contract, "find_target_by_wxid", return_value=resolved):
            summary = contract.dry_run_send_checks(args(target_name_contains="有风", require_target_contact=True))
        self.assertTrue(summary["dry_run"])
        self.assertEqual(summary["target_source"], "contacts_by_wxid")
        self.assertEqual([item["kind"] for item in summary["payloads"]], ["text", "image"])
        self.assertTrue(summary["payloads"][1]["has_media_base64"])

    def test_dry_run_safe_basic_profile_builds_safe_payload_set(self) -> None:
        resolved = {"wxid": "12345@chatroom", "remark": "有风测试群", "chatroom": True, "_target_source": "contacts_by_wxid"}
        with patch.object(contract, "find_target_by_wxid", return_value=resolved):
            summary = contract.dry_run_send_checks(
                args(send_profile="safe-basic", send_kinds="text", target_name_contains="有风", require_target_contact=True)
            )

        self.assertEqual([item["kind"] for item in summary["payloads"]], contract.SAFE_BASIC_SEND_KINDS)
        self.assertTrue(all(not item.get("skipped") for item in summary["payloads"]))

    def test_dry_run_all_kinds_summarizes_payloads_without_sensitive_values(self) -> None:
        resolved = {"wxid": "12345@chatroom", "remark": "有风测试群", "chatroom": True, "_target_source": "contacts_by_wxid"}
        with patch.object(contract, "find_target_by_wxid", return_value=resolved):
            summary = contract.dry_run_send_checks(
                args(send_kinds="all", target_name_contains="有风", require_target_contact=True)
            )

        payloads = {item["kind"]: item for item in summary["payloads"]}
        self.assertEqual(set(payloads), contract.SUPPORTED_SEND_KINDS)
        encoded = json.dumps(summary, ensure_ascii=False)
        self.assertNotIn("12345@chatroom", encoded)
        self.assertNotIn(contract.CONTRACT_CHECK_PNG_BASE64[:16], encoded)
        self.assertNotIn(contract.MINIMAL_AMR_BASE64[:16], encoded)
        self.assertTrue(payloads["image"]["has_media_base64"])
        self.assertTrue(payloads["voice"]["has_media_base64"])
        self.assertIn("media_duration_ms", payloads["voice"]["fields"])
        self.assertEqual(payloads["video"]["reason"], "video requires --video-file or --video-media-url")
        self.assertEqual(payloads["emoji"]["reason"], "emoji requires --emoji-source-chat-record-id or --emoji-md5")
        self.assertIn("quote requires", payloads["quote"]["reason"])
        self.assertIn("mini-program requires", payloads["mini-program"]["reason"])
        self.assertIn("chat-history requires", payloads["chat-history"]["reason"])

    def test_confirm_voice_requires_real_media_sample(self) -> None:
        resolved = {"wxid": "12345@chatroom", "remark": "有风测试群", "chatroom": True, "_target_source": "contacts_by_wxid"}
        with patch.object(contract, "find_target_by_wxid", return_value=resolved):
            with self.assertRaisesRegex(contract.ContractError, "real AMR/SILK sample"):
                contract.send_checks(args(send_kinds="voice", target_name_exact="有风测试群"))

    def test_confirm_send_requires_exact_target_name_guard(self) -> None:
        resolved = {"wxid": "12345@chatroom", "remark": "有风测试群", "chatroom": True, "_target_source": "contacts_by_wxid"}
        with patch.object(contract, "find_target_by_wxid", return_value=resolved):
            with self.assertRaisesRegex(contract.ContractError, "target-name-exact"):
                contract.send_checks(args(send_kinds="text"))

    def test_confirm_send_requires_contact_resolved_target(self) -> None:
        with patch.object(contract, "find_target_by_wxid", return_value=None):
            with self.assertRaisesRegex(contract.ContractError, "found in contacts"):
                contract.send_checks(
                    args(
                        send_kinds="text",
                        target_name="有风测试群",
                        target_name_exact="有风测试群",
                    )
                )

    def test_source_forward_kinds_emit_payload_when_source_ids_are_present(self) -> None:
        resolved = {"wxid": "12345@chatroom", "remark": "有风测试群", "chatroom": True, "_target_source": "contacts_by_wxid"}
        with patch.object(contract, "find_target_by_wxid", return_value=resolved):
            summary = contract.dry_run_send_checks(
                args(
                    send_kinds="emoji,quote,mini-program,chat-history",
                    emoji_source_chat_record_id=11,
                    quote_msg_id=22,
                    mini_program_source_chat_record_id=33,
                    chat_history_source_chat_record_ids="44,55",
                )
            )

        payloads = {item["kind"]: item for item in summary["payloads"]}
        for item in payloads.values():
            self.assertNotIn("skipped", item)
            self.assertEqual(item["target_count"], 1)
        self.assertIn("source_chat_record_id", payloads["emoji"]["fields"])
        self.assertIn("quote_msg_id", payloads["quote"]["fields"])
        self.assertIn("source_chat_record_id", payloads["mini-program"]["fields"])
        self.assertIn("source_chat_record_ids", payloads["chat-history"]["fields"])


class SendSuccessRequirementTests(unittest.TestCase):
    def test_required_send_success_accepts_sent_and_visible_results(self) -> None:
        result = contract.check_required_send_success(
            {"results": [{"kind": "text", "outbox_final_status": "sent", "outbound_message_found": True}]}
        )
        self.assertEqual(result, {"send_success": True})

    def test_required_send_success_rejects_skipped_failed_or_missing_history(self) -> None:
        cases = [
            {"results": [{"kind": "emoji", "skipped": True, "reason": "missing source"}]},
            {"results": [{"kind": "text", "outbox_final_status": "failed", "outbound_message_found": False}]},
            {"results": [{"kind": "image", "outbox_final_status": "sent", "outbound_message_found": False}]},
        ]
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(contract.ContractError):
                    contract.check_required_send_success(case)


class ParseSendKindsTests(unittest.TestCase):
    def test_parse_send_kinds_normalizes_aliases_and_deduplicates(self) -> None:
        self.assertEqual(contract.parse_send_kinds("text,image,text,mini_program"), ["text", "image", "mini-program"])
        self.assertEqual(contract.parse_send_kinds("all-basic"), ["text", "image", "file", "link", "location"])
        self.assertEqual(contract.parse_send_kinds("safe-basic"), ["text", "image", "file", "link", "location"])

    def test_selected_send_kinds_uses_profile_when_no_explicit_kind_override(self) -> None:
        selected = contract.selected_send_kinds(args(send_profile="safe-basic", send_kinds="text"))

        self.assertEqual(selected, contract.SAFE_BASIC_SEND_KINDS)

    def test_selected_send_kinds_rejects_profile_with_explicit_kind_override(self) -> None:
        with self.assertRaisesRegex(contract.ContractError, "cannot be combined"):
            contract.selected_send_kinds(args(send_profile="safe-basic", send_kinds="text,image"))


if __name__ == "__main__":
    unittest.main()
