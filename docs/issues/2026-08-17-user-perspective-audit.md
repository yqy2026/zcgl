# 用户视角全面点检审计报告（2026-08-17 下午）

## 1. 背景与目的

同日上午已完成一轮模块点检（`2026-08-17-module-point-check.md`，API 103 条探测 + 20 路由页面加载实测，缺陷 2.1-2.6 当日修复）。该轮的深度边界是"页面能打开、接口能 200"；本轮按「启动项目并进行实际用户角度的点检等手段，全面审计项目」的要求，把点检深度推进到**真实用户操作流**：登录成功/失败路径、筛选与搜索、分页、表单弹窗与校验、详情入口导航、口径切换、全局搜索、通知、登出，并复验上午全部修复在运行环境的实际生效情况。

本轮**只审计不修码**（缺陷登记后修复另行排期），全部结论以"真实浏览器操作 + 截图视觉复核 + DOM 读取 + 控制台/网络错误收集"四重证据支撑。

## 2. 环境与验证方式

| 项 | 结果 |
|---|---|
| 服务 | 复用当日运行中的实例：后端 uvicorn :8002、前端 Vite :5173、PostgreSQL :5432、Redis :16379 |
| 后端代码版本 | ✅ 已验证为修复后代码：`/api/v1/tasks/statistics`、`/asset-custom-fields/types`、`/enum-fields/types/categories/list` 均 401（路由可达，鉴权先于业务）；两个 `[Any]` 垃圾路径均 404（已删除）——即上午 2.1/2.2/2.3 修复运行时生效 |
| 登录账号 | admin / admin123（Development Administrator，无界数据范围） |
| 浏览器操作 | Chrome 通道 Playwright（1600×900，与上午点检同款）6 轮脚本（v2 全模块扫描 + v3/v4/v5/v6 定向核实），每步截图 + console/pageerror/HTTP≥400 收集；ZCode In-app Browser 辅助交互复核（登录链、登出链、用户菜单） |
| 视觉复核 | 全部关键截图逐张人工/AI 视觉核验（登录校验、错误密码静默、资产列表、新建用户弹窗、项目详情抽屉、口径切换、经营分析、台账等 15+ 张） |
| 证据留存 | `tmp/audit-0817/`（截图 30+ 张、`results_v2.json`～`results_v5.json`、脚本 `tmp/audit_ui_0817*.js`） |

## 3. 结论总览

- **主路径全部可用**：登录（正确路径）、工作台（含产权方/运营方口径切换）、资产列表（19 行、关键词搜索、四组筛选下拉、分页、行操作、详情入口）、新增资产表单（空提交校验完整）、项目列表 + 详情抽屉、合同中心列表 + 编号进详情、经营台账（统计 + 数据行）、经营分析（4 图表完整渲染、0 图表错误）、主体/用户/角色/组织（列表 + 树视图）/产权证（列表 + 详情页）、字典联动、操作日志、系统设置、全局搜索（广州 → 项目/客户/资产分组）、通知中心、登出。
- **本轮新发现缺陷 4 项**（1 项 P1、1 项 P2、2 项 P3），全部完成根因定位与代码级证据；上午点检未覆盖到的根因是本轮走完了"错误路径 + 详情页深处"的操作流。
- **上午修复复验全部通过**（§6）。
- 观察项 5 条（§5），其中 2 条与上午 2.7 观察项关联。
- v2 全程 pageerror=0；console 错误 8 条全部归因（外部图片 1、组织树告警 2、产权证 422 链 5）；HTTP≥400 共 3 条（外部图片超时 1、产权证 422×2）。

## 4. 缺陷清单

### 4.1 【P1】错误密码登录：无任何反馈 + 页面硬刷新清空表单（auth 错误路径断裂）

- **现象**（真实操作流）：
  1. 输入错误密码点击「立即登录」→ **无 toast、无红字、按钮不 loading**（截图 `02-login-wrong-pwd.png` 视觉复核确认页面无任何变化）；
  2. 约 1 秒后页面**硬刷新**（整页重载），已输入的用户名/密码**被清空**，URL 变为 `/login?redirect=%2Flogin`；
  3. 控制台证据链：`[WARN] [API] Token expired, attempting refresh {url: auth/login}` → `POST /auth/refresh` 400「刷新令牌缺失」→ `[ERROR] Token refresh failed, logging out`。
