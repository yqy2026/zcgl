# 单元测试重构设计文档

**日期**: 2025-01-20
**状态**: 设计完成，待实施
**优先级**: P0（高优先级）

---

## 执行摘要

当前测试套件存在严重质量问题：74,108行测试代码仅实现33.8%覆盖率，其中12,946次Mock调用导致测试绕过了实际业务逻辑。本文档设计了一套渐进式重构方案，目标是8周内将覆盖率提升至65%+，同时将测试代码量减少40%。

### 关键指标目标

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 代码覆盖率 | 33.8% | 65%+ |
| Mock使用率 | 85% | <20% |
| 集成测试占比 | 5% | 60%+ |
| 测试执行时间 | 未知 | <5分钟 |
| 测试代码量 | 74,108行 | <45,000行 |

---

## 问题分析

### 核心问题

**问题1：Mock依赖症**
- 12,946次Mock调用，占总测试的85%
- 测试绕过了核心业务逻辑，只验证"是否调用"而非"逻辑是否正确"

**问题2：空洞断言**
- 308次 `mock_db.query.assert_called()` 只验证调用，不验证结果
- 缺少业务规则验证和边界条件测试

**问题3：测试金字塔倒置**
- 单元测试95%，集成测试5%，E2E测试0%
- 违反测试最佳实践，导致维护成本高、价值低

### 数据支撑

**按层级分组的覆盖率**：
- Model层：93.0%（过度测试）
- CRUD层：23.7%（基础薄弱）
- Service层：22.2%（核心未保护）
- API层：26.0%（入口未保护）

**完全未测试的关键文件**：
- `src/api/v1/rent_contract.py` - 0%（核心业务）
- `src/api/v1/system_monitoring.py` - 0%
- `src/api/v1/excel.py` - 0%
- `src/services/document/cache.py` - 0%

---

## 重构策略

### 三阶段重构

#### 阶段1：测试分层重构（优先级：高）

**目标**：减少Mock依赖，增加真实逻辑测试

**做法**：
1. **保留纯函数单元测试**（无Mock）
   - 工具函数、验证器、格式化器
   - 示例：`utils/format_date.py`

2. **Service层改为集成测试**（真实数据库）
   - 使用真实SQLite内存数据库
   - 测试完整业务逻辑路径
   - 验证数据库状态和业务规则

3. **API层改为端到端测试**（TestClient）
   - 使用FastAPI TestClient
   - 测试完整请求-响应流程

**预期效果**：
- Mock使用量减少85%（12,946 → ~2,000）
- 覆盖率提升至60%+
- 测试代码减少40%（74k → ~40k行）

#### 阶段2：断言质量提升（优先级：中）

**目标**：从验证调用转向验证行为

**重构模式**：

| 场景 | 错误断言 | 正确断言 |
|------|---------|---------|
| 数据库操作 | `mock_db.add.assert_called()` | 验证数据库中的实际状态 |
| 业务规则 | Mock跳过 | 测试真实业务逻辑 |
| 错误处理 | 缺失 | 验证异常类型和消息 |
| 边界条件 | 缺失 | 测试空值、零值、极大值 |

#### 阶段3：测试金字塔重建（优先级：长期）

**目标状态**：
- E2E测试：10%（关键业务流程）
- 集成测试：60%（组件协作）
- 单元测试：30%（纯函数）

---

## 实施计划

### Week 1：基础设施搭建

**任务**：
1. 创建数据库fixtures
   ```python
   @pytest.fixture(scope="function")
   def db_session():
       engine = create_engine("sqlite:///:memory:")
       Base.metadata.create_all(engine)
       ...
   ```

2. 创建API测试客户端
   ```python
   @pytest.fixture(scope="module")
   def client():
       return TestClient(app)
   ```

3. 创建测试工厂
   ```python
   class TestAssetFactory:
       @staticmethod
       def create_asset(db_session, **overrides):
           ...
   ```

**验收标准**：
- ✅ 能够运行一个简单的集成测试（API→DB）
- ✅ 数据库在测试间自动清理
- ✅ 测试执行时间 < 2秒/个

### Week 2-7：模块重构（按优先级）

**优先级矩阵**：

| 模块 | 风险等级 | 当前覆盖率 | 重构优先级 | 预计工作量 |
|------|---------|-----------|-----------|-----------|
| 认证授权 | 🔴 高 | 29.5% | P0 | 3天 |
| 资产管理 | 🔴 高 | ~25% | P0 | 5天 |
| 合同管理 | 🔴 高 | 0% | P0 | 4天 |
| 权属管理 | 🟡 中 | 22% | P1 | 2天 |
| 系统监控 | 🟢 低 | 0% | P2 | 2天 |

**重构模板（以Ownership为例）**：

**Day 1：删除旧测试，编写集成测试**
```python
def test_create_ownership_success(db_session):
    """正常创建流程"""
    service = OwnershipService()
    result = service.create_ownership(
        db_session,
        obj_in=OwnershipCreate(name="测试权属方", short_name="CS")
    )

    # 验证业务规则
    assert result.code.startswith("OW")
    assert len(result.code) == 9

    # 验证数据库状态
    db_obj = db_session.query(Ownership).filter_by(id=result.id).first()
    assert db_obj is not None

def test_create_ownership_duplicate_name_raises_error(db_session):
    """重复名称报错"""
    service = OwnershipService()

    service.create_ownership(
        db_session,
        obj_in=OwnershipCreate(name="甲方", short_name="A")
    )

    with pytest.raises(ValueError, match="名称.*已存在"):
        service.create_ownership(
            db_session,
            obj_in=OwnershipCreate(name="甲方", short_name="B")
        )
```

