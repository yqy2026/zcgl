# 代码质量扩展指南 - 数据库优化与测试覆盖

## 📋 概述

本文档是对《代码质量最佳实践指南》的扩展，专门针对数据库优化和测试覆盖提供详细的实践指南。这些内容基于地产资产管理系统的实际开发经验总结，旨在帮助开发团队提升代码质量和系统性能。

## 🗄️ 数据库优化最佳实践

### 1. 连接池管理

#### 合理配置连接池
```python
# ✅ 好的连接池配置
from core.enhanced_database import ConnectionPoolConfig

# 根据并发需求配置连接池
pool_config = ConnectionPoolConfig(
    pool_size=20,           # 基础连接数
    max_overflow=30,        # 最大溢出连接数
    pool_timeout=30,        # 获取连接超时
    pool_recycle=3600,      # 连接回收时间
    pool_pre_ping=True,     # 连接预检查
    echo=False              # 生产环境关闭SQL日志
)

# ❌ 不好的配置
pool_config = ConnectionPoolConfig(
    pool_size=100,          # 过大的连接池浪费资源
    max_overflow=0,         # 没有溢出连接无法处理突发流量
    pool_timeout=5,         # 过短的超时时间
    pool_recycle=0,         # 不回收连接可能导致连接老化
    pool_pre_ping=False,    # 不检查连接可能导致使用失效连接
    echo=True               # 生产环境开启SQL日志影响性能
)
```

#### 连接池监控
```python
# 定期监控连接池状态
def monitor_connection_pool():
    """监控连接池状态"""
    db_manager = get_database_manager()
    pool_status = db_manager.get_connection_pool_status()

    # 检查连接池利用率
    utilization = pool_status["utilization"]
    if utilization > 80:
        logger.warning(f"连接池利用率过高: {utilization}%")

    # 检查连接泄漏
    active_connections = pool_status["checked_out"]
    if active_connections > pool_status["pool_size"]:
        logger.error(f"检测到可能的连接泄漏: {active_connections} 个活跃连接")

    return pool_status
```

### 2. 查询优化

#### 索引策略
```python
# ✅ 好的索引设计
# 在常用查询字段上创建索引
CREATE INDEX idx_assets_ownership_status ON assets(ownership_status);
CREATE INDEX idx_assets_created_at ON assets(created_at);
CREATE INDEX idx_contracts_asset_id ON contracts(asset_id);

# 复合索引优化多字段查询
CREATE INDEX idx_assets_status_category ON assets(status, business_category);
CREATE INDEX idx_contracts_dates ON contracts(start_date, end_date);

# 避免过多索引影响写入性能
# ❌ 不好的索引设计
CREATE INDEX idx_assets_all_fields ON assets(name, address, area, status, created_at, updated_at);
```

#### 查询优化
```python
# ✅ 好的查询优化
def get_assets_with_filters(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    """根据条件查询资产"""
    query = session.query(Asset)

    # 使用索引友好的查询条件
    if status:
        query = query.filter(Asset.status == status)  # 利用status索引

    if category:
        query = query.filter(Asset.business_category == category)  # 利用category索引

    # 分页避免大数据集
    return query.limit(limit).all()

# ❌ 不好的查询
def get_all_assets() -> List[dict]:
    """查询所有资产 - 可能导致内存溢出"""
    return session.query(Asset).all()  # 没有分页，可能导致内存问题
```

#### 避免N+1查询问题
```python
# ✅ 好的关联查询
def get_contracts_with_assets() -> List[dict]:
    """获取合同及其关联资产"""
    # 使用joinedload避免N+1问题
    return session.query(Contract).options(
        joinedload(Contract.asset)
    ).all()

# ✅ 使用selectinload优化一对多关系
def get_assets_with_contracts() -> List[dict]:
    """获取资产及其合同"""
    return session.query(Asset).options(
        selectinload(Asset.contracts)
    ).all()

# ❌ N+1查询问题
def get_contracts_with_assets_bad() -> List[dict]:
    """获取合同及其关联资产 - 存在N+1问题"""
    contracts = session.query(Contract).all()
    for contract in contracts:
        # 每个合同都会执行一次查询获取资产信息
        asset = session.query(Asset).filter(Asset.id == contract.asset_id).first()
        contract.asset = asset
    return contracts
```

