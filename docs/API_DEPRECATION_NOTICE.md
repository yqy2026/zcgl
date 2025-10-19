# API废弃声明

## 概述

本文档记录了系统中已废弃的API端点及其迁移指南。

## 废弃的API端点

### 1. 系统字典兼容性API

**端点前缀**: `/api/v1/system-dictionaries-compat/`
**废弃日期**: 2025年10月16日
**计划移除日期**: 2025年12月31日
**状态**: 🚨 已废弃

#### 废弃原因

为了统一字典管理，减少代码重复，提高系统维护性。旧的系统字典API已被新的统一字典管理API替代。

#### 受影响的端点

- `GET /api/v1/system-dictionaries-compat/` - 获取系统字典列表
- `POST /api/v1/system-dictionaries-compat/` - 创建系统字典项
- `GET /api/v1/system-dictionaries-compat/migration-status` - 获取迁移状态
- `POST /api/v1/system-dictionaries-compat/migrate` - 触发数据迁移

#### 迁移指南

**新的推荐端点**: `/api/v1/dictionaries/`

**迁移映射**:

| 旧端点 | 新端点 | 说明 |
|--------|--------|------|
| `GET /api/v1/system-dictionaries-compat/?dict_type=X` | `GET /api/v1/dictionaries/X/options` | 获取字典选项 |
| `POST /api/v1/system-dictionaries-compat/` | `POST /api/v1/dictionaries/` | 创建字典 |
| 字典项创建 | `POST /api/v1/dictionaries/{type}/values` | 添加字典值 |

**代码迁移示例**:

```typescript
// 旧的API调用
const oldAPI = await fetch('/api/v1/system-dictionaries-compat/?dict_type=property_type');

// 新的API调用
const newAPI = await fetch('/api/v1/dictionaries/property_type/options');
```

**Python后端迁移示例**:

```python
# 旧的API调用
response = client.get("/api/v1/system-dictionaries-compat/", params={"dict_type": "property_type"})

# 新的API调用
response = client.get("/api/v1/dictionaries/property_type/options")
```

## 迁移时间线

- **2025年10月16日**: API废弃声明发布，开始废弃过渡期
- **2025年11月30日**: 停止对废弃API的功能支持
- **2025年12月31日**: 完全移除废弃API端点

## 建议

1. **立即迁移**: 建议立即开始使用新的API端点
2. **测试验证**: 在生产环境迁移前，请在开发环境充分测试
3. **更新文档**: 更新相关技术文档和API使用说明
4. **团队培训**: 通知开发团队关于API变更的信息

## 支持

如有迁移相关问题，请联系技术团队或查看：
- [统一字典管理API文档](http://localhost:8002/docs)
- [系统架构文档](../docs/)
- 技术支持群组

---

**更新时间**: 2025年10月16日
**版本**: v1.0
**状态**: 生效中