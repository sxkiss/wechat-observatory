"""Minimal Python client for wechat-observatory public API v1.

This module intentionally uses only the Python standard library. It is small
adapter glue, not a generated SDK. Helpers return JSON dictionaries and avoid
printing API keys, raw XML, media base64, or full message bodies.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, Iterator, Optional

FINAL_OUTBOX_STATUSES = frozenset({"sent", "failed"})


class APIError(RuntimeError):
    def __init__(self, status: int, body: str, api_key: str = "") -> None:
        super().__init__(f"HTTP {status}: {redact_text(body, api_key)[:300]}")
        self.status = status
        self.body = body


class WechatObservatoryClient:
    """Tiny public API v1 client.

    The client is intentionally explicit: send methods only queue outbox items;
    callers must poll outbox status until `sent` or `failed`.
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.timeout = timeout
        if not self.base_url:
            raise ValueError("base_url is required")
        if not self.api_key:
            raise ValueError("api_key is required")

    def request_json(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        url = self.base_url + path
        if query:
            clean_query = {key: value for key, value in query.items() if value is not None}
            if clean_query:
                url += "?" + urllib.parse.urlencode(clean_query)

        data = None
        headers = {
            "Accept": "application/json",
            "X-Bridge-API-Key": self.api_key,
        }
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                payload = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            raise APIError(exc.code, payload, self.api_key) from exc

        parsed = json.loads(payload or "{}")
        if not isinstance(parsed, dict):
            raise APIError(200, "response is not a JSON object", self.api_key)
        return parsed

    def capabilities(self) -> Dict[str, Any]:
        return self.request_json("GET", "/api/v1/capabilities")

    def messages(
        self,
        *,
        after_id: Optional[int] = None,
        before_id: Optional[int] = None,
        limit: int = 100,
        device: Optional[str] = None,
        wxid: Optional[str] = None,
        chat_id: Optional[str] = None,
        chat_kind: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.request_json(
            "GET",
            "/api/v1/messages",
            query={
                "after_id": after_id,
                "before_id": before_id,
                "limit": limit,
                "device": device,
                "wxid": wxid,
                "chat_id": chat_id,
                "chat_kind": chat_kind,
            },
        )

    def iter_messages(self, *, after_id: int = 0, limit: int = 100, max_pages: int = 1) -> Iterator[Dict[str, Any]]:
        cursor = after_id
        pages = 0
        while True:
            data = self.messages(after_id=cursor, limit=limit)
            pages += 1
            for item in data.get("messages") or []:
                if isinstance(item, dict):
                    yield item
            next_cursor = data.get("next_cursor")
            if isinstance(next_cursor, int):
                cursor = next_cursor
            if not data.get("has_more") or pages >= max_pages:
                return

    def contacts(self, *, query: str = "", limit: int = 100, include_deleted: bool = False) -> Dict[str, Any]:
        return self.request_json(
            "GET",
            "/api/v1/contacts",
            query={"q": query, "limit": limit, "include_deleted": str(include_deleted).lower() if include_deleted else None},
        )

    def modules_status(self) -> Dict[str, Any]:
        return self.request_json("GET", "/api/v1/modules/status")

    def send_text(self, target_wxid: str, text: str) -> Dict[str, Any]:
        return self.request_json("POST", "/api/v1/messages/text", body={"wx_ids": [target_wxid], "text": text})

    def send_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.request_json("POST", "/api/v1/messages/action", body=payload)

    def outbox(self, outbox_id: int) -> Dict[str, Any]:
        return self.request_json("GET", f"/api/v1/outbox/{outbox_id}")

    def poll_outbox(self, outbox_id: int, timeout: int = 30, interval: float = 2.0) -> Dict[str, Any]:
        deadline = time.monotonic() + timeout
        last: Dict[str, Any] = {}
        while True:
            data = self.outbox(outbox_id)
            outbox = data.get("outbox") or {}
            if isinstance(outbox, dict):
                last = outbox
                if outbox.get("status") in FINAL_OUTBOX_STATUSES:
                    return data
            if time.monotonic() >= deadline:
                return data if data else {"outbox": last}
            time.sleep(interval)

    def media_bytes(self, media_url: str, timeout: Optional[int] = None) -> bytes:
        """Download bytes from a `/api/media/...` URL using this API key scope."""
        if not media_url.startswith("/api/media/"):
            raise ValueError("media_url must start with /api/media/")
        req = urllib.request.Request(
            self.base_url + media_url,
            headers={"X-Bridge-API-Key": self.api_key},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            raise APIError(exc.code, payload, self.api_key) from exc

    def ws_url(self, replay: int = 0) -> str:
        parsed = urllib.parse.urlsplit(self.base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        prefix = parsed.path.rstrip("/")
        query = urllib.parse.urlencode({"api_key": self.api_key, "replay": replay})
        return urllib.parse.urlunsplit((scheme, parsed.netloc, prefix + "/api/v1/ws", query, ""))


def redact_text(value: Any, api_key: str = "") -> str:
    if not isinstance(value, str):
        return ""
    redacted = value
    if api_key:
        redacted = redacted.replace(api_key, "<api-key>")
    redacted = re.sub(r"api_key=[^&\s\"]+", "api_key=<redacted>", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"wxid_[A-Za-z0-9_-]+", "<wxid>", redacted)
    redacted = re.sub(r"[A-Za-z0-9_-]+@chatroom", "<chatroom>", redacted)
    redacted = re.sub(r"(password|token|secret|cookie|credential)=([^&\s\"]+)", r"\1=<redacted>", redacted, flags=re.IGNORECASE)
    return redacted


def safe_len(value: Any) -> int:
    return len(value) if isinstance(value, str) else 0


def message_summary(message: Dict[str, Any]) -> Dict[str, Any]:
    media = message.get("media") or []
    appmsg = message.get("appmsg") or {}
    unsupported = message.get("unsupported") or []
    return {
        "id": message.get("id") or message.get("event_id"),
        "kind": message.get("kind"),
        "direction": message.get("direction"),
        "chat_kind": message.get("chat_kind"),
        "text_len": safe_len(message.get("text")),
        "media_count": len(media) if isinstance(media, list) else 0,
        "appmsg_type": appmsg.get("type") if isinstance(appmsg, dict) else None,
        "appmsg_subtype": appmsg.get("subtype") if isinstance(appmsg, dict) else None,
        "appmsg_title_present": bool(appmsg.get("title")) if isinstance(appmsg, dict) else False,
        "unsupported_count": len(unsupported) if isinstance(unsupported, list) else 0,
    }


def message_summary_line(message: Dict[str, Any]) -> str:
    summary = message_summary(message)
    parts = [
        f"id={summary['id']}",
        f"kind={summary['kind']}",
        f"direction={summary['direction']}",
        f"chat_kind={summary['chat_kind']}",
        f"text_len={summary['text_len']}",
        f"media_count={summary['media_count']}",
    ]
    if summary["appmsg_type"] or summary["appmsg_subtype"] or summary["appmsg_title_present"]:
        parts.append(f"appmsg_type={summary['appmsg_type'] or ''}")
        parts.append(f"appmsg_subtype={summary['appmsg_subtype'] or ''}")
        parts.append(f"appmsg_title_present={summary['appmsg_title_present']}")
    if summary["unsupported_count"]:
        parts.append(f"unsupported_count={summary['unsupported_count']}")
    return " ".join(parts)


def outbox_summary_line(data: Dict[str, Any], api_key: str = "") -> str:
    outbox = data.get("outbox") or {}
    if not isinstance(outbox, dict):
        outbox = {}
    media = outbox.get("media") or []
    return " ".join(
        [
            f"outbox_id={outbox.get('id') or data.get('outbox_id')}",
            f"kind={outbox.get('kind') or data.get('kind')}",
            f"status={outbox.get('status')}",
            f"media_count={len(media) if isinstance(media, list) else 0}",
            f"target_present={bool(outbox.get('target_wxid'))}",
            f"last_error={redact_text(outbox.get('last_error') or '', api_key)}",
        ]
    )
