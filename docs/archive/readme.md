# 文档归档目录说明

## 🎯 Purpose
本目录用于存放**已完成历史阶段、但仍需保留追溯价值**的文档，避免旧草稿干扰当前基线。

## ✅ Status
**当前状态**: Active (2026-02-09)

---

## 归档原则

- 当前研发与验收基线以 `docs/requirements-specification.md` 为准。
- 存在以下任一条件的文档进入归档：
  - 仅描述历史版本（如 v2 升级临时计划）
  - 已被新规格或新流程替代
  - 调研问卷、评估草案等非当前执行文档
- 归档文档默认只读，不再持续维护业务正确性。

---

## 目录结构

- `drafts/`：历史草稿、重构分析草案
- `plans/`：历史升级计划、临时实施计划
- `testing/`：历史阶段测试清单
- `research/`：调研问卷、技术评估记录

---

## 已归档（当前）

- `drafts/architecture-refactoring-2026-02.md`
- `plans/v2-upgrade-plan-2026-02.md`
- `testing/v2-test-cases-2026-02.md`
- `releases/v2-release-notes-2026-01.md`
- `research/land-property-asset-management-requirements-survey.md`
- `research/land-property-asset-management-requirements-survey-field.md`
- `research/siliconflow-paddleocr-integration-2026-02.md`

---

## 使用建议

- 需要了解当前能力：优先查看 `docs/requirements-specification.md`
- 需要查看历史背景：从本目录按时间定位
- 若归档文档被重新激活，应迁回主目录并更新 `docs/index.md` 与 `CHANGELOG.md`
