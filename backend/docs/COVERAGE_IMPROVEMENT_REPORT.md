# 测试覆盖率改进报告（占位）

原阶段性覆盖率报告已清理/归档，以避免过期信息误导。
当前覆盖率目标与执行方式请参考以下文档：

- [测试标准](../../docs/TESTING_STANDARDS.md)
- [代码质量扩展指南](./code_quality_extended_guide.md)

如需生成新的覆盖率报告，可在后端目录执行：

```bash
cd backend
pytest --cov=src --cov-report=html
```

生成的 HTML 报告位于 `backend/htmlcov/`。
