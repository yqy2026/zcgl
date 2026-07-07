# 项目问题跟踪索引

本目录只保留仍需实施、验证或重新立项的技术债务与系统性问题。已被 SSOT、代码实现或后续计划吸收的记录移入 `docs/archive/issues/`。

> 状态以本索引为入口；进入完成态前必须有新鲜门禁证据。`scripts/check_requirements_authority.py` 会校验活动报告与本索引双向一致。

## 活动记录

| 文档 | 内容 | 状态 | 下一动作 |
|------|------|------|------|
| [2026-07-06-operations-ledger-prd-revision.md](./2026-07-06-operations-ledger-prd-revision.md) | 运营台账、终端租户收缴、运营方收入/成本与代理服务费结算的 PRD 修订建议 | 🔄 实施中 | 后端模型、迁移、流水分摊和服务费底座已启动 |
| [2026-06-23-wecom-userid-mapping-and-send-verification.md](./2026-06-23-wecom-userid-mapping-and-send-verification.md) | 企业微信应用消息真实发送验证与系统用户↔企业微信 `userid` 映射 | 🔄 外部验证/映射待补 | 应用消息代码与凭据 `gettoken` 已验证；真实发送待企业微信可信 IP / 域名配置，正式映射待实施 |
| [2026-04-party-architecture-analysis.md](./2026-04-party-architecture-analysis.md) | 主体列表业务角色体验问题与旧 A+C 方案 | ⏸ 旧方案未采纳，待重新立项 | 先补产品需求与验收口径，再决定动态查询或读模型；禁止直接落旧 JSONB 缓存方案 |

## 已归档记录

归档清单与原因统一见 [`docs/archive/issues/README.md`](../archive/issues/README.md)。
