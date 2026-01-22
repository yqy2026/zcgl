# 产权证管理功能实现计划

## 概述

新增产权证管理功能,支持4种权属证书类型(不动产权证、房屋所有权证、土地使用证、其他权属证明)的上传识别、字段提取、CRUD管理和资产关联。

**设计原则**:
- 复用现有LLM Vision服务和文档提取架构
- 参考合同模块的成功模式
- 多对多关联设计(产权证↔资产, 产权证↔权利人)
- 独立权利人表+可选组织关联
- 多维度置信度评分机制

**预计工期**: 12个工作日

---

## 核心功能

### 1. 数据模型设计
- 产权证主表 (`PropertyCertificate`) - 包含基本信息、房屋信息、土地信息、限制信息
- 权利人表 (`PropertyOwner`) - 独立存储,支持个人/组织/共有
- 多对多关联表:
  - `property_cert_assets` - 产权证↔资产
  - `property_certificate_owners` - 产权证↔权利人(支持拥有权比例)
  - `property_owner_organizations` - 权利人↔组织(可选)
- 附件表 (`PropertyCertificateAttachment`) - 支持多个扫描件
- 历史记录表 (`PropertyCertificateHistory`) - 审计追踪

### 2. 字段提取和验证
- **4种证书类型专用Prompt模板**:
  - 不动产权证(新版): 包含所有字段(房屋+土地)
  - 房屋所有权证(旧版): 仅房屋字段,土地字段为null
  - 土地使用证: 仅土地字段,房屋字段为null
  - 其他权属证明: 仅提取基本信息
- **字段验证器** (`PropertyCertificateValidator`):
  - 必填字段检查(按证书类型)
  - 格式验证(证书编号、日期、面积、权利比例)
  - 逻辑一致性检查(日期范围、面积关系)
- **置信度评分** (`ConfidenceScoreCalculator`):
  - 4个维度: 字段覆盖率(25%) + 格式有效性(30%) + 逻辑一致性(20%) + LLM可靠性(25%)
  - 评分标准: ≥90优秀, 70-89中等需复核, <70低质量必须修正

### 3. API端点设计
**CRUD操作**:
- `POST /api/v1/property-certificates/` - 创建产权证(手动或导入会话)
- `GET /api/v1/property-certificates/` - 列表查询(分页、多条件筛选)
- `GET /api/v1/property-certificates/{id}` - 详情(包含权利人、资产)
- `PUT /api/v1/property-certificates/{id}` - 更新
- `DELETE /api/v1/property-certificates/{id}` - 删除(仅管理员)

**文件上传和识别**:
- `POST /api/v1/property-certificates/upload` - 上传并识别,返回提取结果和session_id
- `POST /api/v1/property-certificates/confirm-import` - 确认导入,创建记录

**关联管理**:
- `POST /api/v1/property-certificates/{id}/assets` - 批量关联资产
- `DELETE /api/v1/property-certificates/{id}/assets/{asset_id}` - 取消关联
- `POST /api/v1/property-certificates/{id}/owners` - 添加权利人
- `DELETE /api/v1/property-certificates/{id}/owners/{owner_id}` - 移除权利人

**附件管理**:
- `POST /api/v1/property-certificates/{id}/attachments` - 上传附件
- `GET /api/v1/property-certificates/{id}/attachments` - 附件列表

**批量操作**:
- `POST /api/v1/property-certificates/batch/delete` - 批量删除
- `POST /api/v1/property-certificates/batch/update-status` - 批量更新状态

**统计查询**:
- `GET /api/v1/property-certificates/statistics/overview` - 统计概览

### 4. 前端页面设计
- **列表页** (`PropertyCertificateListPage.tsx`):
  - 多条件筛选(证书编号、权利人、地址、类型、关联资产)
  - 表格展示(分页、排序、批量操作)
  - 操作: 新建、查看、编辑、删除、关联资产

