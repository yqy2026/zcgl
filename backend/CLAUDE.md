# Backend CLAUDE.md

后端开发专用指南。通用信息请参阅根目录 `CLAUDE.md`。

---

## 快速开始

```bash
cd backend
python run_dev.py       # 启动开发服务器 (port 8002)
pytest                  # 运行测试
ruff check . && ruff format .  # Lint + 格式化
```

---

## 分层架构

```
请求 → api/v1/ → services/ → crud/ → models/
              ↑ 业务逻辑    ↑ 数据库操作
```

**核心原则**: 业务逻辑 **必须** 放在 `services/`，不要放在 API 端点中。

---

## 添加新功能

### 1. 创建 Schema (`schemas/my_feature.py`)

```python
from pydantic import BaseModel

class MyFeatureCreate(BaseModel):
    name: str

class MyFeatureResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
```

### 2. 创建 Model (`models/my_feature.py`)

```python
from src.models.base import Base
from sqlalchemy import Column, Integer, String

class MyFeature(Base):
    __tablename__ = "my_features"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
```

### 3. 创建 CRUD (`crud/my_feature.py`)

```python
from src.crud.base import CRUDBase
from src.models.my_feature import MyFeature
from src.schemas.my_feature import MyFeatureCreate

class CRUDMyFeature(CRUDBase[MyFeature, MyFeatureCreate, MyFeatureCreate]):
    pass

my_feature_crud = CRUDMyFeature(MyFeature)
```

### 4. 创建 Service (`services/my_feature/my_feature_service.py`)

```python
from sqlalchemy.orm import Session
from src.crud.my_feature import my_feature_crud

class MyFeatureService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict):
        return my_feature_crud.create(self.db, obj_in=data)
```

### 5. 创建 API 端点 (`api/v1/my_feature.py`)

```python
from fastapi import APIRouter, Depends
from src.core.router_registry import route_registry
from src.services.my_feature.my_feature_service import MyFeatureService

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.get("/")
async def get_all(service: MyFeatureService = Depends(get_service)):
    return service.get_all()

# 自动注册路由
route_registry.register_router(router, prefix="/api/v1", tags=["My Feature"], version="v1")
```

---

## 数据加密

系统支持对 PII (Personally Identifiable Information) 字段进行加密存储。

### 加密字段

| 字段 | 类型 | 加密方式 | 说明 |
|------|------|----------|------|
| `tenant_name` | 可搜索 PII | AES-256-SIV (确定性) | 租户名称 |
| `ownership_entity` | 可搜索 PII | AES-256-SIV (确定性) | 权属方 |
| `address` | 可搜索 PII | AES-256-SIV (确定性) | 物业地址 |
| `manager_name` | 非搜索 PII | AES-256-GCM (标准) | 管理责任人 |

### 加密方式

- **确定性加密 (AES-256-SIV)**: 相同明文产生相同密文，支持数据库搜索和精确匹配
- **标准加密 (AES-256-GCM)**: 相同明文产生不同密文（随机 nonce），安全性更高

### 加密策略

- **写入时加密**: 新创建和更新的记录自动加密 PII 字段
- **读取时解密**: 从数据库读取时自动解密，对应用层透明
- **现有数据**: 保持明文直到下次更新（encrypt-on-write 策略）
- **优雅降级**: 密钥缺失时禁用加密，数据以明文存储

### 配置

#### 1. 生成加密密钥

```bash
cd backend
python -m src.core.encryption
```

输出示例:
```
Generating new encryption key...

Add this to your .env file:
----------------------------------------------------------------------
DATA_ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwMTIzOjE="
----------------------------------------------------------------------

⚠️  IMPORTANT SECURITY NOTES:
   • Keep this key secure and never commit it to version control
   • Store it in a secure secrets manager in production
   • Use different keys for development, staging, and production
   • Rotate keys periodically (increment version number)
   • Test key recovery procedures before production deployment
```

#### 2. 配置环境变量

将生成的密钥添加到 `.env` 文件:

```bash
DATA_ENCRYPTION_KEY="<your_generated_key>"
```

#### 3. 验证加密状态

```python
from src.crud.asset import asset_crud

print(f"Encryption enabled: {asset_crud.sensitive_data_handler.encryption_enabled}")
```

### 密钥管理

#### 开发/测试环境

```bash
# 使用生成的密钥
DATA_ENCRYPTION_KEY="test-key-for-development-only:1"
```

#### 生产环境

**推荐做法**:
- 使用 AWS KMS、HashiCorp Vault 等密钥管理服务
- 不同环境使用不同密钥
- 定期轮换密钥（通过递增版本号）
- 测试密钥恢复流程

**密钥格式**:
```
{base64_encoded_key}:{version}
```

示例:
```
MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzOjE=
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^ ^
                  32字节密钥 (base64)                  版本号
```

### 密钥轮换

系统支持多版本密钥（未来功能）:

1. 生成新密钥: `DATA_ENCRYPTION_KEY_V2="new-key:2"`
2. 应用自动使用新密钥加密新数据
3. 旧数据在下次更新时自动用新密钥重新加密
4. 可选: 运行后台任务批量重新加密所有数据

### 安全注意事项

⚠️ **重要**:
- 永远不要将加密密钥提交到版本控制
- 生产环境必须使用强随机密钥
- 定期审计密钥访问权限
- 监控加密/解密操作日志
- 制定密钥泄露应急响应计划

### 测试

```bash
# 单元测试
pytest tests/unit/core/test_encryption.py -v

# 集成测试
pytest tests/integration/crud/test_asset_encryption.py -v

# 验证加密功能
pytest -k "encryption" -v
```

---

## 可选依赖处理

```python
from src.core.import_utils import safe_import

# 关键依赖 - 缺失时生产环境会失败
router_registry = safe_import("core.router_registry", critical=True)

# 可选依赖 - 优雅降级
ocr = safe_import("services.ocr", fallback=None)
if ocr:
    # 使用 OCR
else:
    # 提供回退方案
```

---

## 测试

```bash
pytest -m unit              # 单元测试 (快速)
pytest -m integration       # 集成测试 (含数据库)
pytest -m api               # API 端点测试
pytest -m "not slow"        # 排除慢测试
pytest --cov=src --cov-report=html  # 覆盖率
```

测试文件位置: `tests/unit/`, `tests/integration/`

---

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| Import 错误 | `pip install -e .` |
| 数据库连接失败 | 确保 `database/data/` 存在 |
| Alembic 失败 | `alembic stamp head && alembic upgrade head` |
| 加密未生效 | 检查 `DATA_ENCRYPTION_KEY` 是否设置 |
| 搜索加密字段失败 | 确保使用确定性加密（SEARCHABLE_FIELDS） |


<claude-mem-context>
# Recent Activity

<!-- This section is auto-generated by claude-mem. Edit content outside the tags. -->

*No recent activity*
</claude-mem-context>
