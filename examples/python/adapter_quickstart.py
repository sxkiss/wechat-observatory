#!/usr/bin/env python3
"""Minimal wechat-observatory public API v1 adapter example.

This is an integration example, not a production SDK. It never prints the API
key, raw XML, media base64, full message bodies, or full wxid/chatroom IDs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

from wechat_observatory_client import (
    APIError,
    WechatObservatoryClient,
    message_summary_line,
    outbox_summary_line,
)

BASE_URL = os.environ.get("WECHAT_OBSERVATORY_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
API_KEY = os.environ.get("WECHAT_OBSERVATORY_API_KEY", "")


def make_client() -> WechatObservatoryClient:
    if not API_KEY:
        raise SystemExit("Set WECHAT_OBSERVATORY_API_KEY before calling the API.")
    return WechatObservatoryClient(BASE_URL, API_KEY)


def print_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_capabilities(_: argparse.Namespace) -> None:
    print_json(make_client().capabilities())


def cmd_status(_: argparse.Namespace) -> None:
    data = make_client().modules_status()
    modules = [item for item in data.get("modules") or [] if isinstance(item, dict)]
    ready = sum(1 for item in modules if item.get("runtime_status") == "ready")
    print(f"module_count={len(modules)} ready_count={ready}")
    for index, module in enumerate(modules, 1):
        print(
            " ".join(
                [
                    f"module={index}",
                    f"runtime_status={module.get('runtime_status') or ''}",
                    f"device_present={bool(module.get('device'))}",
                    f"owner_wxid_present={bool(module.get('device_wxid'))}",
                    f"last_event_present={bool(module.get('last_event_at') or module.get('last_inbound_at') or module.get('last_poll_at'))}",
                ]
            )
        )


def cmd_sync(args: argparse.Namespace) -> None:
    client = make_client()
    cursor = args.after_id
    pages = 0
    while True:
        data = client.messages(after_id=cursor, limit=args.limit)
        pages += 1
        for message in data.get("messages") or []:
            if isinstance(message, dict):
                print(message_summary_line(message))
        next_cursor = data.get("next_cursor")
        if isinstance(next_cursor, int):
            cursor = next_cursor
        if not data.get("has_more") or pages >= args.max_pages:
            break
    print(f"next_cursor={cursor}")


def cmd_send_text(args: argparse.Namespace) -> None:
    client = make_client()
    data = client.send_text(args.target, args.text)
    outbox_id = data.get("outbox_id")
    print(f"queued kind={data.get('kind')} outbox_id={outbox_id} status_url={data.get('status_url')}")
    if args.wait and isinstance(outbox_id, int):
        print(outbox_summary_line(client.poll_outbox(outbox_id, timeout=args.timeout), API_KEY))


def cmd_outbox(args: argparse.Namespace) -> None:
    print(outbox_summary_line(make_client().outbox(args.outbox_id), API_KEY))


def cmd_watch(args: argparse.Namespace) -> None:
    try:
        import websocket  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit("watch requires websocket-client: python -m pip install websocket-client") from exc

    client = make_client()
    ws = websocket.create_connection(client.ws_url(args.replay), timeout=30)
    try:
        while True:
            raw = ws.recv()
            data = json.loads(raw)
            event_type = data.get("type")
            if event_type == "message" and isinstance(data.get("event"), dict):
                print(message_summary_line(data["event"]))
            else:
                print(f"ws type={event_type} protocol={data.get('protocol_version')}")
    finally:
        ws.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal wechat-observatory public API v1 adapter.")
    sub = parser.add_subparsers(dest="command", required=True)

    capabilities = sub.add_parser("capabilities", help="Print /api/v1/capabilities.")
    capabilities.set_defaults(func=cmd_capabilities)

    status = sub.add_parser("status", help="Print the module status visible to this API key.")
    status.set_defaults(func=cmd_status)

    sync = sub.add_parser("sync", help="Pull messages with after_id cursor.")
    sync.add_argument("--after-id", type=int, default=0)
    sync.add_argument("--limit", type=int, default=100)
    sync.add_argument("--max-pages", type=int, default=1)
    sync.set_defaults(func=cmd_sync)

    send_text = sub.add_parser("send-text", help="Queue a text message.")
    send_text.add_argument("--target", required=True, help="Target wxid or room id, never a display name.")
    send_text.add_argument("--text", required=True)
    send_text.add_argument("--wait", action="store_true", help="Poll the outbox until sent or failed.")
    send_text.add_argument("--timeout", type=int, default=30)
    send_text.set_defaults(func=cmd_send_text)

    outbox = sub.add_parser("outbox", help="Read one outbox item as a redacted summary.")
    outbox.add_argument("outbox_id", type=int)
    outbox.set_defaults(func=cmd_outbox)

    watch = sub.add_parser("watch", help="Watch /api/v1/ws. Requires websocket-client.")
    watch.add_argument("--replay", type=int, default=0)
    watch.set_defaults(func=cmd_watch)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except APIError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