### 3. 事务管理

#### 合理使用事务
```python
# ✅ 好的事务管理
def transfer_ownership(
    asset_id: int,
    from_owner_id: int,
    to_owner_id: int
) -> bool:
    """转移资产所有权"""
    try:
        # 开始事务
        with session.begin():
            # 检查资产状态
            asset = session.query(Asset).filter(
                Asset.id == asset_id,
                Asset.owner_id == from_owner_id
            ).with_for_update().first()  # 行锁防止并发问题

            if not asset:
                raise AssetNotFoundError(f"Asset {asset_id} not found")

            # 更新所有权
            asset.owner_id = to_owner_id
            asset.updated_at = datetime.utcnow()

            # 记录变更历史
            history = OwnershipHistory(
                asset_id=asset_id,
                from_owner_id=from_owner_id,
                to_owner_id=to_owner_id,
                transferred_at=datetime.utcnow()
            )
            session.add(history)

        # 事务自动提交
        return True

    except Exception as e:
        logger.error(f"所有权转移失败: {e}")
        # 事务自动回滚
        return False

# ❌ 不好的事务管理
def transfer_ownership_bad(asset_id: int, from_owner_id: int, to_owner_id: int):
    """转移资产所有权 - 缺乏事务保护"""
    asset = session.query(Asset).filter(Asset.id == asset_id).first()
    asset.owner_id = to_owner_id
    session.commit()  # 没有错误处理，可能导致数据不一致
```

### 4. 性能监控

#### 慢查询监控
```python
# 启用慢查询日志
import logging

# 配置慢查询日志
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
logger = logging.getLogger('sqlalchemy.engine')

def slow_query_handler(conn, cursor, statement, parameters, context, executemany):
    """慢查询处理器"""
    execution_time = context['duration']
    if execution_time > 1.0:  # 超过1秒的查询
        logger.warning(f"慢查询检测: {execution_time:.2f}s")
        logger.warning(f"SQL: {statement}")
        logger.warning(f"参数: {parameters}")

        # 记录到数据库
        slow_query = SlowQuery(
            sql=statement,
            parameters=str(parameters),
            execution_time=execution_time,
            timestamp=datetime.utcnow()
        )
        session.add(slow_query)
        session.commit()

# 注册慢查询处理器
from sqlalchemy import event
event.listen(engine, "after_cursor_execute", slow_query_handler)
```

#### 性能指标收集
```python
# 定期收集性能指标
def collect_database_metrics():
    """收集数据库性能指标"""
    db_manager = get_database_manager()
    metrics = db_manager.metrics

    # 收集关键指标
    performance_data = {
        "timestamp": datetime.utcnow(),
        "total_queries": metrics.total_queries,
        "slow_queries": metrics.slow_queries,
        "avg_response_time": metrics.avg_response_time,
        "connection_errors": metrics.connection_errors,
        "pool_utilization": get_pool_utilization()
    }

    # 存储到时序数据库或监控系统
    store_metrics(performance_data)

    # 检查性能告警
    check_performance_alerts(performance_data)

def check_performance_alerts(metrics: dict):
    """检查性能告警"""
    # 慢查询告警
    if metrics["slow_queries"] > 10:
        send_alert("数据库慢查询数量过多", "warning")

    # 平均响应时间告警
    if metrics["avg_response_time"] > 1000:  # 1秒
        send_alert("数据库响应时间过长", "critical")

    # 连接错误告警
    if metrics["connection_errors"] > 5:
        send_alert("数据库连接错误频繁", "critical")
```

### 5. 数据库维护

#### 定期维护任务
```python
# 定期数据库优化
def schedule_database_maintenance():
    """安排数据库维护任务"""
    # 每日任务
    schedule_daily_task(cleanup_old_logs, time="02:00")
    schedule_daily_task(update_statistics, time="03:00")

    # 每周任务
    schedule_weekly_task(rebuild_indexes, day="sunday", time="04:00")
    schedule_weekly_task(analyze_slow_queries, day="sunday", time="05:00")

    # 每月任务
    schedule_monthly_task(full_database_optimization, day=1, time="06:00")

def cleanup_old_logs():
    """清理旧日志"""
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    session.query(LogEntry).filter(
        LogEntry.created_at < cutoff_date
    ).delete()
    session.commit()

def update_statistics():
    """更新数据库统计信息"""
    # PostgreSQL
    session.execute(text("ANALYZE"))

    session.commit()

def rebuild_indexes():
    """重建索引"""
    # 检查索引碎片化情况
    fragmented_indexes = get_fragmented_indexes()

    for index_info in fragmented_indexes:
        if index_info["fragmentation"] > 30:  # 碎片化超过30%
            logger.info(f"重建索引: {index_info['name']}")
            rebuild_index(index_info["name"])
```

