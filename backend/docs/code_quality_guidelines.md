# 🚀 代码质量最佳实践指南

## 📖 概述

本指南旨在为土地物业资产管理系统（iFlow）的开发团队提供代码质量最佳实践，确保代码的可维护性、可读性和可靠性。通过遵循这些指南，我们可以保持高标准的代码质量，减少技术债务，提高开发效率。

## 🎯 代码质量目标

### 核心目标
- **可读性**: 代码应该易于理解和维护
- **可靠性**: 代码应该稳定运行，错误处理完善
- **可维护性**: 代码结构清晰，便于修改和扩展
- **性能**: 代码应该高效运行，避免不必要的资源浪费
- **安全性**: 代码应该防范常见的安全漏洞

### 量化指标
| 指标 | 目标值 | 工具 | 检查频率 |
|------|--------|------|----------|
| 代码复杂度 | ≤ 8.0 | Radon | 每次提交 |
| 代码重复度 | ≤ 3.0% | JSCPD | 每日 |
| 类型错误 | ≤ 2 | MyPy | 每次提交 |
| 安全问题 | 0 | Bandit | 每次提交 |
| 单元测试覆盖率 | ≥ 80% | pytest-cov | 每次PR |

## 🔧 开发环境配置

### 必需工具安装
```bash
# 安装UV包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
cd backend
uv sync --dev

# 安装pre-commit钩子
uv run pre-commit install
```

### VS Code 配置
推荐安装以下扩展：
- Python
- Ruff
- MyPy
- GitLens
- Error Lens

`.vscode/settings.json` 配置：
```json
{
    "python.defaultInterpreterPath": "./backend/.venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.fixAll.ruff": true,
        "source.organizeImports.ruff": true
    }
}
```

## 📝 编码规范

### 1. 命名规范

#### 变量命名
```python
# ✅ 好的命名
user_count: int = 0
is_valid: bool = True
asset_data: dict = {}
max_retry_attempts: int = 3

# ❌ 不好的命名
n: int = 0  # 过于简单
flag: bool = True  # 含义不明确
d: dict = {}  # 无意义的名字
max_retries: int = 3  # 缩写不当
```

#### 函数命名
```python
# ✅ 好的命名
def calculate_occupancy_rate(leased_area: float, total_area: float) -> float:
    """计算出租率"""
    pass

def validate_asset_data(data: dict) -> bool:
    """验证资产数据有效性"""
    pass

# ❌ 不好的命名
def calc_rate(a: float, b: float) -> float:  # 函数名不清晰，参数无意义
    pass

def check(d: dict) -> bool:  # 函数名和参数都不清晰
    pass
```

#### 类命名
```python
# ✅ 好的命名
class AssetManager:
    """资产管理器"""
    pass

class PDFImportService:
    """PDF导入服务"""
    pass

# ❌ 不好的命名
class Manager:  # 过于通用
    pass

class PDFService:  # 不够具体
    pass
```

### 2. 代码格式

#### 行长度
- 每行不超过88个字符（Ruff默认配置）
- 长字符串使用括号换行

```python
# ✅ 好的格式
message = (
    "这是一个很长的消息，需要换行处理，"
    "确保代码可读性良好"
)

# ❌ 不好的格式
message = "这是一个很长的消息，需要换行处理，确保代码可读性良好，但是超过了建议的行长度限制"
```

#### 缩进和空格
```python
# ✅ 好的格式
def process_assets(
    assets: list[dict],
    *,
    validate: bool = True,
    save_to_db: bool = False
) -> list[dict]:
    """处理资产数据"""
    processed_assets = []
    
    for asset in assets:
        if validate and not validate_asset(asset):
            continue
            
        processed_asset = transform_asset_data(asset)
        processed_assets.append(processed_asset)
    
    if save_to_db:
        save_assets_to_database(processed_assets)
    
    return processed_assets

# ❌ 不好的格式
def process_assets(assets:list[dict],*,validate:bool=True,save_to_db:bool=False)->list[dict]:
    processed_assets=[]
    for asset in assets:
        if validate and not validate_asset(asset):
            continue
        processed_asset=transform_asset_data(asset)
        processed_assets.append(processed_asset)
    if save_to_db:
        save_assets_to_database(processed_assets)
    return processed_assets
```

