# Python Adapter Example

最小外部适配器示例，走 `/api/v1` 公开协议，不依赖手机模块私有接口。默认输出会隐藏完整 wxid、群 ID 和聊天正文，只打印结构摘要。

## Client 用法

```python
from wechat_observatory_client import WechatObservatoryClient, message_summary_line

client = WechatObservatoryClient("http://127.0.0.1:8088", "<your-api-key>")

capabilities = client.capabilities()
for message in client.iter_messages(after_id=0, limit=20):
    print(message_summary_line(message))

queued = client.send_text("<target-wxid-or-room-id>", "hello")
status = client.poll_outbox(queued["outbox_id"], timeout=30)
```

## CLI 用法

```bash
export WECHAT_OBSERVATORY_BASE_URL="http://127.0.0.1:8088"
export WECHAT_OBSERVATORY_API_KEY="<your-api-key>"

python3 examples/python/adapter_quickstart.py capabilities
python3 examples/python/adapter_quickstart.py status
python3 examples/python/adapter_quickstart.py sync --after-id 0 --limit 20
python3 examples/python/adapter_quickstart.py send-text --target "<target-wxid-or-room-id>" --text "hello" --wait
```

`status` 应至少看到一个 `runtime_status=ready` 的模块。否则通常是 API Key 绑定的设备和正在运行的手机模块不一致，先修正设备绑定再同步消息或发送。

WebSocket 示例需要可选依赖：

```bash
python3 -m pip install websocket-client
python3 examples/python/adapter_quickstart.py watch --replay 0
```

不要把真实 API Key、wxid、聊天内容、媒体 base64 或原始 XML 写入日志和公开示例。