## 🧪 测试覆盖完整指南

### 1. 测试策略概览

#### 测试金字塔
```mermaid
graph TB
    A[E2E Tests - 10%] --> B[Integration Tests - 20%]
    B --> C[Unit Tests - 70%]

    style A fill:#ffcccc
    style B fill:#ffffcc
    style C fill:#ccffcc
```

#### 测试覆盖率目标
| 测试类型 | 覆盖率目标 | 测试重点 |
|---------|-----------|----------|
| 单元测试 | 80%+ | 业务逻辑、工具函数、数据模型 |
| 集成测试 | 60%+ | API端点、数据库操作、外部服务 |
| 端到端测试 | 40%+ | 关键业务流程、用户场景 |

### 2. 单元测试最佳实践

#### 测试结构组织
```python
# ✅ 好的测试文件结构
# tests/test_services/test_asset_service.py
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

class TestAssetService:
    """资产服务测试类"""

    @pytest.fixture
    def mock_repository(self):
        """模拟资产仓库"""
        return Mock(spec=AssetRepository)

    @pytest.fixture
    def asset_service(self, mock_repository):
        """资产服务实例"""
        return AssetService(mock_repository)

    @pytest.fixture
    def sample_asset(self):
        """示例资产数据"""
        return {
            "id": 1,
            "name": "测试资产",
            "area": 100.0,
            "status": "active",
            "created_at": datetime.utcnow()
        }

    def test_create_asset_success(self, asset_service, mock_repository, sample_asset):
        """测试成功创建资产"""
        # Arrange
        mock_repository.save.return_value = sample_asset

        # Act
        result = asset_service.create_asset(sample_asset)

        # Assert
        assert result == sample_asset
        mock_repository.save.assert_called_once_with(sample_asset)

    def test_create_asset_invalid_data(self, asset_service):
        """测试创建资产时数据验证失败"""
        # Arrange
        invalid_asset = {"name": "", "area": -100}  # 无效数据

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            asset_service.create_asset(invalid_asset)

        assert "资产名称不能为空" in str(exc_info.value)
        assert "面积必须大于0" in str(exc_info.value)

    def test_get_asset_by_id_not_found(self, asset_service, mock_repository):
        """测试获取不存在的资产"""
        # Arrange
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(AssetNotFoundError):
            asset_service.get_asset_by_id(999)
```

#### Mock和Fixture使用
```python
# ✅ 好的Mock使用
@patch('services.asset_service.database')
def test_asset_service_with_database_mock(mock_db):
    """测试资产服务使用数据库Mock"""
    # 配置Mock返回值
    mock_db.query.return_value.filter.return_value.first.return_value = {
        "id": 1,
        "name": "测试资产"
    }

    # 执行测试
    service = AssetService()
    result = service.get_asset(1)

    # 验证结果
    assert result["name"] == "测试资产"
    mock_db.query.assert_called_once()

# ✅ 复杂Fixture使用
@pytest.fixture
def complex_test_data():
    """复杂测试数据Fixture"""
    return {
        "assets": [
            {"id": 1, "name": "资产1", "status": "active"},
            {"id": 2, "name": "资产2", "status": "inactive"},
        ],
        "contracts": [
            {"id": 1, "asset_id": 1, "tenant": "租户A"},
            {"id": 2, "asset_id": 1, "tenant": "租户B"},
        ],
        "expected_results": {
            "active_assets_count": 1,
            "total_contracts": 2
        }
    }

def test_complex_business_logic(complex_test_data):
    """测试复杂业务逻辑"""
    # 使用复杂测试数据进行测试
    assets = complex_test_data["assets"]
    contracts = complex_test_data["contracts"]
    expected = complex_test_data["expected_results"]

    # 执行业务逻辑
    result = calculate_business_metrics(assets, contracts)

    # 验证结果
    assert result["active_assets_count"] == expected["active_assets_count"]
    assert result["total_contracts"] == expected["total_contracts"]
```

