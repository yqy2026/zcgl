# V2.0 Release Notes

**发布日期**: 2026-01-08
**版本**: 2.0.0
**状态**: Historical Release Notes（2026-02-09）

> 说明：本文档用于记录 v2 版本历史发布信息。  
> 当前研发与验收基线请参考：`docs/requirements-specification.md`（相对路径：`../../requirements-specification.md`）。

---

## 🎉 新增功能

### 1. 项目和权属方独立详情页

**项目详情页** (`/project/:id`)
- 基本信息展示（项目名称、编号、状态、地址等）
- 关联资产列表（支持点击跳转）
- 统计卡片：资产总数、出租率、总面积

**权属方详情页** (`/ownership/:id`)
- 基本信息展示（名称、编号、简称等）
- 资产列表 + 合同列表（区分上游/下游）
- 财务统计占位（待后端 API 支持）

**技术实现**：
- 使用 React Query 进行数据获取和缓存
- 响应式布局，支持移动端
- 错误边界和加载状态管理

### 2. 站内消息通知系统

**通知中心组件**（右上角铃铛图标）
- 未读消息计数（红色角标）
- 下拉列表展示最近 10 条通知
- 自动刷新（列表 60s，计数 30s）
- 支持标记已读、删除操作

**通知类型**：
| 类型 | 说明 | 优先级 |
|------|------|--------|
| `contract_expiring` | 合同即将到期（30天内） | 根据剩余天数动态调整 |
| `contract_expired` | 合同已到期 | URGENT |
| `payment_overdue` | 付款逾期 | 根据逾期天数动态调整 |
| `payment_due` | 付款即将到期 | NORMAL |
| `system_notice` | 系统通知 | NORMAL |

**技术实现**：
- 后端：`Notification` ORM 模型 + 6个 REST API 端点
- 前端：`NotificationCenter` 组件 + `notificationService`
- 数据库：`notifications` 表（索引优化：`is_read`, `type`）

### 3. 企业微信集成

**功能**：
- 自动推送重要通知到企业微信群
- 支持文本和 Markdown 消息格式
- 失败重试和错误日志记录
- 可通过环境变量开关

**配置方法**：

在 `backend/.env` 中设置：
```bash
# 启用企业微信通知
WECOM_ENABLED=true

# 企业微信机器人 Webhook URL
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY

# 是否 @所有人（可选）
WECOM_MENTION_ALL=false
```

**获取 Webhook URL**：
1. 打开企业微信群聊
2. 点击群设置 → 群机器人
3. 添加机器人 → 复制 Webhook 地址

### 4. 合同到期自动扫描

**定时任务**：
- 扫描即将到期的合同（默认提前 30 天）
- 为所有活跃用户创建通知
- 支持手动触发测试

**API 端点**：
```http
POST /api/v1/notifications/run-tasks
Authorization: Bearer YOUR_TOKEN
```

**响应示例**：
```json
{
  "expiring_contracts": 3,
  "overdue_payments": 0,
  "due_payments": 0,
  "timestamp": "2026-01-08T13:02:17.845937"
}
```

---

## 📁 新增文件

### 前端
```
frontend/src/
├── pages/
│   ├── Project/ProjectDetailPage.tsx          (318 行)
│   └── Ownership/OwnershipDetailPage.tsx      (425 行)
├── components/Notification/
│   ├── NotificationCenter.tsx                  (237 行)
│   └── index.ts
└── services/
    └── notificationService.ts                  (178 行)
```

### 后端
```
backend/src/
├── models/
│   └── notification.py                         (110 行)
├── api/v1/
│   └── notifications.py                        (230 行)
└── services/notification/
    ├── __init__.py
    ├── scheduler.py                            (145 行)
    └── wecom_service.py                        (75 行)
```

### 数据库迁移
```
backend/alembic/versions/
└── a15055d892cb_add_notifications_table_and_wechat_.py
```

---

## 🔧 配置变更

### 1. 环境变量

