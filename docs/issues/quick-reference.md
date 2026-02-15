# 问题快速参考

**最后更新**: 2026-02-14 | **详细文档**: [code-review-2026-02-14.md](./code-review-2026-02-14.md)

---

## 🔴 必须立即修复 (7项)

| # | 问题 | 位置 | 状态 |
|---|------|------|:----:|
| C-01 | Docker nginx 配置缺失 | `deployment/` | ⬜ |
| C-02 | 异常类重复定义 | `api/v1/assets/`, `exceptions.py` | ⬜ |
| C-03 | 敏感信息 stdout 输出 | `security/secret_validator.py` | ⬜ |
| C-04 | useEffect 无限循环风险 | `PromptDashboard.tsx` | ⬜ |
| C-05 | 空 catch 块吞掉错误 | 多处 | ⬜ |
| C-06 | index 作为 React key | 多处 | ⬜ |
| C-07 | E2E 测试认证状态为空 | `tests/e2e/storage/` | ⬜ |

---

## 🟠 尽快修复 (12项)

| # | 问题 | 位置 | 状态 |
|---|------|------|:----:|
| H-01 | Token 黑名单内存存储 | `token_blacklist.py` | ⬜ |
| H-02 | 全局变量滥用 | `asset_service.py` | ⬜ |
| H-03 | Any 类型过度使用 (318处) | 99个文件 | ⬜ |
| H-04 | useState 管理服务器数据 | `PromptDashboard.tsx` | ⬜ |
| H-05 | 缺少 useCallback 优化 | 多处 | ⬜ |
| H-06 | 类型断言滥用 | 测试文件 | ⬜ |
| H-07 | 隐式 any 类型 | 测试文件 | ⬜ |
| H-08 | 模型单元测试缺失 (6个) | `tests/unit/models/` | ⬜ |
| H-09 | Service 层测试缺失 | 2个服务 | ⬜ |
| H-10 | 前端覆盖率过低 (50%) | `vitest.config.ts` | ⬜ |
| H-11 | 测试标记文档不完整 | `CLAUDE.md` | ⬜ |
| H-12 | 轮询缺少失败计数 | 多处 | ⬜ |

---

## 🟡 建议修复 (15项)

| # | 问题 | 位置 | 状态 |
|---|------|------|:----:|
| M-01 | 重复代码 - 辅助函数 | `crud/asset.py` | ⬜ |
| M-02 | 硬编码中文字符串 | 多处 | ⬜ |
| M-03 | sys.stderr.write 调试输出 | 多处 | ⬜ |
| M-04 | 过长文件 (1156行) | `crud/asset.py` | ⬜ |
| M-05 | 大列表未虚拟化 | 前端全局 | ⬜ |
| M-06 | setTimeout 内存泄漏风险 | `usePDFImportSession.ts` | ⬜ |
| M-07 | 测试 Fixtures 重复 | 多个 conftest.py | ⬜ |
| M-08 | 迁移文件命名不一致 | `alembic/versions/` | ⬜ |
| M-09 | 类型忽略注解 | `config.py` | ⬜ |
| M-10 | 条件导入过多 | `api/v1/__init__.py` | ⬜ |
| M-11 | 缓存键可能冲突 | `crud/base.py` | ⬜ |
| M-12 | 冗余 pop 操作 | `crud/asset.py` | ⬜ |
| M-13 | Lint 禁用过多 | 前端全局 | ⬜ |
| M-14 | useEffect 依赖不完整 | `DictionaryPage.tsx` | ⬜ |
| M-15 | 测试中 index 作为 key | 测试文件 | ⬜ |

---

## 🟢 持续改进 (4+项)

| # | 问题 | 位置 | 状态 |
|---|------|------|:----:|
| L-01 | 导入顺序不规范 | `dependencies.py` | ⬜ |
| L-02 | 未使用的导入 | `asset_service.py` | ⬜ |
| L-03 | 注释与文档不一致 | 多处 | ⬜ |
| L-04 | 过多 console.log | 前端组件 | ⬜ |

---

## 📊 进度

```
严重: [----------] 0/7 (0%)
高危: [----------] 0/12 (0%)
中等: [----------] 0/15 (0%)
低危: [----------] 0/4 (0%)
总计: [----------] 0/38 (0%)
```

---

## 🎯 本周目标

- [ ] C-01: Docker nginx 配置
- [ ] C-02: 异常类重复定义
- [ ] C-04: useEffect 无限循环
- [ ] C-05: 空 catch 块

---

*状态标记: ⬜ 待处理 | 🔄 进行中 | ✅ 已完成*
