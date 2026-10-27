# 变更日志 (Changelog)

格式见 `AGENTS.md`「CHANGELOG 规范」：新条目加在「未发布」段最上方，每条一行、不超过 200 字，细节写进提交说明。
历史条目见 [`docs/archive/changelog/`](docs/archive/changelog/README.md)。

## 未发布

- docs(asset-ops): 更新 V2 开工前置条件，补齐管理费回执命令字段扩宽及真实 PostgreSQL 幂等测试计划；仅修规格，未实施 V2。
- docs(merge): 合入 V2 租金、押金与委托管理费规格及实施计划，保留 V1 归档和验收边界；V2 功能仍未开始，目标环境数据切换方案确认后开工。
- docs(merge): 合入 Agent 规则单一来源与日志归档分支，额外原样归档 develop 新增的 V1 收口记录，保留已合并的 PR #95 证据。
- fix(frontend): `useFormFieldVisibility` 中业态类别为空时经营模式误显示（`?.trim() !== ''` 未判空），改为先判空再 trim 并补测试；同步更正 typescript-conventions 示例。该 hook 目前无调用方。
- docs(changelog): 原 CHANGELOG 达 3844 行 / 1.68 MB，按时间段原样拆入 `docs/archive/changelog/`（3 份，均 ≤2000 行），新文件改为一行一条。
- docs(agents): AGENTS.md 设为唯一事实源——CLAUDE.md/GEMINI.md 改为首行导入（Claude 原先读不到 AGENTS.md），子目录规则迁入 backend/、frontend/AGENTS.md；集中红线、去重，修正错误的判空示例与 make check 说明。