### 3. 类型注解

#### 函数参数和返回值
```python
from typing import Optional, Union, List, Dict, Any
from datetime import datetime

# ✅ 好的类型注解
def get_asset_by_id(
    asset_id: int,
    include_deleted: bool = False
) -> Optional[dict[str, Any]]:
    """根据ID获取资产信息"""
    pass

def calculate_financial_metrics(
    assets: List[dict[str, Any]],
    start_date: datetime,
    end_date: datetime
) -> Dict[str, float]:
    """计算财务指标"""
    pass

# ❌ 不好的类型注解
def get_asset(asset_id, include_deleted=False):  # 缺少类型注解
    pass
```

#### 类属性类型注解
```python
# ✅ 好的类型注解
class AssetService:
    """资产服务类"""
    
    def __init__(self, db_session: Session) -> None:
        self.db_session: Session = db_session
        self.cache: Dict[str, Any] = {}
        self._logger: Logger = logging.getLogger(__name__)
    
    def get_total_value(self) -> float:
        """获取总资产价值"""
        pass

# ❌ 不好的类型注解
class AssetService:
    def __init__(self, db_session):  # 缺少类型注解
        self.db_session = db_session
        self.cache = {}
        self._logger = logging.getLogger(__name__)
```

## 🏗️ 代码结构

### 1. 函数设计

#### 函数长度
- 单个函数不超过50行代码
- 复杂逻辑应该拆分成多个小函数

```python
# ✅ 好的函数设计
def import_pdf_contract(
    file_path: str,
    *,
    validate_format: bool = True,
    extract_text: bool = True
) -> dict[str, Any]:
    """导入PDF合同"""
    if validate_format:
        _validate_pdf_format(file_path)
    
    if extract_text:
        text = _extract_text_from_pdf(file_path)
        contract_data = _parse_contract_text(text)
    else:
        contract_data = {}
    
    return contract_data

def _validate_pdf_format(file_path: str) -> None:
    """验证PDF格式"""
    pass

def _extract_text_from_pdf(file_path: str) -> str:
    """从PDF中提取文本"""
    pass

def _parse_contract_text(text: str) -> dict[str, Any]:
    """解析合同文本"""
    pass

# ❌ 不好的函数设计
def import_pdf_contract(file_path: str) -> dict[str, Any]:
    # 一个函数做了太多事情，难以测试和维护
    # 验证PDF格式
    if not file_path.endswith('.pdf'):
        raise ValueError("Invalid PDF format")
    
    # 提取文本
    import PyPDF2
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    
    # 解析合同
    contract_data = {}
    # ... 大量解析逻辑
    return contract_data
```

#### 错误处理
```python
# ✅ 好的错误处理
def get_asset_value(asset_id: int) -> float:
    """获取资产价值"""
    try:
        asset = database.get_asset(asset_id)
        if asset is None:
            raise AssetNotFoundError(f"Asset {asset_id} not found")
        
        if asset["status"] != "active":
            raise InactiveAssetError(f"Asset {asset_id} is not active")
        
        return calculate_asset_value(asset)
        
    except DatabaseError as e:
        logger.error(f"Database error while fetching asset {asset_id}: {e}")
        raise AssetServiceError(f"Failed to get asset {asset_id}") from e
    
    except Exception as e:
        logger.error(f"Unexpected error while getting asset {asset_id}: {e}")
        raise AssetServiceError(f"Unexpected error") from e

# ❌ 不好的错误处理
def get_asset_value(asset_id: int) -> float:
    asset = database.get_asset(asset_id)
    return calculate_asset_value(asset)  # 没有错误处理
```

### 2. 类设计

