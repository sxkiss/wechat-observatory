<!-- AUTO-DOC: Update me when files in this folder change -->

# Android Module Root

该目录保存 Android 构建入口、Gradle Wrapper 和模块源码子目录。当前支持本地 `./gradlew` 构建，以及 GitHub Actions 的 debug/release APK 工作流。

## Files

| File | Role | Function |
|------|------|----------|
| build.gradle | Build Root | 锁定 Android Gradle Plugin 版本 |
| settings.gradle | Build Root | 定义仓库源与 `:app` 模块 |
| gradlew | Wrapper | 统一本地与 CI 的 Gradle 入口 |
| gradlew.bat | Wrapper | Windows 下的 Gradle Wrapper 入口 |
| README.md | Doc | 说明模块构建、配置与发送行为 |