**Day 2：API层端到端测试**
```python
def test_create_ownership_endpoint(client, db_session):
    """完整API流程测试"""
    response = client.post(
        "/api/v1/ownerships",
        json={"name": "新权属方", "short_name": "XQF"}
    )

    assert response.status_code == 200
    assert db_session.query(Ownership).count() == 1
```

**Day 3：边界条件测试**
```python
def test_create_ownership_with_special_characters(db_session):
    """特殊字符处理"""
    service = OwnershipService()
    result = service.create_ownership(
        db_session,
        obj_in=OwnershipCreate(name="甲方（集团）有限公司", short_name="A")
    )
    assert "（集团）" in result.name
```

### Week 8：文档和培训

**任务**：
1. 编写测试指南
2. 创建测试模板
3. 团队培训

---

## 风险缓解

### 风险1：重构期间测试保护消失

**策略**：
1. 分支保护机制
   ```bash
   git checkout -b refactor/test-ownership-2024-01
   pytest --cov --baseline-report=old_coverage.json
   ```

2. 金丝雀发布
   ```python
   @pytest.mark.legacy
   @pytest.mark.smoke
   def test_legacy_create_ownership_still_works():
       # 保留的最小集旧测试
   ```

3. 分模块渐进式迁移
   - Week 1: Ownership（低风险）
   - Week 2: Asset（中风险）
   - Week 3: RentContract（高风险，保留旧测试）

### 风险2：集成测试性能退化

**策略**：
1. 数据库优化
   ```python
   @pytest.fixture(scope="session")  # session级别共享引擎
   def db_engine():
       ...

   @pytest.fixture(scope="function")  # function级别独立session
   def db_session(db_engine):
       ...
   ```

2. 并行测试执行
   ```ini
   [pytest]
   addopts = -n auto
   ```

3. 测试分层执行
   ```bash
   pytest -m "unit" --maxfail=5        # 快速反馈
   pytest -m "unit or integration"     # 完整测试
   pytest -m "unit or integration or e2e"  # 全面测试
   ```

**性能目标**：
- 单个集成测试 < 2秒
- 完整测试套件 < 5分钟

### 风险3：团队适应阻力

**策略**：
1. 模板和脚手架
   ```bash
   python scripts/generate_integration_test.py --module Ownership
   ```

2. 文档和培训
   ```markdown
   ## 何时使用集成测试？

   ✅ 使用集成测试：
   - Service层业务逻辑
   - API端点功能测试
   - 复杂业务规则

   ❌ 使用单元测试：
   - 纯工具函数
   - 简单验证器
   ```

3. 代码审查检查表
   ```markdown
   - [ ] 新测试使用真实数据库（非Mock）
   - [ ] 测试覆盖业务规则（非仅调用验证）
   - [ ] 包含异常场景测试
   ```

---

## 成功标准

### 量化指标

| 指标类别 | 当前值 | 目标值 | 测量方法 |
|---------|--------|--------|---------|
| 代码覆盖率 | 33.8% | 65%+ | `pytest --cov` |
| Mock使用率 | 85% | <20% | 统计 `@patch` 次数 |
| 集成测试占比 | 5% | 60%+ | 文件路径统计 |
| 测试执行时间 | 未知 | <5分钟 | `pytest --durations` |
| 测试代码量 | 74,108行 | <45,000行 | `wc -l tests/` |

### 分阶段里程碑

```
M1 (Week 2):  核心模块覆盖率 >50%, Mock率 <40%
M2 (Week 4):  核心模块覆盖率 >60%, Mock率 <25%
M3 (Week 6):  所有模块覆盖率 >60%, Mock率 <20%
M4 (Week 8):  集成测试占比 >50%, 文档完善
```

### 质量验收标准

**L1：基础要求（必须达成）**
- 无遗留Mock测试在核心模块
- 所有新测试使用真实数据库
- 所有业务规则有测试覆盖

**L2：质量要求（应当达成）**
- 测试命名清晰
- 单个测试 < 2秒
- 使用工厂模式创建测试数据

**L3：卓越要求（努力达成）**
- E2E测试覆盖关键用户流程
- 测试指南完整
- CI集成自动化质量检查

---

## 预期价值

| 维度 | 重构前 | 重构后 | 改进 |
|------|--------|--------|------|
| 实际保护能力 | 低（Mock绕过逻辑） | 高（真实代码路径） | 10x |
| 测试维护成本 | 高（74k行代码） | 低（~40k行） | -46% |
| 新功能信心 | 低（测试不可靠） | 高（集成测试保护） | 质变 |
| 重构安全性 | 危险（测试脆弱） | 安全（测试健壮） | 质变 |
| 团队开发速度 | 慢（修复Mock耗时） | 快（真实反馈） | 2x |

---

## 下一步

1. 创建重构分支
2. 搭建测试基础设施
3. 从Ownership模块开始重构
4. 持续监控指标并调整策略

---

**文档版本**: 1.0
**最后更新**: 2025-01-20
