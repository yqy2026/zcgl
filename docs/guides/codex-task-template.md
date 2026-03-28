# Codex 任务模板

## 目标

让 Codex 在首轮就拿到可执行上下文，减少来回追问、遗漏校验和“做了一半就停”。

## 标准模板

```text
Goal:
要实现、修复或评审什么。

Context:
- 相关模块、文件、接口、报错、截图或日志
- 对应 REQ 编号、计划文档或历史背景
- 上下游依赖、当前阻塞点、已知边界

Constraints:
- 遵守 AGENTS.md
- 先给方案，等我确认后再动手
- 不明确先问，不要自己猜
- 采用 TDD；修 bug 先写复现测试
- 不做兼容保留，优先暴露问题
- 修改后更新 CHANGELOG.md

Done when:
1. 代码、文档或配置改动完成
2. 受影响测试或验证已完成
3. 受影响 lint / type-check / docs-lint 已完成
4. 相关 SSOT 文档已同步
5. 回复中列出边界情况和建议测试用例
```

## 常用写法

### 新功能

```text
Goal:
为资产详情页新增租赁台账摘要卡片。

Context:
- 页面：frontend/src/pages/Assets/AssetDetailPage.tsx
- 后端接口：/api/v1/assets/{id}/lease-summary
- REQ-AST-004

Constraints:
- 遵守 AGENTS.md
- 先给方案，等我确认后再动手
- 不做兼容保留
- 前端数据获取使用 React Query
- 修改后更新 CHANGELOG.md

Done when:
1. 页面可展示摘要卡片
2. 空态、错误态、无权限态已覆盖
3. 受影响测试通过
4. SSOT 文档与 CHANGELOG 已同步
```

### Bug 修复

```text
Goal:
修复合同审批后台账没有重算的问题。

Context:
- 现象：合同从待审变为生效后，ledger 未生成
- 报错：无显式报错，数据缺失
- 相关文件：backend/src/services/contract_approval_service.py
- REQ-RNT-006

Constraints:
- 遵守 AGENTS.md
- 采用 TDD，先写复现测试
- 不明确先问，不要自己猜
- 修改后更新 CHANGELOG.md

Done when:
1. 新增复现测试，修复前失败、修复后通过
2. 同类状态迁移不回归
3. 受影响后端测试通过
4. SSOT 文档与 CHANGELOG 已同步
```

### 只调研 / 只出方案

如果这次不要直接改代码，请在 `Constraints` 或 `Done when` 里显式写清楚：

```text
Constraints:
- 本次只调研并输出方案，不改代码

Done when:
1. 给出 2-3 种方案及 trade-off
2. 明确推荐方案
3. 列出涉及文件和风险点
```

## 反模式

- 只说“看一下这个问题”，不给现象、路径或报错
- 只给结论，不给 `Done when`
- 任务涉及多个子系统，却不说明本次边界
- 明明只想调研，却没写“不要改代码”
- 需要同步需求或字段文档，却没给 REQ 编号或 SSOT 入口
