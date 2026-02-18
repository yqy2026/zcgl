# Git 冲突处理复盘（2026-02）

> 本文件从 `AGENTS.md` 外迁，记录 2026 年 2 月 Git 冲突事故的经验教训与标准化流程。

---

## 必须遵守的规则

- 本地存在大量未提交改动时，**先做双重备份**再同步远端：`备份分支 + WIP 提交 + patch 导出`
- 不要直接使用"一键偏向"策略（如 `rebase -X theirs/ours`）后立即推送；必须人工复核冲突文件
- `modify/delete` 冲突必须单独审查：先查 `git log -- <file>` 和最近删除提交，再决定保留删除还是恢复文件
- 涉及模型聚合文件（如 `models/__init__.py`、`models/asset.py`）时，优先防止重复定义/重复建表
- 不在主工作分支直接硬解冲突：优先在临时备份分支完成 rebase 与验证，再回灌目标分支

---

## 推荐流程（标准化）

1. **记录现场并建备份**：
   - `git status -sb`、`git rev-parse --short HEAD`
   - `git switch -c backup/pre-sync-<timestamp>`
   - `git add -A && git commit -m "chore(wip): backup before remote sync"`
   - `git format-patch -1 HEAD --stdout > ../pre-sync-wip-<timestamp>.patch`
2. 先 `git fetch`，确认分叉，再在备份分支执行 `git rebase origin/<branch>`
3. **冲突分类处理**：
   - `content (UU)`：逐块合并，保留双方有效改动
   - `modify/delete (DU)`：先确认"删除是否为架构收口"，避免误恢复历史文件
4. **测试冲突语义校验**：
   - 若远端引入新 schema/响应约束（如 `UserResponse.phone` 必填），优先对齐远端测试基线，再补本地语义
   - 避免"仅能过冲突但语义过时"的测试文件被保留
5. **合并完成后最小验证**：
   - `rg -n "^(<<<<<<<|=======|>>>>>>>)"` 确认无冲突标记
   - 关键模块导入烟测（特别是 `backend/src/models`、`backend/src/crud`）
   - `ruff check` + 受影响测试最小集
6. 验证通过后回灌主分支：
   - `git switch <target-branch>`
   - `git merge --ff-only backup/pre-sync-<timestamp>`
7. 推送前输出"冲突清单 + 处理决策 + 风险点 + 验证结果"；推送成功后再清理临时分支与 patch

---

## 事故教训

- 自动偏向策略会掩盖结构性冲突：可能导致误恢复已删除文件、跨模块导入漂移、模型重复定义
- "能提交"不等于"语义正确"：必须加导入烟测和关键路径回归测试
- 测试冲突不应机械"保留本地"：需先判断是否已被远端模型/接口演进淘汰
- "备份分支先解冲突 + 主分支快进回灌"可显著降低二次修复与回滚成本

---

## 启动排查经验

> 以下为开发过程中积累的排查经验，供定位问题时参考。

- 后端开发请使用项目虚拟环境 `backend/.venv`（避免系统/Anaconda 导致 `.env` 不生效或 CORS/依赖异常）
- 后端启动建议：`cd backend && .\.venv\Scripts\python.exe run_dev.py`
- 若 8002 被占用可临时切换端口（例如 8003），需要同步调整前端代理或 API_BASE_URL
- 前端推荐保持 `VITE_API_BASE_URL=/api/v1` + Vite 代理，避免跨域
- `/system/users` 报错常见原因：
  - CORS 预检未允许 `Authorization` 头，需在后端 CORS 允许头中加入 `Authorization`
  - CORS 中间件需包裹错误响应（放在中间件链最外层）
- `/api/v1/roles` 的 `MissingGreenlet` 多由角色权限懒加载触发，需在 role CRUD 用 `selectinload(Role.permissions)` 预加载
- `/api/v1/auth/users` 若使用 `DISTINCT` 包含 JSON 列会触发 Postgres "json 无等号"错误，应改为 `distinct(User.id)` 并独立 count
- RBAC 初始化脚本：`backend/scripts/setup/init_rbac_data.py` 可反复执行并补齐权限（包含 `property_certificate`）
- 若数据库仍存在遗留列 `users.role` 或 `assets.ownership_entity`，先执行 `alembic upgrade head` 移除后再初始化 RBAC
- Playwright 调试建议使用 `npx --yes @playwright/cli`，产物统一放在 `output/playwright/`
