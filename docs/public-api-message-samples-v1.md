# Public API Message Samples v1

本文档是外部适配器的消息样例索引。运行时事实以
`GET /api/v1/capabilities` 为准；这里的 JSON fixture 是脱敏后的稳定
结构样例，用来说明 `MessageEnvelope v1`、发送请求和 outbox ACK 的形状。

## Fixture Directory

`docs/message-fixtures/public-api-v1/`

入口文件：

- `index.json`：列出全部 fixture。
- `public-api-v1.<kind>.json`：每种消息或子类型的完整脱敏样例。

## 使用方式

1. 先调用 `GET /api/v1/capabilities` 确认当前能力和字段契约。
2. 再读取本目录 fixture，按 `inbound_envelope` 适配入站解析。
3. 发送时参考 `outbound_request`，但发送目标必须替换成真实 wxid 或群 room id。
4. 发送接口返回只代表 queued；继续用 `status_url` 查询到 `sent` 或 `failed`。

所有 fixture 都遵守这些规则：

- 不包含真实 wxid、群 id、API key、token、cookie、聊天原文、raw XML 或媒体 base64。
- 入站样例只使用公开信封字段：`media[]`、`appmsg`、`location` 等。
- `media_url`、`location_latitude` 这类字段只会出现在出站请求里，不会出现在 `inbound_envelope` 顶层。
- `chat_display_name` 只用于展示，不能作为发送目标。

## MessageEnvelope v1 Shape

| 区域 | 字段 | 说明 |
| --- | --- | --- |
| 基础 | `id`, `device`, `owner_wxid`, `direction`, `kind`, `subtype` | 适配器路由和去重的核心字段。 |
| 会话 | `chat_id`, `chat_kind`, `from_wxid`, `to_wxid`, `room_id`, `sender_wxid` | `chat_id` 是稳定会话 ID；群聊实际发送者看 `sender_wxid`。 |
| 媒体 | `media[]` | 每项包含 `kind`, `mime`, `name`, `url`, `size`, `opaque`。 |
| 卡片 | `appmsg` | 链接、小程序、文件、引用、聊天记录、表情结构字段。 |
| 位置 | `location` | 经纬度、缩放、POI、展示文本。 |
| 证据 | `evidence`, `unsupported` | 解析来源和明确降级项。适配器必须容忍未知项。 |

## 样例索引

| Fixture | 入站重点字段 | 出站 | 当前状态 | 适配提示 |
| --- | --- | --- | --- | --- |
| `public-api-v1.text.json` | `kind=text`, `text` | `POST /api/v1/messages/text` | stable | 目标只传 wxid 或 room id。 |
| `public-api-v1.image.json` | `media[0].kind=image`, `media[0].url` | `POST /api/v1/messages/image` | stable | 下载媒体要使用同一 API Key 权限。 |
| `public-api-v1.video.json` | `kind=video`, `message_type=43/62`, `media[]` | `POST /api/v1/messages/video` | stable | 不要依赖原始 type，优先按 `kind=video` 处理。 |
| `public-api-v1.voice.json` | `kind=voice`, `media[].mime=audio/amr` 或 `audio/silk` | `POST /api/v1/messages/voice` | stable | 已验证可听音频；继续兼容更多 AMR/SILK 变体。 |
| `public-api-v1.file.json` | `kind=file`, `appmsg.subtype=file`, `media[]` | `POST /api/v1/messages/file` | stable | 发送文件建议总是带 `media_name`。 |
| `public-api-v1.emoji.json` | `kind=emoji`, `appmsg.title`, `appmsg.url`, `media[].opaque` | `POST /api/v1/messages/emoji` | structured/stable | 表情稳定源是 MD5/CDN；本地 media 可能不可直接预览。 |
| `public-api-v1.location.json` | `location.latitude`, `location.longitude`, `location.label` | `POST /api/v1/messages/location` | stable | 示例坐标是合成值，不要记录真实隐私位置。 |
| `public-api-v1.quote.json` | `appmsg.subtype=quote`, `message_type=822083633` | `POST /api/v1/messages/quote` | sample-only | 引用元数据不完整时应失败并给出原因。 |
| `public-api-v1.link.json` | `appmsg.subtype=link`, `appmsg.title`, `appmsg.url` | `POST /api/v1/messages/link` | stable | 支持 source 转发或直接构造网页卡片。 |
| `public-api-v1.mini-program.json` | `appmsg.subtype=mini_program`, `appmsg.type=33/36` | `POST /api/v1/messages/mini-program` | source-forward stable | 源消息转发更稳，直接构造仍需更多样本。 |
| `public-api-v1.chat-history.json` | `kind=chat_history`, `appmsg.type=19` | `POST /api/v1/messages/chat-history` | forwarding-only | 不开放任意 raw XML 自动化。 |
| `public-api-v1.payment.json` | `kind=payment`, `subtype=transfer/red_packet`, `unsupported[]` | no | parse-only | 红包/转账只做识别和脱敏，不做出站。 |
| `public-api-v1.system.json` | `kind=system`, `message_type=10000` | no | parse-only | 默认不进入业务自动化。 |
| `public-api-v1.unknown.json` | `kind=unknown`, `message_type`, `unsupported[]` | no | preserved | 只保留证据，不猜测业务含义。 |

## 发送和 ACK 样例

发送文本：

```json
{
  "wx_ids": ["<target>"],
  "text": "<text>"
}
```

入队响应：

```json
{
  "ok": true,
  "protocol_version": "v1",
  "kind": "text",
  "outbox_id": 1001,
  "status_url": "/api/v1/outbox/1001",
  "outbox": {
    "id": 1001,
    "device": "<device>",
    "owner_wxid": "<owner>",
    "target_wxid": "<target>",
    "kind": "text",
    "status": "pending"
  }
}
```

终态响应：

```json
{
  "ok": true,
  "protocol_version": "v1",
  "outbox": {
    "id": 1001,
    "kind": "text",
    "status": "sent",
    "chat_record_id": 90001
  }
}
```

失败时读取 `outbox.last_error`，不要把 queued 响应当成真正发送成功。

## Validation

运行：

```bash
python3 scripts/validate_public_api_fixtures.py
python3 scripts/test_public_api_fixtures.py
```

校验内容包括：

- JSON 语法和 fixture/index 一致性。
- 必要字段：`id`, `device`, `direction`, `kind`, `message_type`, `chat_id`, `chat_kind`。
- 禁止敏感字段：API key、token、cookie、password、raw XML、media base64 等。
- 禁止真实 wxid 或群 room id。
- 入站 `inbound_envelope` 禁止旧扁平字段，必须使用 `media[]`、`appmsg`、`location`。