- **根因**（代码级定位）：
  - `frontend/src/services/authService.ts:31`：`login()` 调 `apiClient.post(AUTH_API.LOGIN, ...)` **未传 `skipAuthRefresh: true`**（对比同文件 `getCurrentUser()` 正确传递了该标记）；
  - `frontend/src/api/client.ts:477-527`：拦截器对**任何非 refresh 的 401** 都进入"刷新令牌"分支，对 `/auth/login` 自身的 401（密码错误）无豁免 → 未登录态下 refresh 必然 400 → catch 分支执行 `window.location.href = '/login?redirect=…'`（`client.ts:524`）硬跳转；
  - `frontend/src/pages/LoginPage.tsx:106`：catch 块假定「错误处理已在 useAuth 中完成」，但 `useAuth` 设置的 error message 被随后的硬刷新整体吞掉，永远不可见。
- **附带发现**：硬跳转写入的 `?redirect=` query 参数**无任何消费方**——`LoginPage.tsx:103-104` 只读 `location.state.from`（SPA 内导航 state），硬刷新后 state 必然丢失，redirect 参数是死码；也因此用户重新完整输入后能正常进入 `/dashboard`（默认值兜底），链路不至于彻底断裂。
- **影响**：所有输错密码的用户都会遇到"点了没反应 → 页面闪一下 → 输入没了"的体验；错误密码的具体原因（密码错/账号锁/账号停用）完全不可见。
- **建议**：
  1. `login()` 请求标记 `skipAuthRefresh: true`；拦截器同时对 `/auth/login`、`/auth/refresh` URL 做 401 豁免（双保险）；
  2. `LoginPage` catch 中显式展示错误（useAuth error 或 `MessageManager.error`），后端 401 的 message（如「用户名或密码错误」）透传到 UI；
  3. 顺带清理 `redirect` query 死码或改为真实消费（统一回跳语义）。

### 4.2 【P2】产权证详情页「关联资产」显示原始 UUID（page_size 超限 → 422）

- **现象**：`/property-certificates/{id}` 详情页「关联资产」区域显示 `db724328-b1d9-45ab-8cea-b502303fafe3`（v4 DOM dump + 截图确认），用户无法得知关联的是哪个资产。
- **根因**：`frontend/src/pages/PropertyCertificate/PropertyCertificateDetailPage.tsx:71` 请求 `getAssets({ page: 1, page_size: 200 })`，而后端 `PaginationLimits.MAX_PAGE_SIZE = 100`（`backend/src/constants/api_constants.py:113`，`assets.py:295` Query `le=100`）→ 请求 **422**（且被前端重试机制再发一次，共 2 条 422 记录）→ `assetNameById` 映射表为空 → `:317` 的 `assetNameById.get(aid) ?? aid` 兜底输出 UUID。
- **上午未发现的原因**：上午点检只访问了产权证**列表页**与 API 探测，未进入详情页（详情页还有独立的 422 网络错误，页面加载型检查不覆盖详情页内部查询）。
- **影响**：产权证详情的关联资产可读性归零；控制台持续报 VALIDATION_ERROR 噪音 + 无意义重试。
- **建议**：`page_size` 改为 ≤100（资产规模增长后应改为按 `asset_ids` 批量查询名称的后端接口，避免全量拉取）；前端重试条件应排除 4xx。

### 4.3 【P3】组织树 TreeNode `value: undefined` antd v6 告警（每次进入组织页触发）

- **现象**：进入 `/system/organizations` 控制台输出 2 条告警：`Warning: TreeNode value is invalidate: undefined`、`key or value with TreeNode must be the same…`。
- **根因**：`frontend/src/pages/System/Organization/utils.tsx:102-123` `convertOrganizationTreeToDataNodes` 构建节点只设 `key: node.id` 未设 `value`，与 antd v6 Tree 的 key/value 语义不兼容（树视图本身渲染正常，v4 实测树形视图标签可切换、节点显示正常）。
- **建议**：节点补 `value: node.id`（或按 antd v6 规范统一只用其一），消除告警并避免未来 selection API 踩坑。

### 4.4 【P3】项目详情抽屉对「无有效数据」项目显示纯空白（无空态）

- **现象**：项目列表首行（`QC-REPROBE2-NOMGR`，非启用/待补绑定/0 资产，见 §5 观察项）点「查看项目」→ 抽屉打开、标题正常，但**内容区完全空白**（截图视觉复核确认）；正常项目（广州大道北 PRJ-LE000001-202608-0005）抽屉完整渲染基本信息/状态/组织/资产关联。
- **定性**：数据性空白（该测试项目确无可显字段）而非渲染崩溃，但产品上应显示 Empty 空态而非纯空白，避免用户误以为加载失败。
- **建议**：抽屉内容区对空数据加 `<Empty>` 占位；顺带处理「待补绑定/非启用」项目在列表中的可视化区分。

