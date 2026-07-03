#!/usr/bin/env python3
"""Validate Android Action Outbox coverage without building the APK.

The Android module currently has no Gradle wrapper in this environment, so the
standard verification suite cannot always compile it. This check keeps the
gateway outbox protocol and the LSPosed action dispatcher aligned.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENTS_GO = ROOT / "internal" / "bridge" / "events.go"
HOOK_ENTRY = ROOT / "android-module" / "app" / "src" / "main" / "java" / "cc" / "wechat" / "observatory" / "HookEntry.java"

ACTION_METHODS = {
    "text": "sendText(",
    "image": "sendImageAction(",
    "video": "sendVideoAction(",
    "voice": "sendVoiceAction(",
    "file": "sendFileAction(",
    "emoji": "sendEmojiAction(",
    "location": "sendLocationAction(",
    "quote": "sendQuoteAction(",
    "link": "sendLinkAction(",
    "mini_program": "sendMiniProgramAction(",
    "chat_history": "sendChatHistoryAction(",
}

ACTION_HANDLER_DEFINITIONS = {
    kind: method[:-1] for kind, method in ACTION_METHODS.items() if kind != "text"
}

MEDIA_ACTION_REQUIREMENTS = {
    "image": ["media_url is required", "downloadOutboxMedia(", "media download produced empty file", "sendImage(", "mediaFile.delete()"],
    "video": ["media_url is required", "downloadOutboxMedia(", "media download produced empty file", "sendVideo(", "mediaFile.delete()"],
    "voice": [
        "media_url is required",
        "downloadOutboxMedia(",
        "media download produced empty file",
        "isSupportedVoiceMedia(",
        "sendVoice(",
        "mediaFile.delete()",
    ],
    "file": ["media_url is required", "downloadOutboxMedia(", "media download produced empty file", "sendFile(", "mediaFile.delete()"],
}


def extract_outbox_kinds(source: str) -> list[str]:
    kinds = re.findall(r"OutboxKind[A-Za-z]+\s*=\s*\"([^\"]+)\"", source)
    seen: set[str] = set()
    ordered: list[str] = []
    for kind in kinds:
        if kind not in seen:
            seen.add(kind)
            ordered.append(kind)
    return ordered


def extract_method_body(source: str, method_name: str) -> str:
    match = re.search(
        r"(?:private|public|protected)\s+static\s+[\w<>\[\]]+\s+"
        + re.escape(method_name)
        + r"\s*\(",
        source,
    )
    if match is None:
        return ""
    brace = source.find("{", match.start())
    if brace < 0:
        return ""
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace : index + 1]
    return ""


def validate_action_coverage(events_source: str, hook_source: str) -> dict[str, object]:
    handle_body = extract_method_body(hook_source, "handleOutboxItems")
    ack_body = extract_method_body(hook_source, "outboxAck")

    kinds = extract_outbox_kinds(events_source)
    missing_known_methods = [kind for kind in kinds if kind not in ACTION_METHODS]
    missing_dispatch = [
        kind
        for kind in kinds
        if f'"{kind}".equals(kind)' not in handle_body or ACTION_METHODS.get(kind, "") not in handle_body
    ]
    missing_handler_definitions = [
        kind
        for kind, method in ACTION_HANDLER_DEFINITIONS.items()
        if kind in kinds and f"SendResult {method}" not in hook_source
    ]
    missing_media_requirements = []
    for kind, requirements in MEDIA_ACTION_REQUIREMENTS.items():
        if kind not in kinds:
            continue
        body = extract_method_body(hook_source, ACTION_HANDLER_DEFINITIONS[kind])
        missing = [requirement for requirement in requirements if requirement not in body]
        if missing:
            missing_media_requirements.append({"kind": kind, "missing": missing})

    unknown_failed_ack = "unsupported outbox kind" in handle_body and "SendResult.failed" in handle_body
    terminal_ack = (
        'ack.put("status", result.ok ? "sent" : "failed")' in ack_body
        and 'ack.put("error", result.error)' in ack_body
    )
    legacy_text_default = 'kind = isBlank(item.optString("media_kind", "")) ? "text"' in handle_body

    errors = []
    if missing_known_methods:
        errors.append({"type": "missing_validator_mapping", "kinds": missing_known_methods})
    if missing_dispatch:
        errors.append({"type": "missing_android_dispatch", "kinds": missing_dispatch})
    if missing_handler_definitions:
        errors.append({"type": "missing_android_handler_definition", "kinds": missing_handler_definitions})
    if missing_media_requirements:
        errors.append({"type": "missing_media_action_requirements", "items": missing_media_requirements})
    if not unknown_failed_ack:
        errors.append({"type": "missing_unknown_kind_failed_ack"})
    if not terminal_ack:
        errors.append({"type": "missing_terminal_ack_status_or_error"})
    if not legacy_text_default:
        errors.append({"type": "missing_legacy_text_default"})

    summary = {
        "ok": not errors,
        "kind_count": len(kinds),
        "kinds": kinds,
        "unknown_failed_ack": unknown_failed_ack,
        "terminal_ack": terminal_ack,
        "legacy_text_default": legacy_text_default,
        "errors": errors,
    }
    return summary


def main() -> int:
    events_source = EVENTS_GO.read_text(encoding="utf-8")
    hook_source = HOOK_ENTRY.read_text(encoding="utf-8")
    summary = validate_action_coverage(events_source, hook_source)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
