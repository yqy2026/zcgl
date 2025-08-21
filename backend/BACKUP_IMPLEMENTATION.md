# 数据备份和恢复功能实现文档

## 概述

本文档描述了土地物业资产管理系统中数据备份和恢复功能的完整实现。该功能提供了数据库的自动和手动备份、恢复、管理和清理功能。

## 功能特性

### 核心功能
- ✅ **数据库完整备份** - 支持SQLite数据库的完整备份
- ✅ **压缩备份** - 使用gzip压缩减少存储空间
- ✅ **备份文件管理** - 列出、查询、删除备份文件
- ✅ **数据库恢复** - 从备份文件恢复数据库
- ✅ **自动备份调度** - 定时自动创建备份
- ✅ **异步备份** - 支持后台异步备份操作
- ✅ **备份验证** - 验证恢复的数据库完整性
- ✅ **安全恢复** - 恢复前创建安全备份，失败时自动回滚

### 高级功能
- ✅ **备份清理** - 自动清理过期和超量备份
- ✅ **备份配置** - 灵活的备份策略配置
- ✅ **API接口** - 完整的RESTful API支持
- ✅ **错误处理** - 完善的异常处理和日志记录

## 架构设计

### 组件结构

```
backend/src/
├── services/
│   └── backup_service.py          # 备份服务核心实现
├── api/v1/
│   └── backup.py                   # 备份API端点
├── schemas/
│   └── backup.py                   # 备份相关数据模型
└── tests/
    └── test_backup.py              # 备份功能测试
```

### 核心类

#### 1. BackupConfig
备份配置管理类，负责管理备份策略和参数。

```python
class BackupConfig:
    def __init__(self):
        self.backup_dir = Path("backups")           # 备份目录
        self.max_backups = 30                       # 最大备份数量
        self.compress = True                        # 是否压缩
        self.auto_backup_enabled = True             # 自动备份开关
        self.backup_interval_hours = 24             # 备份间隔（小时）
        self.backup_retention_days = 30             # 备份保留天数
```

#### 2. DatabaseBackupService
数据库备份服务主类，提供所有备份相关功能。

**主要方法：**
- `create_backup()` - 创建备份
- `create_backup_async()` - 异步创建备份
- `restore_backup()` - 恢复备份
- `list_backups()` - 列出备份
- `delete_backup()` - 删除备份
- `get_backup_info()` - 获取备份信息
- `cleanup_old_backups()` - 清理过期备份

#### 3. AutoBackupScheduler
自动备份调度器，负责定时执行备份任务。

**主要方法：**
- `start_scheduler()` - 启动调度器
- `stop_scheduler()` - 停止调度器
- `_should_create_backup()` - 判断是否需要备份

## API接口

### 备份管理端点

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/backup/create` | 创建备份 |
| GET | `/api/v1/backup/list` | 列出所有备份 |
| GET | `/api/v1/backup/info/{filename}` | 获取备份详细信息 |
| POST | `/api/v1/backup/restore` | 恢复备份 |
| DELETE | `/api/v1/backup/{filename}` | 删除备份 |
| POST | `/api/v1/backup/cleanup` | 清理过期备份 |
| GET | `/api/v1/backup/scheduler/status` | 获取调度器状态 |

### 请求/响应示例

#### 创建备份
```bash
curl -X POST "http://localhost:8001/api/v1/backup/create" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "手动备份",
    "async_backup": false
  }'
```

**响应：**
```json
{
  "success": true,
  "message": "备份创建成功",
  "backup_info": {
    "filename": "backup_20250802_083333.db.gz",
    "file_path": "backups/backup_20250802_083333.db.gz",
    "file_size": 1024,
    "timestamp": "2025-08-02T08:33:33",
    "created_at": "2025-08-02T08:33:33",
    "description": "手动备份",
    "is_compressed": true,
    "backup_type": "full"
  },
  "async_backup": false
}
```

#### 列出备份
```bash
curl -X GET "http://localhost:8001/api/v1/backup/list"
```

**响应：**
```json
{
  "success": true,
  "message": "找到 3 个备份文件",
  "backups": [
    {
      "filename": "backup_20250802_083333.db.gz",
      "file_path": "backups/backup_20250802_083333.db.gz",
      "file_size": 1024,
      "timestamp": "2025-08-02T08:33:33",
      "created_at": "2025-08-02T08:33:33",
      "description": "手动备份",
      "is_compressed": true,
      "backup_type": "full"
    }
  ],
  "total_count": 3
}
```

#### 恢复备份
```bash
curl -X POST "http://localhost:8001/api/v1/backup/restore" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_filename": "backup_20250802_083333.db.gz",
    "confirm": true
  }'
```

**响应：**
```json
{
  "success": true,
  "message": "数据库恢复成功",
  "restored": true,
  "safety_backup": "land_property.db.safety_20250802_083400"
}
```

## 数据模型

### BackupRequest
```python
class BackupRequest(BaseModel):
    description: Optional[str] = None    # 备份描述
    async_backup: bool = False           # 是否异步备份
```

### BackupInfo
```python
class BackupInfo(BaseModel):
    filename: str                        # 备份文件名
    file_path: str                       # 备份文件路径
    file_size: int                       # 文件大小（字节）
    timestamp: str                       # 备份时间戳
    created_at: str                      # 创建时间
    description: str                     # 备份描述
    is_compressed: bool                  # 是否压缩
    backup_type: str                     # 备份类型
    original_size: Optional[int] = None  # 原始大小（压缩文件）