新增以下配置项到 `backend/.env.example`：

```bash
# ==========================================
# 企业微信通知配置 (V2.0 新功能)
# ==========================================
WECOM_ENABLED=false
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY_HERE
WECOM_MENTION_ALL=false
```

### 2. 路由配置

在 `frontend/src/routes/AppRoutes.tsx` 中新增详情页路由：

```typescript
// 项目详情页（必须在列表页之前）
{
  path: '/project/:id',
  element: React.lazy(() => import('../pages/Project/ProjectDetailPage')),
}

// 权属方详情页（必须在列表页之前）
{
  path: '/ownership/:id',
  element: React.lazy(() => import('../pages/Ownership/OwnershipDetailPage')),
}
```

### 3. 数据库迁移

运行以下命令创建 `notifications` 表：

```bash
cd backend
alembic upgrade head
```

---

## 🚀 部署指南

### 1. 数据库迁移

```bash
cd backend
alembic upgrade head
```

验证表创建：
```bash
psql "$DATABASE_URL" -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='notifications';"
# 输出: notifications
```

### 2. 配置企业微信（可选）

编辑 `backend/.env`：
```bash
WECOM_ENABLED=true
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
```

### 3. 设置定时任务（生产环境）

**方式一：cron 任务**
```bash
# 每 6 小时扫描一次
0 */6 * * * curl -X POST http://localhost:8002/api/v1/notifications/run-tasks \
  -H "Authorization: Bearer YOUR_SERVICE_TOKEN"
```

**方式二：APScheduler（推荐）**
```python
# 在 backend/src/main.py 中添加
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    run_notification_tasks,
    'interval',
    hours=6,
    id='notification_scan'
)
scheduler.start()
```

### 4. 验证部署

**后端**：
```bash
cd backend
python run_dev.py
# 访问 http://localhost:8002/docs
# 查找 "通知管理" 标签下的 6 个端点
```

**前端**：
```bash
cd frontend
npm run dev
# 登录后点击右上角铃铛图标
# 应能看到通知中心下拉列表
```

---

## 📋 API 端点清单

| 方法 | 端点 | 功能 | 权限 |
|------|------|------|------|
| GET | `/api/v1/notifications/` | 获取通知列表（分页） | 登录用户 |
| GET | `/api/v1/notifications/unread-count` | 获取未读数量 | 登录用户 |
| POST | `/api/v1/notifications/{id}/read` | 标记单条已读 | 登录用户 |
| POST | `/api/v1/notifications/read-all` | 标记全部已读 | 登录用户 |
| DELETE | `/api/v1/notifications/{id}` | 删除通知 | 登录用户 |
| POST | `/api/v1/notifications/run-tasks` | 手动触发扫描 | 登录用户 |

---

## 🐛 已知问题

1. **付款追踪功能暂未启用**
   - 原因：缺少 `RentLedger` 模型
   - 影响：`PAYMENT_OVERDUE` 和 `PAYMENT_DUE` 通知类型暂不可用
   - 解决方案：待 `RentLedger` 模型实现后，在 `scheduler.py` 中取消注释相关代码

2. **财务统计图表占位**
   - 权属方详情页的财务统计部分目前显示占位信息
   - 需要后端提供收入/支出统计 API

---

## 🔮 后续规划

1. **RentLedger 模型实现**（P1）
   - 完成付款台账功能
   - 启用付款逾期和到期提醒

2. **通知模板系统**（P2）
   - 支持自定义通知消息模板
   - 多语言支持

3. **通知偏好设置**（P3）
   - 用户可配置接收哪些类型的通知
   - 通知频率控制

---

## 📞 支持

如有问题，请查阅：
- [API 文档](http://localhost:8002/docs)
- [V2.0 升级计划（归档）](../plans/v2-upgrade-plan-2026-02.md)
- [测试用例文档（归档）](../testing/v2-test-cases-2026-02.md)

---

**V2.0 升级实施完成！** 🎉
