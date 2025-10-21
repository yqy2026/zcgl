# 安全模块文档

## 概述

安全模块提供了全面的安全防护功能，包括文件上传验证、请求频率限制、安全中间件和安全审计等功能。

## 核心组件

### 1. 文件验证器 (FileValidator)

负责验证上传文件的安全性和有效性。

#### 主要功能：
- 文件类型验证（MIME类型和扩展名匹配）
- 文件大小限制
- 文件名安全性检查
- 恶意内容扫描
- 文件哈希计算

#### 使用示例：
```python
from src.core.security import security_middleware

# 验证文件上传
validation_result = await security_middleware.validate_file_upload(
    file,
    allowed_types=['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    max_size=50 * 1024 * 1024  # 50MB
)
```

### 2. 请求频率限制器 (RateLimiter)

实施基于IP和请求类型的频率限制，防止恶意请求和DDoS攻击。

#### 限制策略：
- PDF导入：每分钟最多5次
- Excel操作：每分钟最多10次
- POST请求：每分钟最多30次
- 一般请求：每分钟最多100次

#### 使用示例：
```python
from src.core.security import RateLimiter

rate_limiter = RateLimiter()

# 检查频率限制
if rate_limiter.check_rate_limit(client_ip, 100, 60):
    # 允许请求
    pass
else:
    # 拒绝请求
    raise HTTPException(status_code=429, detail="请求过于频繁")
```

### 3. 安全中间件 (SecurityMiddleware)

提供请求级别的安全验证和防护。

#### 功能特性：
- IP黑名单检查
- 请求频率限制
- User-Agent验证
- 可疑请求检测
- 安全事件记录

#### 中间件配置：
```python
from src.middleware.security_middleware import setup_security_middleware

# 在主应用中设置安全中间件
setup_security_middleware(app)
```

### 4. 请求安全工具 (RequestSecurity)

提供输入数据清理和验证工具。

#### 主要方法：
```python
from src.core.security import RequestSecurity

# 清理输入数据
clean_input = RequestSecurity.sanitize_input(user_input)

# 验证邮箱格式
is_valid_email = RequestSecurity.validate_email(email)

# 验证手机号格式
is_valid_phone = RequestSecurity.validate_phone(phone)

# 检查URL安全性
is_safe_url = RequestSecurity.is_safe_url(url)
```

## 安全配置

### 环境变量配置

```bash
# 安全配置
SECURITY_ENABLED=true
MAX_FILE_SIZE=104857600  # 100MB
RATE_LIMIT_ENABLED=true

# IP黑名单
IP_BLACKLIST=192.168.1.100,10.0.0.50

# 允许的文件类型
ALLOWED_FILE_TYPES=pdf,xlsx,xls,csv,json

# CORS配置
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 配置文件示例

```python
# config/security.py
SECURITY_CONFIG = {
    "allowed_origins": ["http://localhost:5173", "http://localhost:3000"],
    "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "max_file_size": 100 * 1024 * 1024,  # 100MB
    "rate_limit": {
        "pdf_import": {"max_requests": 5, "time_window": 60},
        "excel": {"max_requests": 10, "time_window": 60},
        "post": {"max_requests": 30, "time_window": 60},
        "default": {"max_requests": 100, "time_window": 60}
    },
    "ip_blacklist": ["192.168.1.100", "10.0.0.50"],
    "malicious_signatures": [
        b'<?php', b'<script', b'javascript:', b'vbscript:'
    ]
}
```

## 安全审计

### 审计事件类型

- `FILE_VALIDATION_SUCCESS` - 文件验证成功
- `FILE_VALIDATION_FAILED` - 文件验证失败
- `RATE_LIMIT_EXCEEDED` - 频率限制超出
- `REQUEST_BLOCKED` - 请求被拦截
- `SUSPICIOUS_REQUEST` - 可疑请求
- `EXCEL_IMPORT_STARTED` - Excel导入开始
- `EXCEL_ASYNC_IMPORT_STARTED` - 异步Excel导入开始

### 审计日志示例

```json
{
  "timestamp": "2025-01-01T12:00:00Z",
  "event_type": "FILE_VALIDATION_SUCCESS",
  "details": {
    "filename": "data.xlsx",
    "size": 1048576,
    "hash": "a1b2c3d4e5f6...",
    "validation_time": "2025-01-01T12:00:00Z"
  },
  "user_id": "user123",
  "ip_address": "192.168.1.100"
}
```

## 文件上传安全

### 支持的文件类型

| MIME类型 | 扩展名 | 描述 |
|---------|--------|------|
| application/pdf | .pdf | PDF文档 |
| application/vnd.openxmlformats-officedocument.spreadsheetml.sheet | .xlsx | Excel文件 |
| application/vnd.ms-excel | .xls | Excel文件（旧版） |
| text/csv | .csv | CSV文件 |
| application/json | .json | JSON文件 |
| image/jpeg | .jpg,.jpeg | JPEG图片 |
| image/png | .png | PNG图片 |
| image/tiff | .tiff,.tif | TIFF图片 |

### 文件大小限制

- PDF文件：50MB
- Excel文件：100MB
- 图片文件：20MB
- 其他文件：10MB

### 安全检查项目

1. **文件扩展名验证** - 检查是否在允许列表中
2. **MIME类型验证** - 使用python-magic检测真实文件类型
3. **文件名安全检查** - 防止路径遍历和特殊字符
4. **恶意内容扫描** - 检测已知的恶意签名
5. **文件大小限制** - 防止大文件攻击
6. **文件哈希计算** - 用于完整性和重复检测

## 部署注意事项

### 系统依赖

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install libmagic1
```

**CentOS/RHEL:**
```bash
sudo yum install file-devel
```

**macOS:**
```bash
brew install libmagic
```

**Windows:**
```bash
pip install python-magic-bin
```

### 生产环境配置

1. **启用所有安全中间件**
2. **配置适当的文件大小限制**
3. **设置严格的CORS策略**
4. **启用安全日志记录**
5. **配置监控和告警**

### 性能考虑

- 文件验证会增加处理时间，建议使用异步处理
- 频率限制器使用内存存储，重启会丢失数据
- 安全审计日志可能产生大量数据，需要定期清理

## 测试

运行安全模块测试：

```bash
cd backend
uv run python -m pytest tests/test_security.py -v
```

测试覆盖：
- 文件验证功能
- 频率限制机制
- 输入清理和验证
- 安全中间件功能
- 集成测试

## 故障排除

### 常见问题

1. **python-magic导入错误**
   - 确保安装了系统依赖
   - Windows用户需要安装python-magic-bin

2. **文件验证失败**
   - 检查文件类型是否在允许列表中
   - 确认文件大小不超过限制
   - 验证文件名不包含非法字符

3. **频率限制过于严格**
   - 调整配置中的限制参数
   - 检查IP获取是否正确

4. **安全审计日志过多**
   - 调整日志级别
   - 实施日志轮转策略

### 调试模式

启用调试模式获取详细的安全日志：

```python
import logging
logging.getLogger("src.core.security").setLevel(logging.DEBUG)
```

## 最佳实践

1. **定期更新恶意签名库**
2. **监控安全事件日志**
3. **实施最小权限原则**
4. **定期进行安全审计**
5. **保持依赖库更新**
6. **实施安全代码审查**
7. **使用HTTPS传输**
8. **定期备份重要数据**