## 5. 观察项（非缺陷，登记备查）

1. **工作台同页出租率口径不一致**：统计卡片「整体出租率 91.4%」vs「运营状况概览」与「智能洞察」均为 91.5%（底层 91.47% 的舍入方向不同）。同页两处数字不一致易引发用户疑问，建议统一舍入规则。与上午 2.7 观察项同族（口径治理）。
2. **探测残留测试数据未清理**：项目列表存在 `QC-REPROBE2-NOMGR` / `PRJ-QC01-202608-7777`（非启用、待补绑定、无管理组织）等历史探测脚本造的数据；资产/主体数据为种子数据（正常）。建议清理非种子测试数据，避免干扰验收与演示。
3. **登录页外部资源超时**（上午已知维持）：`lh3.googleusercontent.com` 装饰图 `ERR_CONNECTION_TIMED_OUT`，登录页左图缺失；非本仓资源，建议替换为本地静态资源。另注：该资源长时间 pending 会让浏览器 `load` 事件显著延迟（自动化/监控场景易超时）。
4. **后台标签页 antd 动画冻结**（环境特性）：在 In-app Browser 后台标签页中，antd 动画依赖的 rAF 被节流，出现登录按钮点击不响应、登出确认弹窗不关闭且按钮卡 loading 等现象；**前台 Chrome 通道复验全部正常**，非应用缺陷。对真实用户的影响场景是"后台标签页长时间挂起后回来操作"，一般刷新即恢复；登记供排查同类报告时参考。
5. **资产名称蓝色链接样式但不可点击**：资产列表「物业地址/名称」列渲染为蓝色文本（视觉上像链接，截图复核确认），但 `cursor: auto` 且无点击行为，实际详情入口是行尾「查看资产详情」眼睛按钮（带完整 aria-label，可访问性良好）。视觉语义与交互不一致，建议调整颜色或让名称可点。

## 6. 上午修复复验结果（运行时实测）

| 上午缺陷 | 复验方式 | 结果 |
|---|---|---|
| 2.1 asset-custom-fields/types 路由遮蔽 | 未登录探针 | ✅ 401 可达（修复前 404） |
| 2.2 tasks 静态端点遮蔽 | 未登录探针 `/tasks/statistics` | ✅ 401 可达 |
| 2.3 enum `[Any]` 路径污染 | 探针规范路径 + `[Any]` 路径 | ✅ 规范路径 401 可达；垃圾路径 404 |
| 2.4 /analytics 图表 ExpressionError | Chrome 实测：console 过滤 `ExpressionError` = 0；canvas=4/svg=45；截图视觉复核 4 图表（概览卡片/分布饼图/柱状图/趋势图）全部完整渲染、标签正常 | ✅ 清零 |
| 2.5 GBK 启动日志 | 服务持续运行无 Logging error（上午真实启动复验维持） | ✅ |
| 2.6 antd 告警（useForm 悬挂/Descriptions span） | v2 全程 console 监听 `useForm is not connected` = 0；资产详情页无 span 告警 | ✅ 清零 |
| 2.7 四项口径观察 | 未动（维持待产品确认；本轮新增 §5.1 同族观察） | ⏸ |
| §9.8 三条死代码 | 本轮未动；同日晚间已清理收口，含复核扩展发现的前端 Monitoring 组件簇（处置记录见 module-point-check §9.8） | ✅ 已收口 |

另：上午「未做浏览器层 20 路由全量回归」的遗留项，本轮 v2 已覆盖同 20 路由（全部 loadOk、无 500、无 pageerror），该遗留可视为闭环。

## 7. 通过项明细（用户操作流实测）

