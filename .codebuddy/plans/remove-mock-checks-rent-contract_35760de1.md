---
name: remove-mock-checks-rent-contract
overview: 移除租赁合同服务中基于 unittest.mock 的查询分支，并将相关测试改为真实数据库会话，确保生产代码一致使用 eager loading。
todos:
  - id: scan-mock-tests
    content: 使用 [subagent:code-explorer] 扫描租赁合同相关测试中的 Mock 查询依赖点
    status: completed
  - id: remove-mock-branch
    content: 移除 rent_contract/service.py 中两处 Mock 判断并固定使用 selectinload
    status: completed
    dependencies:
      - scan-mock-tests
  - id: prepare-db-fixtures
    content: 为租赁合同测试补充真实数据库数据构建方法与基础数据
    status: completed
    dependencies:
      - remove-mock-branch
  - id: update-service-tests
    content: 将 test_rent_contract_service.py 的核心用例改为使用 test_db 会话
    status: completed
    dependencies:
      - prepare-db-fixtures
  - id: update-impl-tests
    content: 将 test_rent_contract_service_impl.py 的 Mock 会话用例改为真实数据库会话
    status: completed
    dependencies:
      - prepare-db-fixtures
  - id: update-coverage-tests
    content: 将 test_rent_contract_service_coverage.py 的 Mock 逻辑改为真实数据验证
    status: completed
    dependencies:
      - prepare-db-fixtures
  - id: verify-test-scope
    content: 补齐关键断言以确保 eager loading 路径覆盖完整
    status: completed
    dependencies:
      - update-service-tests
      - update-impl-tests
      - update-coverage-tests
---

## Product Overview

移除租赁合同服务中针对 Mock 会话的分支判断，保持查询逻辑在生产与测试环境一致，确保数据加载方式统一。界面无可视化变化。

## Core Features

- 移除服务层对 Mock 查询的特殊分支，统一使用一致的加载策略
- 调整相关单元测试为真实数据库会话，覆盖依赖该逻辑的核心用例

## Tech Stack

- Backend: FastAPI + SQLAlchemy 2.0
- Testing: pytest

## Tech Architecture

- 延续现有 Service → CRUD → ORM 的调用链
- 不引入新的架构层或模式

## Implementation Details

### Modified Files

```
backend/src/services/rent_contract/service.py
backend/tests/unit/services/test_rent_contract_service.py
backend/tests/unit/services/rent_contract/test_rent_contract_service_impl.py
backend/tests/unit/services/rent_contract/test_rent_contract_service_coverage.py
```

### Key Code Changes

- `_check_asset_rent_conflicts`：移除 Mock 判断，始终使用 `selectinload(RentContract.assets)`。
- `_calculate_average_unit_price`：移除 Mock 判断，始终使用 `selectinload` 预加载资产与条款。

### Test Strategy

- 使用 `backend/conftest.py` 提供的 `test_db` 会话。
- 在测试中真实创建 Asset / RentContract / RentTerm 数据，验证冲突检测与统计逻辑。
- 保持测试断言与业务逻辑一致，不依赖 MagicMock 断言调用次数。

## Agent Extensions

### SubAgent

- **code-explorer**
- Purpose: 扫描并定位所有依赖 Mock 查询分支的租赁合同相关测试
- Expected outcome: 输出需要改造为真实数据库会话的测试清单与引用位置