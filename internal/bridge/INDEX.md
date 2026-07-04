<!-- AUTO-DOC: Update me when files in this folder change -->

# Bridge

Bridge 层实现模块注册、消息接入、公开 API 和 outbox 调度。当前 outbox 同时覆盖 HTTP 轮询和 WebSocket 唤醒，并对批量租约做统一限流、lane-aware 分发，以及基于已观测出站消息的文本重试去重与 failed ACK 短观察窗口纠偏，兼容事件时间与存储时间偏差；公开 v1 API 现额外暴露实验性的 `revoke` 撤回动作。

## Files

| File | Role | Function |
|------|------|----------|
| events.go | Contract | 定义消息事件、发送请求校验和 module outbox DTO，含实验性 `revoke` kind |
| http.go | Transport | 注册 admin/public/module HTTP 路由，含 `/api/v1/messages/revoke` |
| outbox.go | Storage | 提供内存 outbox 和 lane-aware 租约选择 |
| outbox_lane.go | Utility | 复用 `wxid + kind` lane 的批量租约选择算法 |
| public_api.go | Transport | 暴露公开 v1 发送/查询接口与能力矩阵，标注 `revoke` 为实验能力 |
| service.go | Core | 维护设备/API Key 状态、裁剪模块 outbox 批次并拦截已观测文本重试/误失败 ACK |
| openapi.go | Docs | 内嵌公开协议文档和 OpenAPI JSON，覆盖新增撤回接口 |
| outbox_ws.go | Transport | 处理模块 outbox WebSocket 的 wake、poll 和 ack |
