# API

`wechat-observatory` 有两类 API：

- 管理 API：Web 管理台使用，认证头是 `X-Bridge-Password`。
- 模块 API：手机 LSPosed 模块使用，认证凭据是 API Key。

示例中的服务地址使用：

```text
http://127.0.0.1:8088
```

## 外部适配器接入

外部系统、机器人框架和插件作者优先阅读：

- [Adapter Quickstart v1](adapter-quickstart-v1.md)：推荐接入流程、cursor 补拉、WebSocket 实时消息、发送 ACK 和安全规则。
- [Capability Evidence v1](capability-evidence-v1.md)：每个消息能力当前状态、真实样本证据和升级缺口。
- [Protocol Stability Review v1](protocol-stability-review-v1.md)：公开协议稳定面、媒体读取、owner_wxid 校验和后续风险边界。
- [Public API Errors v1](public-api-errors-v1.md)：公开错误码、重试策略和 outbox ACK 状态语义。
- [Public API Message Samples v1](public-api-message-samples-v1.md)：text/image/video/file/voice/emoji/location/link/mini-program/chat-history/payment 等标准 JSON 样例。
- [Public API Python Client v1](public-api-python-client-v1.md)：最小 Python Client 封装，演示 capabilities、消息补拉、发送 ACK 和媒体下载。
- `GET /api/v1/capabilities`：运行时能力发现，适配器应根据该接口判断当前可用的消息类型和传输方式。
- `GET /docs/openapi.json`：OpenAPI 结构，适合生成客户端或做接口校验。
- `python3 scripts/public_api_contract_check.py`：公开协议验收套件，默认只读检查 capabilities、messages、WebSocket、media、OpenAPI；真实发送必须显式加 `--confirm-send`。

外部适配器应只依赖 `/api/v1` 和 `/api/media/...`。`/module/...` 是手机模块内部协议，`/api/send/...` 是旧管理兼容接口，新接入不建议使用。

## 管理认证

```bash
curl -H "X-Bridge-Password: your-admin-password" \
  http://127.0.0.1:8088/api/modules/status
```

也支持 `?password=...`，但不建议在生产环境使用 URL 参数传密码。

## API Key 管理

列出：

```bash
curl -H "X-Bridge-Password: your-admin-password" \
  http://127.0.0.1:8088/api/api-keys
```

创建：

```bash
curl -X POST \
  -H "X-Bridge-Password: your-admin-password" \
  -H "Content-Type: application/json" \
  -d '{"api_key":"","device":"phone-a","nickname":"Front Desk Phone"}' \
  http://127.0.0.1:8088/api/api-keys
```

`api_key` 留空时，服务端自动生成。

停用：

```bash
curl -X POST \
  -H "X-Bridge-Password: your-admin-password" \
  http://127.0.0.1:8088/api/api-keys/<api-key>/disable
```

启用：

```bash
curl -X POST \
  -H "X-Bridge-Password: your-admin-password" \
  http://127.0.0.1:8088/api/api-keys/<api-key>/enable
```

删除：

```bash
curl -X DELETE \
  -H "X-Bridge-Password: your-admin-password" \
  http://127.0.0.1:8088/api/api-keys/<api-key>
```

删除 API Key 后，对应模块身份会注销。手机端继续使用旧 API Key 时不会重新注册成功。

## 设备管理

修改设备显示名：

```bash
curl -X POST \
  -H "X-Bridge-Password: your-admin-password" \
  -H "Content-Type: application/json" \
  -d '{"name":"phone-a","nickname":"Front Desk Phone"}' \
  http://127.0.0.1:8088/api/devices
```

设备名和显示名由 Web 管理端管理，手机模块不能改名。

## 消息查询

```bash
curl -H "X-Bridge-Password: your-admin-password" \
  "http://127.0.0.1:8088/api/messages?device=phone-a&limit=50"
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `device` | 设备名 |
| `owner_wxid` | 当前登录微信账号，省略时默认当前设备绑定 |
| `wxid` | 对话对象或群聊 ID |
| `limit` | 返回数量 |

## 管理端发送接口

```bash
curl -X POST \
  -H "X-Bridge-Password: your-admin-password" \
  -H "Content-Type: application/json" \
  -d '{"device":"phone-a","owner_wxid":"wxid_current_login","wx_ids":["wxid_friend"],"text":"hello"}' \
  http://127.0.0.1:8088/api/send/text
```

`/api/send/text` 是旧管理兼容接口，会写入 `kind=text` 的 Action Outbox 任务。`owner_wxid` 必填，用于防止浏览器停留在旧账号状态时，把消息发到切换后的微信账号里。

管理端也可以直接创建 Action Outbox v1 任务：

```bash
curl -X POST \
  -H "X-Bridge-Password: your-admin-password" \
  -H "Content-Type: application/json" \
  -d '{"device":"phone-a","owner_wxid":"wxid_current_login","wx_ids":["wxid_friend"],"kind":"image","media_url":"http://127.0.0.1:8088/api/media/example.jpg","media_name":"example.jpg","media_mime":"image/jpeg"}' \
  http://127.0.0.1:8088/api/send/action
```

外部系统不要依赖管理密码接口，推荐使用 `/api/v1/messages/{kind}` 和 `/api/v1/outbox/{id}`。

## 实时事件

```bash
curl -N -H "X-Bridge-Password: your-admin-password" \
  http://127.0.0.1:8088/api/live/events
```

管理台用该接口实时刷新模块状态和消息。

## 模块注册

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"api_key":"dev_key_001","device":"","wxid":"wxid_current_login","nickname":"Current WeChat"}' \
  http://127.0.0.1:8088/module/register
```

服务端以 API Key 为准，`device` 会被 Web 绑定覆盖。

## 模块上报消息

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"api_key":"dev_key_001","from":"wxid_friend","to":"wxid_current_login","text":"hello","message_type":1,"direction":"recv","chat_id":"wxid_friend","chat_kind":"direct"}' \
  http://127.0.0.1:8088/webhook/lsposed/message
```

群聊建议带：

```json
{
  "room_id": "12345@chatroom",
  "sender": "wxid_member",
  "chat_id": "12345@chatroom",
  "chat_kind": "room"
}
```

## 模块同步联系人

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"api_key":"dev_key_001","wxid":"wxid_current_login","complete":true,"contacts":[{"wxid":"filehelper","nickname":"文件传输助手","chatroom":false}]}' \
  http://127.0.0.1:8088/module/contacts/snapshot
```

## 模块出站队列

WebSocket：

```text
GET /module/outbox/ws?api_key=<api-key>&device=<device>&wxid=<current-wxid>
```

HTTP 轮询：

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"api_key":"dev_key_001","device":"phone-a","wxid":"wxid_current_login","limit":1}' \
  http://127.0.0.1:8088/module/outbox/poll
```

ACK：

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"api_key":"dev_key_001","device":"phone-a","items":[{"id":1,"status":"sent"}]}' \
  http://127.0.0.1:8088/module/outbox/ack
```
