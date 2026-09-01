# 审阅报告归档

`docs/archive/reviews/` 用于存放 AI 生成的审阅报告、方案复核记录与一次性评估结论。

- 本目录文档不作为当前需求或实现基线。
- 引用本目录内容时，应同时引用现行 SSOT 文档。
- 新增报告按 `YYYY-MM-DD-<topic>-review.md` 命名。

## 归档清单

| 文档 | 内容 |
|------|------|
| [2026-08-26-land-property-review-final-disposition.md](./2026-08-26-land-property-review-final-disposition.md) | **最终处置表**：明确毁灭性评审哪些接受、调整后接受或否决，并确认 v3.13 已归档、v4.0 是唯一活跃产品方案 |
| [2026-08-25-land-property-redesign-adjudication-review.md](./2026-08-25-land-property-redesign-adjudication-review.md) | 过程裁决记录；已由 2026-08-26 最终处置表收口，仅保留 93 项决策过程和证据门历史 |
| [2026-08-24-land-property-redesign-first-principles-destructive-review.md](./2026-08-24-land-property-redesign-first-principles-destructive-review.md) | 对 v3.13 目标方案完成三轮对抗复核和业务裁决；金额、历史、权限与并发保护有条件通过，产品 IA 与范围退回修订；保留 Asset 经营核算身份、Project 日常运营单元、客户与合作方及运营项目独立入口、专业权益写模型和 `ReinspectDeliveryRun`，撤销 LegalInstrument、AgreementScope、动态定价、项目预算与 Asset 账面价值等无证据扩项；补最小招商机会、Party × Project 催收事项和银行流水导入，以产权方直租完整路径优先，再扩代理与转租；不修改现行 SSOT 或业务代码 |
| [2026-08-17-market-property-system-research-review.md](./2026-08-17-market-property-system-research-review.md) | 中国与国际市场类似土地、物业、资产运营和 IWMS 产品调研，含样本能力矩阵、作业闭环、交互/实施比较及当前项目买借接自研建议 |
| [2026-08-17-land-property-system-product-review.md](./2026-08-17-land-property-system-product-review.md) | 原土地物业系统与当前项目的产品能力、前端体验、差距矩阵和重构路线复核报告 |
| [2026-08-19-sast-quality-audit-review.md](./2026-08-19-sast-quality-audit-review.md) | 全代码库 SAST 与质量深度审计：数据流/BOLA、并发状态、错误处理可观测性、可维护性、DevSecOps 配置五域 45 项发现（含修复建议与已验证安全基线），只读未改代码 |
| [2026-08-19-land-property-redesign-destructive-review.md](./2026-08-19-land-property-redesign-destructive-review.md) | 对重构方案 v3.4 的第一性原理毁灭性评审：命名/信息架构/菜单/布局四维。结论为后端硬化层全部保留、产品层五个结构性推翻（词汇终审前一次裁决、七入口收敛为五问题入口、补房源读视图与组合驾驶舱、黄金视区重排、低频动作去常驻化），含 SSOT 词汇裁决表、两级菜单树、三张页面区块图、v3.5 十条修改建议与补充测试用例；只读评审，未改代码与现行 SSOT |
| [2026-08-19-land-property-redesign-v38-final-review.md](./2026-08-19-land-property-redesign-v38-final-review.md) | 对 v3.8 单文档稿的终审评审：10 砍/10 补与 v1.2 会签五项闭合审计；判定 P1 三项（合同-空间覆盖关系未定义、押金抵扣工作流缺失、坏账核销金额语义缺失）退回 v3.8.1，P2 六项随版修订；v3.8.1 已按评审完成 P1/P2 定向修订，待最终评审；只读评审，未改代码与现行 SSOT |
| [2026-08-20-land-property-redesign-v381-external-review.md](./2026-08-20-land-property-redesign-v381-external-review.md) | 对 v3.8.1 的外部对抗评审终局版：R1 外部 GLM 毁灭性初评（五问+四维度+四大缺口裁决）→ R2 DeepSeek 逐条反驳 → R3 收敛终局。结论：真删 0、并 1、改 12；4 项 P0 站立（盘活进度口径、锁定-签约交接不变量、命令×页面落点表、押金 G0 推荐选①）；撤回 Extend/Correct 与 scope_diagnosis:read 两把删刀并记录教训；驱动 v3.9 修订；只读评审，未改代码与现行 SSOT |
| [2026-08-20-land-property-redesign-final-opinion-review.md](./2026-08-20-land-property-redesign-final-opinion-review.md) | 对 v3.10 及本轮外部反驳意见的最终收敛裁决：保留金额/历史/权限硬化主干，不推倒重构；按用户产品范围指令推翻“物业本期冻结”，新增巡检—工单—验收/重开—交还/交付闭环和第六业务入口；识别 1 项 P0 与 5 项 P1，补齐产权方直租、承租转租、委托运营三种模式的统一授权解析与不可变快照，采用独立 Space 及有效期化项目归属；将 B0 拆为既有裁决和新领域核验两个五日时间盒，将物业 B4 按独立 Epic/五个可独立验收子切片排期，并区分物业域最小增量、整个产品最小商业闭环和本期最终签字范围；物业单向依赖稳定 `space_id`，不反向阻断合同资金主链；v3.11 方案签字与实施后的产品交付签字分门验收；只改评审归档，不改现行 SSOT、v3.10 正文或业务代码 |
| [2026-08-19-land-property-redesign-v372-destructive-review.md](./2026-08-19-land-property-redesign-v372-destructive-review.md) | 对重构方案 v3.7.2 的第二轮毁灭性评审（首席架构师终审，v1.1 复审修订 + v1.2 终审会签 + v1.3 执行更新）。裁决：后端钱与历史硬化层全部保留；推翻 §2.1 空间/资产原子裁决（Asset 冒充 Space 致房源/空置/盘活全线失真），砍治理浮肿 8 项维持 + 1 项重写（合并收款仅删专项权限仪式、锚点版本链保留）+ 1 项降级 ADR 重议（服务费修订），补空间原子/押金红线/坏账核销/底价有效期/待确权接线等 10 项底层核心；终审结论"不签字、退回修订"，文末附复审裁决记录与 v1.2 终审会签五项修正（空间 ADR 对齐、单锚点措辞、已锁定事实源、行数硬规则、return_to 白名单）作为 v3.8 输入；v1.3 起项目文档上限改为 2000 行、v3.8 单文档不拆分；只读评审，未改代码与现行 SSOT |
| [2026-08-21-land-property-redesign-v312-destructive-review.md](./2026-08-21-land-property-redesign-v312-destructive-review.md) | 对 v3.12 的第五轮毁灭性评审与对抗复核终局（R1 Space/Right/Motion 三原子评审 → R2 逐条原文核查 → R3 终局裁决）。R1：骨架判为正确（四事实轴与三原子同构），砍三类脂肪（收付服务费 tab 降为类型筛选、台账"账本集合义"废除、可租/即将释放改名、首版 5 类例外）并增补六件（租金滚存、只读租控图、确权队列、欠费全景、定价参考卡、盘活月报）。R2 驳回 B4.4 过期重检删除（幂等链身份下"幂等新建"不成立，successor 机制正是其唯一载体；证据时效是实体风险非防御机械），降级并发门分期（切片协议已分布）与 0 号切片（改为 B1 后跨 A1–A3 骨架集成测试工件）。R3 接受驳回与降级，删减净残值收缩为四件，补三件遗珠（释放收入潜力卡入清单、巡查 Resume 命令洞、review 有效期补进 B0-B 签字清单）。文末附 v3.13 冻结收口清单（16 项）与五条教训；头条结论：瓶颈已从设计质量转移到 B0 四项签字速度，v3.13 后设计侧停止产出新版本。评审本身只读，未改方案正文、SSOT 或业务代码；该清单已于 2026-08-21 驱动方案正文修订至 v3.13（仍仅改设计文档，未改 SSOT 或业务代码）。v3.13 执行时按终审共识将第 12 项修正为：`ReviewInspectionRun` 与 `ReinspectDeliveryRun` 共享内部后继创建内核，不合并为一条用户命令；并将“台账单义”落为“账本集合义废除，资产台账/合同台账作为对象登记册复合专名保留”；“确权台账队列”落为“确权清单（跟进留痕，非任务）” |
