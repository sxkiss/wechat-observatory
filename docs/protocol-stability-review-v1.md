# Protocol Stability Review v1

本文档记录当前 `/api/v1` 外部协议面的稳定性评审结果。目标是让外部机器人框架和业务适配器只依赖公开协议，不直接接手机模块私有接口。

## 结论

当前方向是可行的：Go 网关继续作为公开协议面，Android 模块作为微信能力执行器，外部系统只需要适配 `/api/v1`、`/api/media/...` 和 WebSocket。这样项目不会变成重网关，也保留了后续接 AllBot、插件或其他框架的空间。

本轮评审确认：

- `MessageEnvelope v1` 已经能覆盖文本、图片、视频、语音、文件、表情、位置、引用、链接、小程序、聊天记录、支付只读识别和未知类型降级。
- 出站协议统一到 Action Outbox，公开发送接口返回 `PublicSendResponse`，真实结果以 outbox ACK 为准。
- HTTP cursor 补拉和 WebSocket 实时可以组成可靠消费模型：`after_id` 做正向补拉，`before_id` 做历史翻页。
- 外部适配器不需要接 `/module/...`；该路径继续保留给手机模块。

## 本轮修复

### API Key 发送必须等待当前 owner_wxid

问题：API Key 发送允许省略 `device` 和 `owner_wxid`，但如果服务端还不知道该设备当前登录微信账号，旧逻辑可能创建 `owner_wxid` 为空的 outbox。

处理：`POST /api/v1/messages/...` 在 API Key 鉴权下会先读取绑定设备当前 `owner_wxid`。如果为空，返回：

```json
{
  "ok": false,
  "code": "owner_wxid_unbound"
}
```

效果：不会绕过当前登录账号校验。设备完成模块注册后，适配器仍然可以省略 `device` 和 `owner_wxid`。

### /api/media 支持外部 API Key 读取

问题：公开消息信封返回 `/api/media/...`，文档也要求外部适配器依赖该地址，但旧路由只接受管理密码，API Key 适配器无法下载媒体。

处理：`GET /api/media/...` 改为 public auth：

- 管理密码可以读取所有媒体，用于管理台。
- API Key 只能读取自己绑定设备目录下的媒体。
- 跨设备媒体路径返回 `media_forbidden`。

这让“入站媒体 URL -> 外部适配器下载”闭环成立，同时不放开跨设备读取。

## 稳定协议面

| 区域 | 当前状态 | 说明 |
| --- | --- | --- |
| 鉴权 | stable | 外部优先 `X-Bridge-API-Key`，也支持 `Authorization: Bearer`；WebSocket 可用 `api_key` 查询参数。 |
| 能力发现 | stable | `GET /api/v1/capabilities` 是适配器启动的第一步。 |
| 消息补拉 | stable | `GET /api/v1/messages?after_id=<id>` 返回升序新消息和 `next_cursor`。 |
| 历史翻页 | stable | `before_id` 用于旧消息倒序分页，不和 `after_id` 混用。 |
| 实时消息 | stable | `GET /api/v1/ws` 推送 `hello`、`message`、`replay`、`ping/pong`。 |
| 媒体读取 | stable | `/api/media/...` 现在支持 public auth，并按设备隔离。 |
| 发送状态 | stable | `GET /api/v1/outbox/{id}` 返回公开 outbox envelope，不暴露 `payload_json` 和 `api_key`。 |
| 手机模块协议 | internal | `/module/...` 不作为外部适配器协议。 |

## 仍需谨慎的边界

- `voice`：协议和出站链路已实现，但播放时长、编码和更多真实样本还需要补。
- `quote`：私聊基础可用，群聊引用还需要更多样本，特别是引用元消息元数据不完整时。
- `mini_program`：源消息转发更稳，直接构造仍依赖更多真实样本。
- `chat_history`：协议支持 `recorditem_xml` 和来源消息 ID，但任意 XML 构造风险高，外部适配器默认应优先源消息转发。
- `payment`：红包、转账只做只读识别和脱敏，不提供出站自动化。

## 适配器推荐实现

1. 调 `GET /api/v1/capabilities` 读取能力矩阵。
2. 用 `GET /api/v1/messages?after_id=0&limit=100` 做首次补拉。
3. 业务处理成功后再保存 `next_cursor`。
4. 连接 `GET /api/v1/ws` 做实时消息。
5. WebSocket 断线后，从最后成功处理的 cursor 补拉，再重连。
6. 发送消息后只把“已入队”当作中间态，继续查询 `/api/v1/outbox/{id}` 直到 `sent` 或 `failed`。

## 安全规则

- 不在日志、文档、示例里输出真实 API Key、wxid、群 ID、聊天正文、媒体 base64、raw XML、cookie 或 token。
- 外部接口不得返回 `api_key`、`raw_xml`、`media_base64`、`raw_provider`、`payload_json`。
- API Key 只能访问绑定设备的数据和媒体。
- 发送目标必须是稳定 ID：好友 wxid 或群 room id，不能用昵称或群名。