- **上传识别页** (`PropertyCertificateImportPage.tsx`):
  - 3步流程: 上传文件 → 审核确认 → 完成
  - 文件上传组件(支持PDF/图片,拖拽上传)
  - 证书类型选择器
  - 识别进度显示

- **审核确认组件** (`PropertyCertificateReview.tsx`):
  - 置信度评分展示(4维度统计卡片)
  - 验证错误和警告提示
  - 系统建议列表
  - Tab分组表单: 基本信息、房屋信息、土地信息、其他信息
  - 字段来源标记(自动提取/手动输入)
  - 资产关联选择器(可选)

- **详情编辑页** (`PropertyCertificateDetailPage.tsx`):
  - 查看模式: 完整信息展示、关联资产列表、权利人列表、附件列表
  - 编辑模式: 复用审核表单组件

---

## 关键文件清单

### 后端文件

| 文件路径 | 说明 | 优先级 |
|---------|------|--------|
| `backend/src/models/property_certificate.py` | 数据模型定义(7个表,枚举类型) | P0 |
| `backend/src/schemas/property_certificate.py` | Pydantic Schema(Create/Update/Response) | P0 |
| `backend/src/crud/property_certificate.py` | CRUD基础类(继承CRUDBase) | P0 |
| `backend/src/crud/property_owner.py` | 权利人CRUD | P0 |
| `backend/src/services/document/extractors/property_cert_adapter.py` | **增强**: 4种Prompt模板 | P0 |
| `backend/src/services/property_certificate/validation.py` | 验证器和评分计算器 | P0 |
| `backend/src/services/property_certificate/service.py` | 业务逻辑Service层 | P0 |
| `backend/src/api/v1/property_certificate.py` | API路由定义 | P0 |
| `backend/alembic/versions/xxxx_add_property_cert_tables.py` | 数据库迁移脚本 | P0 |

### 前端文件

| 文件路径 | 说明 | 优先级 |
|---------|------|--------|
| `frontend/src/types/propertyCertificate.ts` | TypeScript类型定义 | P0 |
| `frontend/src/services/propertyCertificateService.ts` | API服务封装 | P0 |
| `frontend/src/pages/PropertyCertificate/PropertyCertificateListPage.tsx` | 列表页面 | P0 |
| `frontend/src/pages/PropertyCertificate/PropertyCertificateImportPage.tsx` | 上传识别页面 | P0 |
| `frontend/src/pages/PropertyCertificate/PropertyCertificateDetailPage.tsx` | 详情编辑页面 | P1 |
| `frontend/src/pages/PropertyCertificate/components/PropertyCertificateUpload.tsx` | 上传组件 | P0 |
| `frontend/src/pages/PropertyCertificate/components/PropertyCertificateReview.tsx` | 审核确认组件 | P0 |
| `frontend/src/pages/PropertyCertificate/components/PropertyCertificateAssetLink.tsx` | 资产关联组件 | P1 |

---

## 实施步骤

### 阶段1: 数据模型和Schema (2天)

**任务**:
1. 创建 `backend/src/models/property_certificate.py`
   - 定义3个枚举: `CertificateType`, `OwnerType`, `LandUseType`
   - 定义7个模型类
   - 配置所有关联关系
   - 添加索引和约束

2. 创建 `backend/src/schemas/property_certificate.py`
   - `PropertyCertificateCreate` - 包含asset_ids, owner_ids
   - `PropertyCertificateUpdate` - 所有字段可选
   - `PropertyCertificateResponse` - 完整响应(包含关联)
   - `PropertyCertificateListResponse` - 列表响应(分页)
   - `CertificateImportResult` - 上传识别结果

3. 创建 `backend/src/crud/property_certificate.py`
   - `property_certificate_crud = CRUDBase(PropertyCertificate)`
   - `get_by_certificate_number()` - 证书编号查询
   - `get_with_details()` - 包含关联的详情查询
   - `get_multi_with_filters()` - 多条件筛选列表查询

