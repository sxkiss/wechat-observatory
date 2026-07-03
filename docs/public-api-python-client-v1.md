# Public API Python Client v1

`examples/python/wechat_observatory_client.py` 是一个最小 Python 客户端，给外部适配器作者参考。它只依赖 Python 标准库，目标是展示协议调用方式，不是完整发布版 SDK。

## 初始化

```python
from wechat_observatory_client import WechatObservatoryClient

client = WechatObservatoryClient(
    "http://127.0.0.1:8088",
    "<your-api-key>",
)
```

## 能力发现

```python
capabilities = client.capabilities()
for item in capabilities["capabilities"]:
    print(item["kind"], item["outbound_status"])
```

## 可靠收消息

```python
cursor = 0
while True:
    page = client.messages(after_id=cursor, limit=100)
    for message in page["messages"]:
        handle(message)
    if page.get("next_cursor"):
        cursor = page["next_cursor"]
    if not page.get("has_more"):
        break
```

WebSocket 只做实时体验；断线后仍然用 `after_id` 补拉。

## 发文本并等待 ACK

```python
queued = client.send_text("<target-wxid-or-room-id>", "hello")
status = client.poll_outbox(queued["outbox_id"], timeout=30)

if status["outbox"]["status"] == "sent":
    print("sent")
else:
    print(status["outbox"].get("last_error"))
```

发送接口返回 `ok=true` 只代表已入队，不能当成微信真实发送完成。真实结果以 outbox 的 `sent` 或 `failed` 为准。

## 下载媒体

```python
for message in client.iter_messages(after_id=0, limit=20):
    for media in message.get("media") or []:
        blob = client.media_bytes(media["url"])
        print(media.get("kind"), len(blob))
```

`/api/media/...` 使用同一个 API Key 鉴权，服务端会按设备隔离媒体路径。

## 安全边界

- 不打印真实 API Key、wxid、群 ID、聊天正文、raw XML、media base64。
- 目标只传 wxid 或 room id，不传昵称。
- `payment` 和 `system` 是只读识别，不提供出站自动化。
- 运行时能力以 `GET /api/v1/capabilities` 为准。
