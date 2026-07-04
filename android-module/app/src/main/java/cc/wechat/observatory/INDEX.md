<!-- AUTO-DOC: Update me when files in this folder change -->

# Observatory Module

该目录承载 Android 侧微信适配逻辑和配置入口。发送链路现在支持按 `wxid + kind` 分 lane 并发执行，同时保留同 lane 顺序发送；另增加实验性的 `revoke` 出站分支，优先按本地 `message` 表记录触发微信撤回事件。

## Files

| File | Role | Function |
|------|------|----------|
| HookEntry.java | Runtime | Hook 微信数据库、上传消息并调度 outbox 并发发送与实验性撤回 |
| SettingsActivity.java | UI | 暴露模块轮询与出站并发配置 |
| BridgeConfigProvider.java | Config | 向微信进程导出可读取的模块设置 |
| BridgeConfigReceiver.java | Config | 接收外部配置广播并刷新镜像配置 |