- **认证**：干净状态登录 → 工作台（「登录成功」toast）；登出（确认弹窗 → 「已退出登录」toast → /login，Chrome 下无弹窗残留）；用户菜单快捷导航/个人资料/系统设置入口齐全。
- **工作台**：4 统计卡 + 智能洞察 + 面积分布 + 运营概览；产权方⇄运营方口径切换真实生效（视觉复核选中态变化；当前数据集两口径数值一致属数据本身特性）。
- **资产管理**：列表 19 行；关键词搜索（「测试大学」→ 0 行，空结果正常）；确权状态/物业性质/使用状态/资产状态筛选下拉均有选项；分页控件单页正确；行操作 4 个图标按钮全部带 aria-label（查看/编辑/历史/删除，可访问性佳）；「查看资产详情」→ `/assets/{id}`；工具栏（新增资产/导入资产/导出全部/保存条件/搜索历史）齐全。
- **新增资产**：`/assets/new` 独立页面，24+ 字段分组表单；空提交触发 6 条必填校验（权属主体/物业名称/物业地址/确权状态/使用状态/物业性质）；权属主体下拉走实时 parties 接口（主体中心 2 条数据在线，无阻断）；含 PDF 协议上传、重置、取消。
- **项目运营**：列表 + 「查看项目」眼睛按钮打开右侧详情抽屉（正常数据完整渲染）；编辑/删除按钮带 aria-label。
- **合同中心**：列表 + 点合同组编号按钮 → `/contract-center/{id}` 详情页。
- **经营台账**：统计条（当前结果数/本页应收/应付/实收/实付）+ 数据行 + 项目/资产/账期筛选。
- **经营分析**：4 图表完整、0 图表错误（§6）。
- **组织架构**：列表视图（含批量设置主体/新建/编辑/迁移/历史/数据范围/删除工具栏）+ 树形视图（1 节点：广州国有资产管理集团有限公司 GZ-ROOT-ORG 活跃）。
- **用户管理**：5 行；「新建用户」弹窗布局/必填标记（姓名/用户名/密码）正常（弹窗 footer 采样到的「预览调动影响」来自 forceRender 常驻的隐藏组织调动弹窗，属上午 2.6 修复的设计内 DOM，非缺陷）。
- **角色管理**：6 行（系统管理员 103 项权限等）。
- **产权证**：列表 2 行 → 详情页（证书信息、附件列表）。
- **系统**：字典管理（类型点击联动 9 行值）、操作日志（20 行，含今日点检自身操作记录）、系统设置（11 表单/卡片）、数据策略包、通知中心（「暂无通知」+ 查看全部入口）。
- **全局搜索**：顶栏入口 → /search 页，输入「广州」→ 项目/客户/资产分组结果带「查看详情」链接，结果数与对象分布正常。

## 8. 证据留存

- 截图（30+ 张）：`tmp/audit-0817/01-login*.png`、`02-login-wrong-pwd.png`（4.1 视觉证据）、`03-dashboard.png`、`03b-dashboard-manager.png`、`05-assets-list.png`、`07-filter-*.png`、`09-assets-detail.png`、`11-assets-new-*.png`、`12-project-list.png`、`12-project-detail.png`、`12-project-detail-2.png`（4.4 对比证据）、`13-contract-center*.png`、`14-ledger.png`、`15-analytics*.png`、`16-users/16-user-create-modal.png`、`17-organizations*.png`、`20-certificate-detail.png`（4.2 证据）、`24-global-search.png`、`25-notifications.png`、`26-after-logout.png`
- 结构化结果：`tmp/audit-0817/results_v2.json`（全模块 27 步 + console/pageerror/http 错误全集）、`results_v3/v4/v5.json`（定向核实 dumps）
- 脚本：`tmp/audit_ui_0817.js`（v1 登录链路发现）、`_v2.js`（全模块）、`_v3.js`～`_v6.js`（定向）
- 代码证据：`frontend/src/services/authService.ts:31`、`frontend/src/api/client.ts:461-527`、`frontend/src/pages/LoginPage.tsx:95-108`、`frontend/src/pages/PropertyCertificate/PropertyCertificateDetailPage.tsx:71,317`、`backend/src/constants/api_constants.py:100-113`、`frontend/src/pages/System/Organization/utils.tsx:102-123`

## 9. 建议修复顺序

1. **高**：4.1 登录错误路径（一改即闭环：登录请求豁免 refresh + 错误可见 + redirect 死码清理；建议补一条"错误密码 → 可见错误提示"的 e2e 断言防回归）；
2. **中**：4.2 产权证关联资产 UUID（page_size 修正，顺带把 4xx 排除出自动重试）；
3. **低**：4.3 组织树 value 告警、4.4 空数据空态；
4. **口径/数据治理**：§5.1 出租率舍入统一并入 2.7 待产品确认清单；§5.2 测试残留数据清理；§5.3 登录页本地化资源替换。