#### 参数化测试
```python
# ✅ 好的参数化测试
@pytest.mark.parametrize("input_data,expected_output", [
    ({"area": 100, "rented_area": 80}, 80.0),
    ({"area": 200, "rented_area": 150}, 75.0),
    ({"area": 50, "rented_area": 0}, 0.0),
    ({"area": 0, "rented_area": 0}, 0.0),
])
def test_calculate_occupancy_rate(input_data, expected_output):
    """测试出租率计算"""
    result = calculate_occupancy_rate(
        input_data["area"],
        input_data["rented_area"]
    )
    assert result == expected_output

@pytest.mark.parametrize("status,expected_is_active", [
    ("active", True),
    ("inactive", False),
    ("pending", False),
    ("archived", False),
])
def test_is_asset_active(status, expected_is_active):
    """测试资产活跃状态判断"""
    asset = {"status": status}
    result = is_asset_active(asset)
    assert result == expected_is_active
```

### 3. 集成测试

#### API端点测试
```python
# ✅ 好的API集成测试
@pytest.mark.integration
class TestAssetAPI:
    """资产API集成测试"""

    @pytest.fixture
    def client(self):
        """测试客户端"""
        from fastapi.testclient import TestClient
        from main import app

        return TestClient(app)

    @pytest.fixture
    def test_database(self):
        """测试数据库"""
        # 创建内存数据库
        engine = create_engine("postgresql+psycopg://user:password@localhost:5432/zcgl_test")
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        session = Session()

        yield session

        session.close()

    def test_create_asset_endpoint(self, client, test_database):
        """测试创建资产API端点"""
        # 准备测试数据
        asset_data = {
            "name": "测试资产",
            "area": 100.0,
            "status": "active",
            "business_category": "商业"
        }

        # 发送请求
        response = client.post("/api/v1/assets", json=asset_data)

        # 验证响应
        assert response.status_code == 201
        result = response.json()
        assert result["success"] is True
        assert result["data"]["name"] == asset_data["name"]
        assert "id" in result["data"]

    def test_get_asset_endpoint_success(self, client, test_database):
        """测试获取资产API端点成功场景"""
        # 先创建资产
        asset = create_test_asset(test_database)

        # 发送请求
        response = client.get(f"/api/v1/assets/{asset.id}")

        # 验证响应
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["data"]["id"] == asset.id

    def test_get_asset_endpoint_not_found(self, client):
        """测试获取资产API端点404场景"""
        response = client.get("/api/v1/assets/99999")
        assert response.status_code == 404
```

#### 数据库集成测试
```python
# ✅ 好的数据库集成测试
@pytest.mark.integration
class TestDatabaseOperations:
    """数据库操作集成测试"""

    @pytest.fixture
    def db_session(self):
        """数据库会话"""
        engine = create_engine("postgresql+psycopg://user:password@localhost:5432/zcgl_test")
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        session = Session()

        yield session

        session.close()

    def test_create_and_retrieve_asset(self, db_session):
        """测试创建和检索资产"""
        # 创建资产
        asset = Asset(
            name="测试资产",
            area=100.0,
            status="active"
        )
        db_session.add(asset)
        db_session.commit()

        # 检索资产
        retrieved = db_session.query(Asset).filter(
            Asset.id == asset.id
        ).first()

        # 验证结果
        assert retrieved is not None
        assert retrieved.name == "测试资产"
        assert retrieved.area == 100.0

    def test_transaction_rollback(self, db_session):
        """测试事务回滚"""
        # 开始事务
        original_count = db_session.query(Asset).count()

        try:
            with db_session.begin():
                # 添加资产
                asset = Asset(name="测试资产", area=100.0)
                db_session.add(asset)

                # 故意触发错误
                raise ValueError("测试回滚")

        except ValueError:
            pass  # 预期的错误

        # 验证回滚
        final_count = db_session.query(Asset).count()
        assert final_count == original_count
```

### 4. 端到端测试

