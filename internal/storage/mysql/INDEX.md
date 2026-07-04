<!-- AUTO-DOC: Update me when files in this folder change -->

# Mysql

MySQL 存储层负责桥接运行时的持久化、管理台查询投影，以及 outbox 租约的数据库实现。

## Files

| File | Role | Function |
|------|------|----------|
| store.go | Storage | 持久化消息、设备、联系人与 lane-aware outbox lease |
| store_test.go | Test | 校验迁移、查询约束和存储契约 |
