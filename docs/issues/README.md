# 项目问题跟踪索引

本目录只保留仍需实施、验证或重新立项的技术债务与系统性问题。已被 SSOT、代码实现或后续计划吸收的记录移入 `docs/archive/issues/`。

> 状态以本索引为入口；进入完成态前必须有新鲜门禁证据。`scripts/check_requirements_authority.py` 会校验活动报告与本索引双向一致。

## 活动记录

| 文档 | 内容 | 状态 | 下一动作 |
|------|------|------|------|
| [2026-08-09-mvp-g1-acceptance-dryrun.md](./2026-08-09-mvp-g1-acceptance-dryrun.md) | G1/G2 验收预演：3.1-3.3、5.1、5.2、5.3 全部已修复；ACC-023 多账期分摊验收通过 | 🔄 待处置 | "所有方主体"列口径待产品确认；解析候选需 DeepSeek 配置后复验 |
| [2026-08-04-unused-db-fields-audit.md](./2026-08-04-unused-db-fields-audit.md) | 数据库未实际使用字段审计（3 张空表、5 组死字段、已删表 `project_ownership_relations` 仍被 ownership 端点引用） | 🔄 待处置 | 高风险项 4.1 需先在真实已迁移库复现确认；处置方案待立项 |
| [2026-06-23-wecom-userid-mapping-and-send-verification.md](./2026-06-23-wecom-userid-mapping-and-send-verification.md) | 企业微信应用消息真实发送验证与系统用户↔企业微信 `userid` 映射 | 🔄 外部验证/映射待补 | 应用消息代码与凭据 `gettoken` 已验证；真实发送待企业微信可信 IP / 域名配置，正式映射待实施 |

## 已归档记录

归档清单与原因统一见 [`docs/archive/issues/README.md`](../archive/issues/README.md)。