#### 业务流程测试
```python
# ✅ 好的端到端测试
@pytest.mark.e2e
class TestAssetManagementWorkflow:
    """资产管理端到端测试"""

    def test_complete_asset_lifecycle(self):
        """测试完整的资产生命周期"""
        # 1. 创建资产
        asset_data = {
            "name": "端到端测试资产",
            "area": 200.0,
            "status": "active"
        }
        create_response = self.client.post("/api/v1/assets", json=asset_data)
        assert create_response.status_code == 201
        asset_id = create_response.json()["data"]["id"]

        # 2. 上传PDF文档
        with open("test_contract.pdf", "rb") as f:
            pdf_response = self.client.post(
                f"/api/v1/assets/{asset_id}/upload-pdf",
                files={"file": ("test_contract.pdf", f, "application/pdf")}
            )
        assert pdf_response.status_code == 200

        # 3. 创建租赁合同
        contract_data = {
            "asset_id": asset_id,
            "tenant_name": "测试租户",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "monthly_rent": 10000.0
        }
        contract_response = self.client.post("/api/v1/contracts", json=contract_data)
        assert contract_response.status_code == 201
        contract_id = contract_response.json()["data"]["id"]

        # 4. 生成月度台账
        ledger_response = self.client.post(
            f"/api/v1/contracts/{contract_id}/generate-ledger",
            json={"month": "2025-01"}
        )
        assert ledger_response.status_code == 200

        # 5. 验证数据一致性
        asset_response = self.client.get(f"/api/v1/assets/{asset_id}")
        asset_data = asset_response.json()["data"]
        assert asset_data["contract_count"] == 1
        assert asset_data["total_rented_area"] == 200.0
```

### 5. 测试配置和工具

#### Pytest配置
```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试
    database: 数据库相关测试
```

#### 测试工具和脚本
```python
# scripts/test_runner.py
import subprocess
import sys
from pathlib import Path

def run_tests(test_type="all"):
    """运行测试"""
    project_root = Path(__file__).parent.parent

    if test_type == "unit":
        cmd = ["pytest", "-m", "unit", "tests/"]
    elif test_type == "integration":
        cmd = ["pytest", "-m", "integration", "tests/"]
    elif test_type == "e2e":
        cmd = ["pytest", "-m", "e2e", "tests/"]
    else:
        cmd = ["pytest", "tests/"]

    # 运行测试
    result = subprocess.run(cmd, cwd=project_root)

    if result.returncode != 0:
        print(f"测试失败，退出码: {result.returncode}")
        sys.exit(result.returncode)

    print("所有测试通过!")

if __name__ == "__main__":
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    run_tests(test_type)
```

#### 测试数据管理
```python
# tests/fixtures/data_factory.py
import factory
from factory import Faker
from datetime import datetime, timedelta

class AssetFactory(factory.Factory):
    """资产数据工厂"""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n + 1)
    name = Faker('company')
    address = Faker('address')
    area = Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    status = factory.Iterator(['active', 'inactive', 'pending'])
    business_category = Faker('word')
    created_at = Faker('date_time_between', start_date='-2y', end_date='now')
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)

class ContractFactory(factory.Factory):
    """合同数据工厂"""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n + 1)
    asset_id = factory.SubFactory(AssetFactory).id
    tenant_name = Faker('name')
    start_date = Faker('date_between', start_date='-1y', end_date='today')
    end_date = factory.LazyAttribute(
        lambda obj: obj.start_date + timedelta(days=365)
    )
    monthly_rent = Faker('pydecimal', left_digits=5, right_digits=2, positive=True)
    status = 'active'
```

### 6. 持续集成中的测试

#### GitHub Actions配置
```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        cd backend
        pip install uv
        uv sync --dev

    - name: Run unit tests
      run: |
        cd backend
        uv run pytest -m unit --cov=src --cov-report=xml

    - name: Run integration tests
      run: |
        cd backend
        uv run pytest -m integration

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: backend/coverage.xml
```

## 📊 质量指标监控

### 1. 数据库性能指标

#### 关键性能指标（KPI）
| 指标名称 | 目标值 | 告警阈值 | 监控频率 |
|---------|--------|----------|----------|
| 平均查询响应时间 | < 100ms | > 500ms | 实时 |
| 连接池利用率 | < 70% | > 85% | 每分钟 |
| 慢查询数量 | < 5/小时 | > 10/小时 | 每小时 |
| 数据库连接错误率 | < 0.1% | > 1% | 实时 |
| 索引命中率 | > 95% | < 90% | 每小时 |

