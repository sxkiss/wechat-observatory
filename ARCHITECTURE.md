<!-- AUTO-DOC: Update me when project structure or architecture changes -->

# Architecture

微信网关由 Go `bridge`、Android LSPosed 模块和 Web 管理台组成；模块负责微信进程 I/O，服务端负责鉴权、持久化和 outbox 编排。
当前 outbox 支持批量租约，服务端会优先按 `wxid + kind` 分散同批次 lease；Android 模块再按相同 lane 并发发送，同 lane 仍串行，避免微信本地消息验收冲突。
仓库内还提供 GitHub Actions 工作流，覆盖 Android debug/release APK 构建与 Docker 多架构镜像发布。

## Indexes

- [.github/workflows/INDEX.md](.github/workflows/INDEX.md)
- [internal/bridge/INDEX.md](internal/bridge/INDEX.md)
- [android-module/app/src/main/java/cc/wechat/observatory/INDEX.md](android-module/app/src/main/java/cc/wechat/observatory/INDEX.md)
- [android-module/app/src/main/java/cc/wechat/observatory/config/INDEX.md](android-module/app/src/main/java/cc/wechat/observatory/config/INDEX.md)
