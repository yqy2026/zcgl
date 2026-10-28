# 变更日志 (Changelog)

格式见 `AGENTS.md`「CHANGELOG 规范」：新条目加在「未发布」段最上方，每条一行、不超过 200 字，细节写进提交说明。
历史条目见 [`docs/archive/changelog/`](docs/archive/changelog/README.md)。

## 未发布

- test(asset-ops): 补齐押金扣除结清、撤销恢复和不生成租金记录的真实 HTTP 回归，防止赔偿扣款被误计入租金到账（REQ-DEP-001 / #99）。
- style(asset-ops): 对齐押金结算请求与成对撤销服务的 Ruff 格式，修复 PR-B 静态门禁（#99）。
- feat(asset-ops): 接入押金条目、范围查询、收退登记、续签结转与抵租成对撤销，补齐终止自动/手工分配、免租补收及撤销恢复，并提供押金详情和未结清筛选（REQ-DEP-001 / #99）。
- feat(asset-ops): 合并租金 PR-A 并清理分支，启动 PR-B 押金余额、四类方向与续签转入转出纯规则，补齐资金需求 E2E 准入；持久化、结算 API 和前端继续实施（REQ-DEP-001 / #98）。
- docs(asset-ops): 将 V2 实施汇总对齐已有租金代码与测试证据，纠正 PR-A 尚未开始的旧状态，保留 CI、浏览器与资金类整体验收边界（REQ-LED-001 / #98）。
- fix(asset-ops): 丢弃编辑后迟到的租金更正预览，跨业务月阶段规范拆分且保持账期锚点，回填访问收口至 CRUD；API 一致性检查按实际挂载图识别嵌套路由（REQ-LED-001 / #98）。
- fix(ui): 将资产单元、合同详情、合同录入及生命周期页误写为 13rem/15rem 的 7 处字号改为字号变量，修复文字被放大到两百多像素的问题。
- fix(asset-ops): 修复移动顶栏高度变量作用域及合同详情网格最小宽度，避免台账标题被遮挡、租金阶段编辑字段在窄屏溢出（REQ-LED-001 / #98）。
- fix(auth): 补齐登录前的过期改密入口，校验当前密码、账号锁定及密码历史，改密后撤销旧会话并要求重新登录；卡片随表单增高，避免底部操作被裁切（REQ-AUTH-001）。
- fix(asset-ops): 收口 PR-A 复核问题：补齐锁定手工与补收义务的生命周期不一致提示，统一真实 HTTP 权限异常，模型守卫改验未替换阶段的部分唯一索引（REQ-LED-001 / #98）。
- feat(asset-ops): 推进 V2 PR-A 租金义务、追加登记与撤销、阶段更正及台账；统一合同锁序，补录遇锁定重叠时提示核对而不重复计收，完整验证仍在进行（REQ-LED-001）。
- feat(asset-ops): 完成 V2 PR-0 合同字段规则与同事务脱敏变更记录，新增按 Party 范围读取接口；修复委托协议录入与续签字段及扫描件类型，合同级付款字段确认后只读（REQ-CTR-001/002）。
- chore(dev): 按未上线项目直接切到最新 develop 并执行开发库最新迁移，取消 V2 上线演练前置；清理 4 条已合并远端分支和 2 条本地分支，保留主干与未合并依赖分支。
- test(specs): 将租金阶段漂移守卫精确对齐 V2 两个已规划未实现的替换标记字段，其他合同实体继续要求零漂移；字段报告逻辑不变。
- docs(asset-ops): 更新 V2 开工前置条件，补齐管理费回执命令字段扩宽及真实 PostgreSQL 幂等测试计划；仅修规格，未实施 V2。
- docs(merge): 合入 V2 租金、押金与委托管理费规格及实施计划，保留 V1 归档和验收边界；V2 功能仍未开始，目标环境数据切换方案确认后开工。
- docs(merge): 合入 Agent 规则单一来源与日志归档分支，额外原样归档 develop 新增的 V1 收口记录，保留已合并的 PR #95 证据。
- fix(frontend): `useFormFieldVisibility` 中业态类别为空时经营模式误显示（`?.trim() !== ''` 未判空），改为先判空再 trim 并补测试；同步更正 typescript-conventions 示例。该 hook 目前无调用方。
- docs(changelog): 原 CHANGELOG 达 3844 行 / 1.68 MB，按时间段原样拆入 `docs/archive/changelog/`（3 份，均 ≤2000 行），新文件改为一行一条。
- docs(agents): AGENTS.md 设为唯一事实源——CLAUDE.md/GEMINI.md 改为首行导入（Claude 原先读不到 AGENTS.md），子目录规则迁入 backend/、frontend/AGENTS.md；集中红线、去重，修正错误的判空示例与 make check 说明。