4. 创建 `backend/src/crud/property_owner.py`
   - `property_owner_crud = CRUDBase(PropertyOwner)`
   - `get_by_name()` - 姓名查重

5. 创建数据库迁移脚本
   - 使用 `alembic revision -m "add property certificate tables"`
   - 定义 `upgrade()` 创建所有表和枚举
   - 定义 `downgrade()` 删除所有表和枚举

6. 运行迁移: `alembic upgrade head`

**验收标准**:
- 数据库中所有7个表创建成功
- 枚举类型正确创建
- 外键约束生效
- 索引正确建立

---

### 阶段2: 字段提取和验证 (2天)

**任务**:
1. 增强 `backend/src/services/document/extractors/property_cert_adapter.py`
   - 添加4个专用Prompt模板(类属性)
   - 修改 `extract()` 方法支持证书类型参数
   - 实现字段映射逻辑(新版→旧版字段转换)

2. 创建 `backend/src/services/property_certificate/validation.py`
   - 实现 `PropertyCertificateValidator.validate_extracted_fields()`
     - 必填字段检查(按证书类型)
     - 证书编号格式验证
     - 面积字段数值验证
     - 日期格式验证
     - 权利比例验证
     - 日期逻辑验证(起止日期)
     - 面积逻辑验证(建筑面积vs实际面积)

   - 实现 `ConfidenceScoreCalculator.calculate()`
     - 字段覆盖率计算
     - 格式有效性评分
     - 逻辑一致性评分
     - 综合评分计算

3. 更新 `DocumentType.PROPERTY_CERT` 的处理逻辑
   - 在 `extraction_manager.py` 中确保产权证类型路由到 `PropertyCertAdapter`

4. 编写单元测试
   - `tests/unit/services/property_certificate/test_validation.py`
   - 测试各种验证场景(有效/无效/边界情况)
   - 测试评分计算(完美/高/中/低分)

**验收标准**:
- 4种证书类型的Prompt能正确提取字段
- 验证器能识别所有错误和警告
- 评分计算准确反映数据质量
- 单元测试覆盖率 > 80%

---

### 阶段3: Service和API层 (3天)

**任务**:
1. 创建 `backend/src/services/property_certificate/service.py`
   - `create_certificate()` - 创建产权证(验证+查重+关联)
   - `update_certificate()` - 更新产权证+历史记录
   - `extract_from_file()` - 调用文档提取服务
   - `confirm_import()` - 确认导入创建记录
   - `link_assets()` / `unlink_asset()` - 资产关联管理
   - `add_owner()` / `remove_owner()` - 权利人管理
   - `batch_delete()` / `batch_update_status()` - 批量操作
   - `get_statistics()` - 统计查询
   - `_create_history()` - 创建历史记录(私有方法)

2. 创建 `backend/src/api/v1/property_certificate.py`
   - 实现所有API端点(参考设计文档)
   - 集成权限验证(`get_current_active_user`)
   - 统一错误处理(`ResponseHandler`)
   - 添加API文档注释

3. 注册路由
   - 在 `property_certificate.py` 底部调用 `route_registry.register_router()`
   - 验证路由注册成功: `http://localhost:8002/docs`

4. 编写集成测试
   - `tests/integration/api/property_certificate/test_certificate_api.py`
   - 测试所有API端点
   - 测试权限控制
   - 测试错误处理

**验收标准**:
- 所有API端点正常工作
- 业务逻辑验证生效
- 权限控制正确
- 集成测试通过
- API文档完整

---

### 阶段4: 前端页面和组件 (4天)

**任务**:
1. 创建类型定义 `frontend/src/types/propertyCertificate.ts`
   ```typescript
   export interface PropertyCertificate { ... }
   export interface PropertyOwner { ... }
   export interface CertificateImportResult { ... }
   export enum CertificateType { ... }
   ```

