<!-- AUTO-DOC: Update me when files in this folder change -->

# Mysql

MySQL 存储层负责桥接运行时的持久化、管理台查询投影，以及 outbox 租约的数据库实现；当前租约阶段还会对已观测到真实发出的文本重试做数据库侧硬拦截。

## Files

| File | Role | Function |
|------|------|----------|
| store.go | Storage | 持久化消息、设备、联系人，并在 outbox 租约前拦截已观测文本重试 |
| store_test.go | Test | 校验迁移、查询约束、消息去重和存储契约 |
