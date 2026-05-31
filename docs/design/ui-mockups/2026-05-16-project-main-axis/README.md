# 项目主轴资产运营 UI 图

## 定位

本目录存放基于当前 PRD 和规格契约生成的 UI 图，用于产品、设计和研发讨论项目主轴资产运营的目标体验。

生成方式：Codex 根据 `docs/prd.md`、`docs/specs/domain-model.md`、`docs/specs/api-contract.md` 和现有前端设计系统生成静态画板，再通过 Playwright 导出 PNG。

## 设计原则

- 普通用户以“项目”为主工作对象，从项目进入资产、合同关系、台账、客户、风险和分析。
- 用户界面展示“合同关系 / 经营对应关系”，不把 `ContractGroup` 或“合同组”作为普通业务概念暴露。
- 承租转租与代理运营并列展示，同一条合同关系内不混用经营模式。
- 收入、台账和分析按经营模式分区，代理直租租金不计入运营方自营应收。
- 视觉风格延续 Ant Design 管理后台的密度和清晰度，避免营销页式大幅装饰。

## 图稿清单

| 文件 | 画面 | 覆盖需求 |
|---|---|---|
| `png/ui-01-dashboard.png` | 工作台总览 | 项目主轴、全局搜索、风险待办、收入拆分、客户双指标 |
| `png/ui-02-project-detail.png` | 项目详情运营台账 | `REQ-PRJ-003`：项目详情展示资产、合同关系、收付款、租户客户、风险和项目分析入口 |
| `png/ui-03-contract-relation.png` | 合同关系建模 | `REQ-RNT-001`、`REQ-RNT-002`：项目下创建合同关系，承租转租和代理运营不混用 |
| `png/ui-04-analytics-ledger.png` | 经营分析与财务台账 | `REQ-ANA-001`、台账契约：收入拆分、客户双指标、账期穿透和模式口径隔离 |

## 源文件

- `source.html`：可复现静态画板，包含 4 个 1440x960 设计画面。
- `png/`：由源画板导出的 PNG 文件。

## 重新导出

在项目根目录执行：

```powershell
node docs/design/ui-mockups/2026-05-16-project-main-axis/render.mjs
```

脚本优先复用前端项目中的 Playwright 依赖；如 Playwright 自带浏览器未安装，会尝试使用本机 Chrome 或 Edge。也可以通过 `PLAYWRIGHT_CHROMIUM_EXECUTABLE` 指定浏览器路径。
