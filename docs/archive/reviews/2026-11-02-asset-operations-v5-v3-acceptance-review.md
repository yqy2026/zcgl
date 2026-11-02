# V3 功能验收走查与修复复核

- 日期：2026-11-02
- 范围：按用户继续指示执行 V3 四项重点功能验收，并验证实际提交与下载。
- 结论：修复两处真实应用缺陷后，Chromium 走查 14/14 通过。
- 现行口径：[PRD](../../prd.md)、[领域规格](../../specs/domain-model.md)、[API契约](../../specs/api-contract.md)。本文为一次性证据，不代替 SSOT。
- [实施计划](../backend-plans/2026-10-30-asset-operations-v5-v3.md)已完结归档；合并以 PR #104 最新 CI 为准。

## 环境和数据边界

使用当前代码的真实 Vite 前端、Uvicorn 后端、专用 PostgreSQL 验证库和独立 Redis。随机验收账户和起始物业均在本次隔离库构造，未读取开发密钥，未重建开发库或清空既有缓存。

纳入经营性物业土地1.5㎡/建筑100㎡，排除物业10㎡/40㎡，非经营性公房20㎡/60㎡。预期全量土地31.5㎡、建筑200㎡、项目2个，出租率分母1宗、已租1宗。另设仅非经营性、月末后切换运营主体、缺全量来源的合成历史快照。

复用月报测试 helper 时空 `unit_snapshot` 导致范围读取500；最小真实 AsyncSession 复现确认是验收种子非法，使用正式 `build_unit_snapshot` 补齐后读取通过，没有修改业务校验或吞错。

## 真实浏览器结果

| 检查 | 结果 |
|---|---|
| 页面真实登录 | 通过 |
| 全量面积/项目与经营性考核分母独立 | 通过 |
| 重复复制接口返回原草稿身份 | 通过 |
| 页面重复复制自动继续编辑原草稿 | 通过 |
| 原草稿排除原因等内容保留 | 通过 |
| 页面预览、确认提交并展示全量来源快照 | 通过 |
| 点击导出后实际下载CSV，含汇总及公房来源 | 通过 |
| 仅非经营性物业时汇总仍可见 | 通过 |
| 月末后转主体，补报上月仍归原主体 | 通过 |
| 合成历史快照保留原口径及来源未知提示 | 通过 |
| 320/640/1440宽度无页面横向溢出 | 三项通过 |
| 页面脚本错误 | 未捕获 |

本机截图及CSV位于 Codex 本轮可视化目录 `v3-acceptance-20261102/`，包含 `01-full-property-totals.png`、`02-existing-draft.png`、`03-only-public-property.png`、`04-month-end-operator.png`、`05-legacy-snapshot.png`、`06-new-full-snapshot.png`、`accepted-report.csv` 和 `results.json`。浏览器脚本和随机凭据只在临时目录，不写入仓库。

## 发现、修复及回归

1. **已有草稿未恢复编辑**。共享API拦截器返回增强错误，原Axios错误在 `originalError`；报送服务只解析直接Axios错误，丢失业务码和 `draft_id`。只在报送服务解一层真实包装，未改公共客户端。使用真实 `ApiErrorHandler.handleError` 的两条回归先失败，修复后报送服务/页面22条通过，类型与定向lint通过。
2. **CSV任务结果在独立请求中丢失**。任务创建提交了pending，渲染终态只flush，会话关闭后回滚；共享事务适配测试掩盖该错误。在服务层成功与失败终态写入后显式提交，未将事务下沉CRUD。新增真实独立会话回归，红测两分支均pending，绿测completed及CSV可见、failed及原因可见，2条通过；mypy全库473文件通过。真实页面下载最终通过。

永久回归：[前端错误包装](../../../frontend/src/services/__tests__/occupancyReportService.test.ts)、[导出独立会话持久化](../../../backend/tests/e2e/test_occupancy_report_export_persistence.py)。后者使用专门新建的导出验证库，测试只删除自身生成的记录，未重建浏览器QA库。

## 复核边界

本轮验证真实登录、页面交互及跨独立请求持久化，不把共享会话HTTP用例等同于真实事务可见性。原实施计划中的主档并发写入边界继续如实保留，未宣称任意并发变更均被阻止。