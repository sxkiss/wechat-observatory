<!-- AUTO-DOC: Update me when files in this folder change -->

# Bridge

Bridge 层实现模块注册、消息接入、公开 API 和 outbox 调度。当前 outbox 同时覆盖 HTTP 轮询和 WebSocket 唤醒，并对批量租约做统一限流与 lane-aware 分发。

## Files

| File | Role | Function |
|------|------|----------|
| outbox.go | Storage | 提供内存 outbox 和 lane-aware 租约选择 |
| outbox_lane.go | Utility | 复用 `wxid + kind` lane 的批量租约选择算法 |
| service.go | Core | 维护设备/API Key 状态并裁剪模块 outbox 批次 |
| outbox_ws.go | Transport | 处理模块 outbox WebSocket 的 wake、poll 和 ack |