#### 单一职责原则
```python
# ✅ 好的类设计
class AssetRepository:
    """资产数据访问"""
    
    def get_by_id(self, asset_id: int) -> Optional[dict]:
        pass
    
    def save(self, asset: dict) -> None:
        pass
    
    def delete(self, asset_id: int) -> None:
        pass

class AssetService:
    """资产业务逻辑"""
    
    def __init__(self, repository: AssetRepository):
        self.repository = repository
    
    def create_asset(self, asset_data: dict) -> dict:
        """创建资产"""
        validated_data = self._validate_asset_data(asset_data)
        return self.repository.save(validated_data)

class AssetController:
    """资产API控制器"""
    
    def __init__(self, service: AssetService):
        self.service = service
    
    def create_asset_endpoint(self, request: Request) -> Response:
        """创建资产API端点"""
        asset_data = request.json()
        result = self.service.create_asset(asset_data)
        return Response(json.dumps(result), status=201)

# ❌ 不好的类设计
class AssetManager:  # 一个类做了太多事情
    def get_asset(self, asset_id: int):
        pass
    
    def save_asset(self, asset_data: dict):
        pass
    
    def create_asset_api(self, request: Request):
        pass
    
    def validate_asset(self, asset_data: dict):
        pass
```

### 3. 模块组织

#### 推荐的项目结构
```
backend/
├── src/
│   ├── api/              # API路由
│   │   ├── v1/
│   │   │   ├── assets.py
│   │   │   ├── users.py
│   │   │   └── auth.py
│   │   └── dependencies.py
│   ├── models/           # 数据模型
│   │   ├── asset.py
│   │   ├── user.py
│   │   └── base.py
│   ├── schemas/          # 数据模式
│   │   ├── asset.py
│   │   └── user.py
│   ├── services/         # 业务逻辑
│   │   ├── asset_service.py
│   │   ├── pdf_service.py
│   │   └── auth_service.py
│   ├── repositories/     # 数据访问
│   │   ├── asset_repo.py
│   │   └── user_repo.py
│   ├── utils/            # 工具函数
│   │   ├── validators.py
│   │   ├── formatters.py
│   │   └── exceptions.py
│   └── core/             # 核心配置
│       ├── config.py
│       ├── database.py
│       └── security.py
```

## 🧪 测试最佳实践

### 1. 单元测试

#### 测试命名
```python
# ✅ 好的测试命名
def test_calculate_occupancy_rate_with_valid_input():
    """测试有效输入的出租率计算"""
    pass

def test_calculate_occupancy_rate_with_zero_total_area():
    """测试总面积为零时的出租率计算"""
    pass

def test_calculate_occupancy_rate_with_negative_values():
    """测试负值输入的出租率计算"""
    pass

# ❌ 不好的测试命名
def test_occupancy_rate():
    pass

def test_function():
    pass
```

#### 测试结构 (AAA模式)
```python
# ✅ 好的测试结构
def test_import_pdf_contract_success():
    """测试成功导入PDF合同"""
    # Arrange (准备)
    test_file = "test_contract.pdf"
    expected_data = {"contract_id": "TEST001", "tenant": "Test Company"}
    
    # Act (执行)
    result = import_pdf_contract(test_file)
    
    # Assert (断言)
    assert result["contract_id"] == expected_data["contract_id"]
    assert result["tenant"] == expected_data["tenant"]
    assert "imported_at" in result

# ❌ 不好的测试结构
def test_import_pdf():
    result = import_pdf_contract("test.pdf")
    assert result is not None
```

### 2. 测试数据

#### 使用工厂模式
```python
# ✅ 好的测试数据管理
import factory
from factory import Faker

class AssetFactory(factory.Factory):
    """资产测试数据工厂"""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: n)
    name = Faker('company')
    area = Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    status = 'active'
    created_at = Faker('date_time')

def test_asset_creation():
    """测试资产创建"""
    # 创建测试数据
    asset_data = AssetFactory()
    
    # 执行测试
    result = create_asset(asset_data)
    
    # 验证结果
    assert result['id'] is not None
    assert result['name'] == asset_data['name']

# ❌ 不好的测试数据
asset_data = {
    'name': 'Test Asset',
    'area': 100.0,
    'status': 'active'
}
```

