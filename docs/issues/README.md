# 项目问题跟踪索引

本目录只保留仍需实施、验证或重新立项的技术债务与系统性问题。已被 SSOT、代码实现或后续计划吸收的记录移入 `docs/archive/issues/`。

> 状态以本索引为入口；进入完成态前必须有新鲜门禁证据。`scripts/check_requirements_authority.py` 会校验活动报告与本索引双向一致。

## 活动记录

| 文档 | 内容 | 状态 | 下一动作 |
|------|------|------|------|
| [2026-08-17-module-point-check.md](./2026-08-17-module-point-check.md) | 全模块点检（API 103 探测 + 20 路由页面实测）：缺陷 2.1-2.6 已修复（§9 修复记录，路由遮蔽/`[Any]` 残留/图表 ExpressionError 根因闭合/GBK 编码含复核补修 FileHandler utf-8/antd 告警）；遗留 2.7 四项口径观察待产品确认、§9.8 三条死代码备查（monitoring.py 与 system_monitoring/ 包均未挂载、assetDictionaryService 指向已下线旧域） | 🔄 部分处置 | 2.7 口径疑点由产品负责人认定；§9.8 死代码清理待立项；浏览器层 20 路由回归复测留待下次点检 |
| [2026-08-10-analytics-ui-caliber-audit.md](./2026-08-10-analytics-ui-caliber-audit.md) | 分析/报表口径一致性前端审计（§3.2 指标前置）：8 条口径规则逐条结论；必须修 5 项（双视角猜选、四类视图缺失、净收益命名、逾期守卫、自营租金命名）、建议修 6 项、观察项 5 项 | 🔄 待处置 | 地图 #69 决策 |
| [2026-08-09-mvp-g1-acceptance-dryrun.md](./2026-08-09-mvp-g1-acceptance-dryrun.md) | G1/G2 验收预演：3.1-3.3、5.1-5.3 已修复；5.5 所有方主体列（方案 A）已实施；5.6 DeepSeek 候选链路复验通过；ACC-023 通过 | ✅ 处置完毕 | 待办清零；仅剩 HTTP 环境幽灵 socket 清理（命令见报告 5.5） |
| [2026-08-04-unused-db-fields-audit.md](./2026-08-04-unused-db-fields-audit.md) | 数据库未实际使用字段审计（3 张空表、5 组死字段、已删表 `project_ownership_relations` 仍被 ownership 端点引用） | 🔄 待处置 | 高风险项 4.1 需先在真实已迁移库复现确认；处置方案待立项 |
| [2026-06-23-wecom-userid-mapping-and-send-verification.md](./2026-06-23-wecom-userid-mapping-and-send-verification.md) | 企业微信应用消息真实发送验证与系统用户↔企业微信 `userid` 映射 | 🔄 外部验证/映射待补 | 应用消息代码与凭据 `gettoken` 已验证；真实发送待企业微信可信 IP / 域名配置，正式映射待实施 |

## 已归档记录

归档清单与原因统一见 [`docs/archive/issues/README.md`](../archive/issues/README.md)。