#### 监控实现
```python
# 性能监控装饰器
def monitor_database_performance(func):
    """数据库性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # 毫秒

            # 记录性能指标
            record_performance_metric(func.__name__, execution_time, "success")

            # 检查性能告警
            if execution_time > 1000:  # 超过1秒
                send_performance_alert(func.__name__, execution_time)

            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            record_performance_metric(func.__name__, execution_time, "error")
            raise

    return wrapper

@monitor_database_performance
def get_asset_statistics():
    """获取资产统计信息"""
    # 复杂的数据库查询
    pass
```

### 2. 测试覆盖率监控

#### 覆盖率指标
| 指标类型 | 当前值 | 目标值 | 趋势 |
|---------|--------|--------|------|
| 总体覆盖率 | 85% | 90% | ↗️ |
| 单元测试覆盖率 | 92% | 95% | ↗️ |
| 集成测试覆盖率 | 78% | 85% | ↗️ |
| API端点覆盖率 | 88% | 95% | ➡️ |

#### 覆盖率报告生成
```python
# scripts/generate_coverage_report.py
import coverage
import json
from datetime import datetime

def generate_coverage_report():
    """生成覆盖率报告"""
    # 创建覆盖率对象
    cov = coverage.Coverage()
    cov.load()

    # 生成报告
    total_coverage = cov.report()

    # 按模块分析覆盖率
    module_coverage = {}
    for module in cov.get_data().measured_files():
        module_name = module.replace('/', '.').replace('.py', '')
        with open(module, 'r') as f:
            lines = f.readlines()
            total_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])

        covered_lines = cov.get_data().line_counts()[module]
        coverage_percent = (covered_lines / total_lines) * 100 if total_lines > 0 else 0

        module_coverage[module_name] = {
            "total_lines": total_lines,
            "covered_lines": covered_lines,
            "coverage_percent": round(coverage_percent, 2)
        }

    # 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_coverage": total_coverage,
        "modules": module_coverage,
        "summary": {
            "modules_analyzed": len(module_coverage),
            "modules_above_80_percent": len([m for m in module_coverage.values() if m["coverage_percent"] >= 80]),
            "modules_below_50_percent": len([m for m in module_coverage.values() if m["coverage_percent"] < 50])
        }
    }

    # 保存报告
    with open("coverage_report.json", "w") as f:
        json.dump(report, f, indent=2)

    # 生成HTML报告
    cov.html_report(directory="htmlcov")

    return report
```

## 🎯 实施建议

### 1. 渐进式实施

#### 阶段一：基础建设（1-2周）
- 配置连接池监控
- 实施基本的慢查询检测
- 建立单元测试框架
- 设置代码覆盖率工具

#### 阶段二：优化改进（2-3周）
- 优化数据库查询
- 完善测试用例覆盖
- 实施性能监控告警
- 建立测试自动化流程

#### 阶段三：持续优化（持续进行）
- 定期性能分析和优化
- 持续改进测试覆盖率
- 监控和调整质量指标
- 团队培训和知识分享

### 2. 团队协作

#### 代码审查检查清单
- [ ] 数据库查询是否已优化
- [ ] 是否有适当的连接池配置
- [ ] 事务管理是否正确
- [ ] 是否有相应的单元测试
- [ ] 测试覆盖率是否达标
- [ ] 性能影响是否已评估

#### 质量改进会议
- 每周质量指标回顾
- 性能瓶颈分析讨论
- 测试覆盖缺口识别
- 改进措施制定和跟踪

### 3. 工具和自动化

#### 推荐工具
- **数据库监控**: Prometheus + Grafana
- **测试框架**: pytest + pytest-cov
- **性能分析**: SQLAlchemy + slow query logging
- **代码质量**: Ruff + MyPy + Bandit

#### 自动化脚本
- 数据库性能监控脚本
- 测试覆盖率报告生成
- 代码质量检查自动化
- 性能回归测试自动化

---

*本扩展指南与主指南配合使用，为团队提供更详细的数据库优化和测试覆盖实践指导。*