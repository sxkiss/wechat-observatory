# Development Status

`wechat-observatory` 当前已经整理为独立的微信网关项目。

## 已完成

- 服务端使用 Go 实现，入口为 `cmd/bridge`。
- 数据库工具入口为 `cmd/bridge-db`。
- Web 管理台使用 React 和 shadcn 风格组件，构建产物嵌入 Go 服务。
- Android 模块包名为 `cc.wechat.observatory`。
- Android 模块公开适配目标为微信 Android `8.0.75`。
- 模块认证只使用 API Key。
- 模块在微信进程内自动识别当前 `wxid`，用户不需要手动填写。
- 设备显示名由 Web 管理端设置。
- 支持 API Key 生成、启用、停用、删除。
- 删除 API Key 会注销对应模块身份。
- 支持消息入库、实时推送、联系人同步、媒体附件保存，以及 Action Outbox v1 的文本、媒体和结构化消息发送。
- 语音入站媒体已通过实机验证：当微信原始 hint 找不到文件时，Android 模块会在 `voice2` 中按消息时间回退定位 AMR/SILK 文件，并通过媒体重试上传。
- 表情入站已通过实机验证：`message.type=47` 会输出结构化 MD5、type/len、规范化 CDN URL；本地表情媒体是 best-effort 附件，octet-stream 原始文件在公开协议中标记为 `opaque=true`。
- 旧游戏业务、命令解析、自动回复和第三方协议登录不属于当前项目。

## 当前数据库表

- `bridge_api_keys`
- `bridge_devices`
- `bridge_message_events`
- `bridge_module_outbox`
- `bridge_module_runtime`
- `bridge_module_contacts`

## 推荐验证

```powershell
python3 scripts/verify_project.py
```

默认验证会运行 Go 测试、公开协议文档/fixture 校验、Android 模块结构、工具链诊断和 action 静态覆盖校验、Android 工具链诊断单测、Public API 契约脚本单测、源码卫生检查、Web Vitest、Web 构建、临时 bridge 二进制构建和 `git diff --check`。源码卫生检查会覆盖 tracked 与 untracked 的源码/文档文件，并跳过备份、缓存和嵌入构建产物。只读线上契约检查需要显式传入 API Key：

快速验证时，`--skip-docs` 只跳过公开文档和 fixture 校验；Android 静态检查、契约工具单测和 Python 语法检查需显式使用 `--skip-static-checks` 才会跳过。

```powershell
$env:WECHAT_OBSERVATORY_API_KEY = "your-api-key"
python3 scripts/verify_project.py --live-readonly --base-url http://127.0.0.1:8088
```

手机模块已连接并应处于 ready 状态时，可以打开更严格的 live gate：

```powershell
python3 scripts/verify_project.py --live-readonly --require-live-ready --base-url http://127.0.0.1:8088
```

如果本机 `.env` 里有 `BRIDGE_ADMIN_PASSWORD`，也可以只读 admin 元数据自动选择绑定到 ready 模块的 API Key，避免误用旧设备 key：

```powershell
python3 scripts/verify_project.py --live-readonly --live-api-key-from-admin --require-live-ready --base-url http://127.0.0.1:8088
```

完整消息样本覆盖可以打开分页扫描。日常安全回归使用 `all-safe-live`，它覆盖除红包/转账支付样本外的所有 public fixture：

```powershell
python3 scripts/verify_project.py --live-readonly --live-api-key-from-admin --require-live-ready --base-url http://127.0.0.1:8088 --live-message-limit 500 --live-message-pages 20 --live-require-fixture all-safe-live
```

严格 14 类覆盖使用 `--live-require-fixture all`。其中 `payment` 只做入站识别和脱敏，不支持出站自动化；如果运行中的服务仍是旧进程，历史高位红包/转账消息可能需要重建并重启服务后才会归一化为 `kind=payment`。

需要做真实发送回归前，先 dry-run 解析目标和待发送 payload 摘要：

```powershell
python3 scripts/public_api_contract_check.py --dry-run-send --send-kinds text,image --target-query "有风" --target-name "有风测试群" --target-kind room --target-name-contains "有风"
```

真实发送回归再使用 `scripts/public_api_contract_check.py --confirm-send --require-send-success`，并显式传入测试目标 `wxid` 或精确联系人查询；建议同时使用 `--target-name-contains` 和 `--require-target-contact`。该命令会真实发送消息，不能作为默认验证。

Android 构建需要当前环境存在 Gradle Wrapper、系统 `gradle`、`GRADLE_BIN` 指定的 Gradle，或当前远端预置的 `/tmp/wechat-gradle`/`/tmp/gradle-*` Gradle 分发包。SDK 优先读取 `WECHAT_ANDROID_SDK_ROOT`、`ANDROID_HOME`、`ANDROID_SDK_ROOT`，也会识别当前远端预置的 `/tmp/wechat-android-sdk`。确认工具链可用后显式执行：

```powershell
python3 scripts/verify_project.py --android
```

默认验证仍会检查 Android LSPosed 模块结构、工具链状态和 outbox kind 分发覆盖；APK 构建是 opt-in，避免日常验证在未准备 SDK 的机器上隐式下载依赖或写入构建产物。

```powershell
python3 scripts/validate_android_toolchain.py
```

该诊断只读输出 `build_ready`、缺失项和历史 APK 元数据；历史 APK 只能证明曾经产出过安装包，不能证明当前源码可复现编译。

## 后续可做

- 增加更多微信版本兼容性记录。
- 增强媒体附件上传和外部对象存储/CDN 支持。
- 增加更细粒度的管理台权限模型。
- 增加数据库备份和数据保留策略文档。
