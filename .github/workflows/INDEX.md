<!-- AUTO-DOC: Update me when files in this folder change -->

# Workflows

该目录保存仓库级 CI 工作流。当前覆盖 Android APK 构建与 Docker 多架构镜像构建，两条链路都面向 GitHub Actions。

## Files

| File | Role | Function |
|------|------|----------|
| android-build.yml | CI | 使用 Gradle Wrapper 构建 Android debug APK 并上传产物 |
| android-release.yml | Release | 优先构建已签名 release APK；无签名配置时回退到 debug APK，并支持手动指定 `release_tag` 发布 |
| docker-build-on-commit.yml | CI | 参考 allbot，在 main 分支变更后构建并推送多架构容器镜像 |
| docker-release-on-tag.yml | Release | 在版本标签上构建并推送 semver / latest 多架构镜像 |