```

### RestoreRequest
```python
class RestoreRequest(BaseModel):
    backup_filename: str                 # 要恢复的备份文件名
    confirm: bool = False                # 确认恢复操作
```

## 备份策略

### 文件命名规则
备份文件使用以下命名格式：
```
backup_YYYYMMDD_HHMMSS.db[.gz]
```

示例：
- `backup_20250802_083333.db.gz` - 压缩备份
- `backup_20250802_083333.db` - 非压缩备份

### 自动清理策略
系统会根据以下规则自动清理备份：

1. **数量限制** - 超过 `max_backups` 数量时，删除最旧的备份
2. **时间限制** - 删除超过 `backup_retention_days` 天的备份
3. **清理时机** - 每次创建新备份时自动执行清理

### 备份验证
恢复备份时会进行以下验证：

1. **文件完整性** - 检查备份文件是否可读
2. **数据库结构** - 验证必要的表是否存在
3. **连接测试** - 确保数据库可以正常连接

必要的表：
- `assets` - 资产表
- `asset_history` - 资产历史表

## 安全特性

### 恢复安全机制
1. **确认机制** - 恢复操作需要明确的确认参数
2. **安全备份** - 恢复前自动创建当前数据库的安全备份
3. **自动回滚** - 恢复失败时自动回滚到安全备份
4. **验证检查** - 恢复后验证数据库完整性

### 错误处理
- **异常捕获** - 完善的异常处理机制
- **日志记录** - 详细的操作日志
- **状态返回** - 明确的成功/失败状态
- **错误信息** - 用户友好的错误提示

## 性能优化

### 压缩优化
- 使用gzip压缩减少存储空间
- 压缩率通常可达到70-80%
- 支持压缩和非压缩两种模式

### 异步处理
- 支持后台异步备份
- 避免阻塞主线程
- 使用线程池处理并发备份

### 文件操作优化
- 使用流式复制减少内存占用
- 批量文件操作提高效率
- 智能清理策略减少磁盘占用

## 使用示例

### 基本使用
```python
from src.services.backup_service import DatabaseBackupService, BackupConfig

# 创建备份服务
config = BackupConfig()
backup_service = DatabaseBackupService(config)

# 创建备份
result = backup_service.create_backup("手动备份")
if result["success"]:
    print(f"备份创建成功: {result['backup_info']['filename']}")

# 列出备份
backups = backup_service.list_backups()
for backup in backups["backups"]:
    print(f"备份: {backup['filename']} ({backup['file_size']} 字节)")

# 恢复备份
restore_result = backup_service.restore_backup("backup_20250802_083333.db.gz", confirm=True)
if restore_result["success"]:
    print("数据库恢复成功")
```

### 异步使用
```python
import asyncio

async def async_backup_example():
    # 异步创建备份
    result = await backup_service.create_backup_async("异步备份")
    if result["success"]:
        print(f"异步备份完成: {result['backup_info']['filename']}")

# 运行异步备份
asyncio.run(async_backup_example())
```

### 自动备份调度
```python
from src.services.backup_service import AutoBackupScheduler

# 创建调度器
scheduler = AutoBackupScheduler(backup_service)

# 启动自动备份（在后台运行）
async def start_auto_backup():
    await scheduler.start_scheduler()

# 停止自动备份
scheduler.stop_scheduler()
```

## 测试

### 运行测试
```bash
# 运行完整测试套件
python -m pytest tests/test_backup.py -v

# 运行简化功能测试
python test_backup_simple.py

# 运行演示程序
python test_backup_demo.py
```

### 测试覆盖
- ✅ 备份创建（压缩/非压缩）
- ✅ 备份列表和信息查询
- ✅ 备份删除和清理
- ✅ 数据库验证
- ✅ 恢复功能（模拟）
- ✅ 异步操作
- ✅ 调度器功能
- ✅ API集成
- ✅ 错误处理

## 配置说明

### 环境变量
```bash
# 数据库URL（自动从现有配置读取）
DATABASE_URL=sqlite:///land_property.db
```

### 配置文件
备份配置可以通过修改 `BackupConfig` 类进行调整：

```python
config = BackupConfig()
config.backup_dir = Path("custom_backups")    # 自定义备份目录
config.max_backups = 50                       # 增加最大备份数量
config.compress = False                       # 禁用压缩
config.backup_interval_hours = 12             # 12小时备份一次
config.backup_retention_days = 60             # 保留60天
```

## 故障排除

### 常见问题

1. **备份创建失败**
   - 检查数据库文件是否存在
   - 确认备份目录权限
   - 查看日志文件获取详细错误信息

2. **恢复失败**
   - 确认备份文件完整性
   - 检查数据库文件权限
   - 验证备份文件格式

3. **自动备份不工作**
   - 检查调度器是否启动
   - 确认自动备份配置已启用
   - 查看调度器日志

### 日志查看
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

## 扩展功能

### 未来改进方向
- 🔄 增量备份支持
- 🔄 远程备份存储（云存储）
- 🔄 备份加密功能
- 🔄 备份完整性校验
- 🔄 多数据库类型支持
- 🔄 备份元数据管理
- 🔄 Web界面管理
- 🔄 备份性能监控

## 总结

数据备份和恢复功能已完全实现并通过测试。该功能提供了：

- **完整的备份解决方案** - 从手动备份到自动调度
- **安全的恢复机制** - 包含验证和回滚功能
- **灵活的配置选项** - 适应不同的备份需求
- **完善的API接口** - 支持前端集成
- **详细的错误处理** - 确保系统稳定性

该功能为土地物业资产管理系统提供了可靠的数据保护机制，确保重要数据的安全性和可恢复性。