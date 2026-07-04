<!-- AUTO-DOC: Update me when files in this folder change -->

# Module Config

配置层负责从 Provider、SharedPreferences 和文件镜像汇总模块设置，并对轮询批次与并发度做边界收口。

## Files

| File | Role | Function |
|------|------|----------|
| BridgeConfig.java | Loader | 读取模块配置并标准化 poll_limit / outbox_parallelism |
