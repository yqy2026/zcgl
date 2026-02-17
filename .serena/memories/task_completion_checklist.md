# 任务完成检查清单

## 代码修改后必须执行

### 1. 代码质量检查
```bash
make lint
make type-check
```

### 2. 运行相关测试
```bash
# 后端
cd backend
pytest -m unit tests/path/to/test_file.py

# 前端
cd frontend
pnpm test
```

### 3. 更新文档
- 更新 `CHANGELOG.md`
- 如有架构变更，更新相关文档

## 提交前检查
- [ ] 代码通过 lint 检查
- [ ] 代码通过类型检查
- [ ] 相关测试通过
- [ ] CHANGELOG.md 已更新
- [ ] 提交消息符合格式: `type(scope): description`