2. 创建API服务 `frontend/src/services/propertyCertificateService.ts`
   - 参考 `pdfImportService.ts` 的封装方式
   - 使用 `apiClient` 发送请求
   - 定义所有API调用方法

3. 创建上传识别页面 `PropertyCertificateImportPage.tsx`
   - 参考 `ContractImportReview.tsx` 的布局
   - 实现3步流程(上传→审核→完成)
   - 集成文件上传组件
   - 集成审核确认组件

4. 创建上传组件 `PropertyCertificateUpload.tsx`
   - 参考 `ContractImportUpload.tsx`
   - 支持证书类型选择
   - 支持拖拽上传
   - 显示上传进度

5. 创建审核确认组件 `PropertyCertificateReview.tsx`
   - 4个统计卡片: 总分、字段覆盖率、格式有效性、逻辑一致性
   - 错误/警告/建议Alert组件
   - Tab分组表单:
     - 基本信息Tab: 证书编号、类型、登记日期、权利人信息、地址
     - 房屋信息Tab: 用途、结构、面积、楼层、建筑年份
     - 土地信息Tab: 土地面积、使用类型、使用期限
     - 其他信息Tab: 共有情况、限制信息、备注
   - 字段来源Tag(自动提取/手动输入)
   - 资产关联选择器(可选)

6. 创建列表页面 `PropertyCertificateListPage.tsx`
   - 参考 `AssetListPage` 和 `ContractListPage`
   - 筛选表单: 证书编号、权利人、地址、类型、资产
   - 数据表格: 展示关键信息
   - 操作按钮: 新建、查看、编辑、删除

7. 创建详情编辑页面 `PropertyCertificateDetailPage.tsx`
   - 查看模式: 完整信息展示
   - 编辑模式: 复用审核表单组件

8. 添加路由配置
   - 在 `frontend/src/router/index.tsx` 中添加路由
   - `/property-certificates` - 列表页
   - `/property-certificates/new` - 手动创建
   - `/property-certificates/import` - 上传识别
   - `/property-certificates/:id` - 详情页

9. 编写前端测试
   - 组件单元测试
   - E2E测试(上传识别流程)

**验收标准**:
- 所有页面正常渲染
- 上传识别流程完整可用
- 表单验证生效
- 数据正确展示和提交
- 前端测试通过

---

### 阶段5: 文档和优化 (1天)

**任务**:
1. 编写API文档
   - 更新 `backend/docs/api.md`
   - 添加产权证相关API文档
   - 提供请求/响应示例

2. 编写用户使用指南
   - 如何上传识别产权证
   - 如何关联资产
   - 如何管理权利人
   - 常见问题解答

3. 性能优化
   - 列表查询优化(添加必要索引)
   - 文件上传优化(断点续传)
   - LLM调用优化(缓存机制)

4. Bug修复
   - 修复测试中发现的问题
   - 修复用户反馈的问题

**验收标准**:
- 文档完整准确
- 性能满足要求
- 无关键Bug

---

## 关键决策点

### 1. 权利人独立存储
**决策**: 使用独立的 `PropertyOwner` 表,支持多人共有

**理由**:
- 避免权利人信息重复
- 支持多人共有场景
- 可选关联组织表(企业权利人)
- 便于权利人信息统一管理

**权衡**: 增加一次关联查询,但通过ORM eager loading优化

### 2. 多对多关联
**决策**: 产权证与资产、权利人均为多对多关系

**理由**:
- 一个产权证可能对应多个资产(如一栋楼多个单元)
- 一个资产可能有多个产权证(如分批取得的土地)
- 一个产权证可能有多个权利人(共有)

**实现**: 使用中间表存储关联关系,支持额外字段(如拥有权比例)

### 3. 证书类型处理
**决策**: 4种证书类型使用不同的Prompt模板,但统一数据模型

**理由**:
- 新版不动产权证字段最全,作为统一模型
- 旧版房产证和土地证是其子集
- 专用Prompt提高提取准确率

**实现**: 在 `PropertyCertAdapter.extract()` 中根据类型选择Prompt