## 🔍 代码审查清单

### 代码提交前自检

#### 功能性检查
- [ ] 代码能够正常编译/运行
- [ ] 所有测试用例通过
- [ ] 边界条件处理完善
- [ ] 错误处理机制完整

#### 质量检查
- [ ] 代码通过Ruff检查（无Error级别问题）
- [ ] 类型注解完整且通过MyPy检查
- [ ] 无安全漏洞（Bandit扫描通过）
- [ ] 代码复杂度在合理范围内

#### 可读性检查
- [ ] 命名清晰且有意义
- [ ] 函数和类有适当的文档字符串
- [ ] 复杂逻辑有注释说明
- [ ] 代码格式一致

#### 性能检查
- [ ] 没有明显的性能瓶颈
- [ ] 数据库查询优化（避免N+1问题）
- [ ] 内存使用合理
- [ ] 适当的缓存机制

### PR审查要点

#### 必须检查项
- [ ] 代码通过所有自动化检查
- [ ] 新增代码有适当的单元测试
- [ ] 测试覆盖率不降低
- [ ] 文档已更新（如需要）

#### 推荐检查项
- [ ] 代码符合项目架构设计
- [ ] 没有重复代码
- [ ] 使用了适当的设计模式
- [ ] 考虑了扩展性

## 🚨 常见问题及解决方案

### 1. 循环导入问题
```python
# 问题：循环导入
# module_a.py
from .module_b import function_b

def function_a():
    return function_b()

# module_b.py
from .module_a import function_a  # 循环导入

def function_b():
    return function_a()

# 解决方案：使用延迟导入或重构
# module_a.py
def function_a():
    from .module_b import function_b  # 延迟导入
    return function_b()
```

### 2. 类型注解循环引用
```python
# 问题：循环引用
# user.py
from .asset import Asset

class User:
    assets: list[Asset]

# asset.py
from .user import User

class Asset:
    owner: User

# 解决方案：使用字符串注解或TYPE_CHECKING
# user.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .asset import Asset

class User:
    assets: list['Asset']  # 字符串注解
```

### 3. 异步代码错误处理
```python
# ✅ 正确的异步错误处理
async def fetch_asset_data(asset_id: int) -> dict:
    """获取资产数据"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"/api/assets/{asset_id}") as response:
                if response.status == 404:
                    raise AssetNotFoundError(f"Asset {asset_id} not found")
                
                response.raise_for_status()
                return await response.json()
                
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error fetching asset {asset_id}: {e}")
        raise AssetServiceError(f"Failed to fetch asset {asset_id}") from e
    
    except Exception as e:
        logger.error(f"Unexpected error fetching asset {asset_id}: {e}")
        raise

# ❌ 不好的异步错误处理
async def fetch_asset_data(asset_id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"/api/assets/{asset_id}") as response:
            return await response.json()  # 没有错误处理
```

## 📈 持续改进

### 质量指标监控
- 每日运行代码质量检查
- 跟踪关键指标的变化趋势
- 定期回顾和调整质量标准

### 团队培训
- 定期进行代码质量培训
- 分享最佳实践和经验
- 鼓励团队成员提出改进建议

### 工具优化
- 定期更新代码质量工具
- 根据项目需要调整工具配置
- 探索新的代码质量工具和方法

## 📞 获取帮助

### 内部资源
- 代码质量监控系统：`backend/scripts/code_quality_monitor.py`
- 质量报告：`backend/reports/`
- 配置文件：`backend/pyproject.toml`

### 外部资源
- [Ruff文档](https://docs.astral.sh/ruff/)
- [MyPy文档](https://mypy.readthedocs.io/)
- [Bandit文档](https://bandit.readthedocs.io/)
- [Python最佳实践](https://realpython.com/)

### 联系方式
- 技术负责人：负责技术决策和标准制定
- 代码质量负责人：负责质量监控和改进推进
- 开发团队：负责具体的代码质量改进执行

---

*本指南会根据项目发展和团队反馈持续更新和完善*