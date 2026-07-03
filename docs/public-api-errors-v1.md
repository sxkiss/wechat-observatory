# Public API Errors v1

本文档记录外部适配器应稳定处理的 `/api/v1` 错误码。响应结构通常为：

```json
{
  "ok": false,
  "code": "error_code",
  "error": "human readable message"
}
```

适配器应该优先判断 `code`，不要依赖英文错误文案。

## 鉴权和范围

| code | HTTP | 含义 | 适配器动作 |
| --- | --- | --- | --- |
| `unauthorized` | 401 | 没有管理密码或 API Key，或凭据无效。 | 停止重试，检查配置。 |
| `device_forbidden` | 403 | API Key 访问了非绑定设备。 | 停止重试，修正 device 或 API Key。 |
| `owner_wxid_forbidden` | 403 | API Key 请求了非当前登录账号。 | 停止重试，等待正确设备/账号或修正请求。 |
| `owner_wxid_unbound` | 409 | 绑定设备还没有完成模块注册，服务端不知道当前登录 wxid。 | 稍后重试，提示检查手机模块是否 ready。 |
| `media_forbidden` | 403 | API Key 读取了其他设备的媒体路径。 | 停止重试，不要跨设备读媒体。 |

## 请求校验

| code | HTTP | 含义 | 适配器动作 |
| --- | --- | --- | --- |
| `invalid_json` | 400 | 请求体不是合法 JSON。 | 修正调用方。 |
| `send_failed` | 400 | 出站请求字段不满足当前 kind 的校验规则。 | 根据错误和 capabilities 修正请求。 |
| `kind_mismatch` | 400 | 具体类型接口和请求体 kind 不一致。 | 使用匹配接口或改用 `/api/v1/messages/action`。 |
| `cursor_conflict` | 400 | `after_id` 和 `before_id` 同时传入。 | 二选一；同步用 `after_id`，历史翻页用 `before_id`。 |
| `invalid_cursor` | 400 | cursor 不是非负整数。 | 修正 cursor 存储。 |
| `invalid_outbox_id` | 400 | outbox id 不是正整数。 | 修正调用方。 |
| `invalid_media_path` | 400 | 媒体路径为空或路径非法。 | 只使用消息 envelope 返回的 `/api/media/...`。 |

## 资源状态

| code | HTTP | 含义 | 适配器动作 |
| --- | --- | --- | --- |
| `outbox_not_found` | 404 | outbox 不存在，或被 API Key 设备范围隐藏。 | 停止轮询，检查 outbox_id 和 API Key。 |
| `media_not_found` | 404 | 媒体文件不存在。 | 可短暂重试；持续失败则标记缺失。 |
| `admin_read_failed` | 500 | 服务端读取存储失败。 | 指数退避重试并告警。 |
| `outbox_read_failed` | 500 | 服务端读取 outbox 失败。 | 指数退避重试并告警。 |

## 出站 ACK 语义

发送接口返回 `ok=true` 只代表任务已入队。适配器必须继续查询 `status_url` 或 `/api/v1/outbox/{id}`：

| status | 含义 | 适配器动作 |
| --- | --- | --- |
| `pending` / `queued` | 任务等待手机模块消费。 | 继续轮询，设置超时。 |
| `leased` | 手机模块已领取，等待 ACK。 | 继续轮询，设置超时。 |
| `sent` | 手机模块确认已执行。 | 标记成功。 |
| `failed` | 手机模块确认失败。 | 读取 `last_error`，按业务重试或失败。 |

## 不应自动重试的场景

- `unauthorized`
- `device_forbidden`
- `owner_wxid_forbidden`
- `media_forbidden`
- `kind_mismatch`
- 请求字段缺失导致的 `send_failed`

## 可以短暂重试的场景

- `owner_wxid_unbound`：模块刚重启或刚换号时。
- 5xx：服务端暂时性错误。
- outbox 中间态超时前的轮询。