### 4. 置信度评分
**决策**: 4维度加权评分(字段覆盖率25% + 格式有效性30% + 逻辑一致性20% + LLM可靠性25%)

**理由**:
- 多维度评估更全面
- 帮助用户识别需要复核的记录
- 数据质量持续改进

**标准**:
- ≥90分: 高质量,可直接使用
- 70-89分: 中等质量,建议复核
- <70分: 低质量,必须人工修正

### 5. 前端组件复用
**决策**: 复用合同模块的上传-识别-审核流程

**复用**:
- `PropertyCertificateUpload` ← `ContractImportUpload`
- `PropertyCertificateReview` ← `ContractImportReview`
- Steps流程、表单验证、文件上传逻辑

**定制**: 字段不同、置信度评分显示、证书类型选择器

---

## 测试策略

### 单元测试
- **验证器测试**: 测试各种字段的验证规则
- **评分计算测试**: 测试不同场景的评分结果
- **Service层测试**: 测试业务逻辑

### 集成测试
- **API端点测试**: 测试所有API的请求响应
- **权限测试**: 测试RBAC权限控制
- **错误处理测试**: 测试各种异常情况

### E2E测试
- **上传识别流程**: 测试从上传到导入的完整流程
- **CRUD操作**: 测试创建、读取、更新、删除
- **关联管理**: 测试资产和权利人关联

---

## 风险和缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM识别准确率不足 | 提取字段错误,用户需要大量手动修正 | 1. 优化Prompt模板<br>2. 提供置信度评分<br>3. 支持手动修正 |
| 证书类型复杂 | 某些地区证书格式特殊,识别失败 | 1. 收集样本持续优化<br>2. 提供"其他"类型兜底<br>3. 支持纯手动创建 |
| 多对多关联复杂 | 关联管理逻辑复杂,容易出错 | 1. 清晰的API设计<br>2. 完整的测试覆盖<br>3. 用户友好的界面 |
| 性能问题 | 大量文件上传和LLM调用导致性能下降 | 1. 实现队列机制<br>2. 添加缓存<br>3. 异步处理 |

---

## 成功标准

### 功能完整性
- ✅ 支持4种证书类型的识别
- ✅ 提取准确率 > 85%
- ✅ 支持手动创建和上传识别两种方式
- ✅ 支持资产和权利人关联
- ✅ 支持附件管理
- ✅ 支持历史记录审计

### 性能指标
- ✅ 文件上传 < 10秒(10MB以内)
- ✅ LLM识别 < 30秒
- ✅ 列表查询 < 1秒(1000条记录)

### 数据质量
- ✅ 置信度评分准确反映数据质量
- ✅ 验证器能识别所有必填字段缺失
- ✅ 逻辑检查能发现日期和面积异常

### 用户体验
- ✅ 上传识别流程流畅(< 3步完成)
- ✅ 错误提示清晰准确
- ✅ 表单验证实时反馈
- ✅ 支持批量操作

---

## 后续优化方向

1. **识别准确率提升**
   - 收集更多样本数据
   - 微调LLM Prompt
   - 考虑使用更高级的Vision模型

2. **功能增强**
   - 支持批量上传识别
   - 支持产权证到期提醒
   - 支持产权证变更记录

3. **性能优化**
   - 实现Redis缓存
   - 优化数据库查询
   - 异步处理大批量任务

4. **移动端支持**
   - 响应式设计优化
   - 移动端专用组件

---

## 参考文档

- 项目根目录: `CLAUDE.md`
- 后端开发指南: `backend/CLAUDE.md`
- 前端开发指南: `frontend/CLAUDE.md`
- 合同模块实现: `backend/src/models/rent_contract.py`, `backend/src/services/rent_contract/service.py`
- 文档提取服务: `backend/src/services/document/extraction_manager.py`
- 前端上传组件: `frontend/src/pages/Contract/ContractImportReview.tsx`
