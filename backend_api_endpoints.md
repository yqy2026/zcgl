# 后端API端点清单

## API模块结构

### 1. 认证模块 (/api/v1/auth)
- POST `/auth/login` - 用户登录
- POST `/auth/logout` - 用户登出
- POST `/auth/refresh` - 刷新令牌
- GET `/auth/me` - 获取当前用户信息
- GET `/auth/users` - 获取用户列表
- GET `/auth/users/search` - 搜索用户
- POST `/auth/users` - 创建用户
- GET `/auth/users/{user_id}` - 获取用户详情
- PUT `/auth/users/{user_id}` - 更新用户
- POST `/auth/users/{user_id}/change-password` - 修改密码
- POST `/auth/users/{user_id}/deactivate` - 停用用户
- DELETE `/auth/users/{user_id}` - 删除用户
- POST `/auth/users/{user_id}/activate` - 激活用户
- GET `/auth/users/{user_id}/unlock` - 解锁用户
- GET `/auth/sessions` - 获取用户会话列表
- DELETE `/auth/sessions/{session_id}` - 撤销会话
- GET `/auth/audit-logs` - 获取审计日志统计
- GET `/auth/security/config` - 获取安全配置

### 2. 资产管理模块 (/api/v1/assets)
- GET `/assets/dev-test` - 开发模式测试端点
- GET `/assets/temp-test` - 临时API测试
- GET `/assets/test-api` - API测试
- GET `/assets/list-test` - 资产列表测试
- GET `/assets` - 获取资产列表
- GET `/assets/ownership-entities` - 获取权属方列表
- GET `/assets/business-categories` - 获取业态类别列表
- GET `/assets/usage-statuses` - 获取使用情况列表
- GET `/assets/property-natures` - 获取物业性质列表
- GET `/assets/ownership-statuses` - 获取确权状态列表
- GET `/assets/{asset_id}` - 获取资产详情
- POST `/assets` - 创建新资产
- PUT `/assets/{asset_id}` - 更新资产
- DELETE `/assets/{asset_id}` - 删除资产
- GET `/assets/{asset_id}/history` - 获取资产历史
- GET `/assets/statistics/summary` - 获取资产统计摘要
- POST `/assets/{asset_id}/attachments` - 上传资产附件
- GET `/assets/{asset_id}/attachments` - 获取资产附件列表
- GET `/assets/{asset_id}/attachments/{filename}` - 下载资产附件
- DELETE `/assets/{asset_id}/attachments/{attachment_id}` - 删除资产附件

### 3. Excel导入导出模块 (/api/v1/excel)
- GET `/excel/template` - 下载Excel导入模板
- GET `/excel/test` - 测试端点
- POST `/excel/preview` - 预览Excel文件内容
- POST `/excel/import` - 导入Excel数据
- GET `/excel/export` - 导出Excel文件
- POST `/excel/export` - 导出选中资产Excel文件

### 4. 统计分析模块 (/api/v1/statistics)
- GET `/statistics/basic` - 获取基础统计数据
- GET `/statistics/summary` - 获取统计摘要
- GET `/statistics/occupancy-rate/overall` - 获取整体出租率统计
- GET `/statistics/occupancy-rate/by-category` - 按类别获取出租率统计
- GET `/statistics/area-summary` - 获取面积汇总统计
- GET `/statistics/financial-summary` - 获取财务汇总统计
- POST `/statistics/cache/clear` - 清除统计数据缓存
- GET `/statistics/cache/info` - 获取缓存信息

### 5. 出租率模块 (/api/v1/occupancy)
- GET `/occupancy/rate` - 计算出租率
- GET `/occupancy/analysis` - 出租率分析
- GET `/occupancy/trends` - 出租率趋势

### 6. 权属方管理模块 (/api/v1/ownerships)
- GET `/ownerships/dropdown-options` - 获取权属方选项列表
- POST `/ownerships` - 创建权属方
- GET `/ownerships/{ownership_id}` - 获取权属方详情
- PUT `/ownerships/{ownership_id}` - 更新权属方
- PUT `/ownerships/{ownership_id}/projects` - 更新权属方关联项目
- DELETE `/ownerships/{ownership_id}` - 删除权属方
- GET `/ownerships` - 获取权属方列表
- POST `/ownerships/search` - 搜索权属方
- GET `/ownerships/statistics/summary` - 获取权属方统计
- POST `/ownerships/{ownership_id}/toggle-status` - 切换权属方状态

### 7. 项目管理模块 (/api/v1/projects)
- GET `/projects/dropdown-options` - 获取项目选项列表
- POST `/projects` - 创建项目
- GET `/projects/{project_id}` - 获取项目详情
- PUT `/projects/{project_id}` - 更新项目
- DELETE `/projects/{project_id}` - 删除项目
- GET `/projects` - 获取项目列表
- POST `/projects/search` - 搜索项目
- GET `/projects/statistics/summary` - 获取项目统计
- POST `/projects/{project_id}/toggle-status` - 切换项目状态

### 8. 租金合同模块 (/api/v1/rent_contract)
- POST `/rent_contract/contracts` - 创建租金合同
- GET `/rent_contract/contracts/{contract_id}` - 获取租金合同详情
- GET `/rent_contract/contracts` - 获取租金合同列表
- PUT `/rent_contract/contracts/{contract_id}` - 更新租金合同
- DELETE `/rent_contract/contracts/{contract_id}` - 删除租金合同
- GET `/rent_contract/contracts/{contract_id}/terms` - 获取合同租金条款
- POST `/rent_contract/contracts/{contract_id}/terms` - 添加租金条款
- POST `/rent_contract/ledger/generate` - 生成月度台账
- GET `/rent_contract/ledger` - 获取租金台账列表
- GET `/rent_contract/ledger/{ledger_id}` - 获取租金台账详情
- PUT `/rent_contract/ledger/{ledger_id}` - 更新租金台账
- PUT `/rent_contract/ledger/batch` - 批量更新租金台账
- GET `/rent_contract/statistics/overview` - 获取租金统计概览
- GET `/rent_contract/statistics/ownership` - 权属方租金统计
- GET `/rent_contract/statistics/asset` - 资产租金统计
- GET `/rent_contract/statistics/monthly` - 月度租金统计
- GET `/rent_contract/statistics/export` - 导出统计数据

### 9. PDF导入模块 (/api/v1/pdf_import)
- GET `/pdf_import/info` - 获取系统信息
- GET `/pdf_import/test_system` - 测试系统
- POST `/pdf_import/upload` - 上传文件
- GET `/pdf_import/progress/{session_id}` - 获取处理进度
- GET `/pdf_import/sessions` - 获取活跃会话
- GET `/pdf_import/sessions/history` - 获取历史会话
- POST `/pdf_import/confirm_import` - 确认导入
- DELETE `/pdf_import/session/{session_id}` - 删除会话
- GET `/pdf_import/test` - 测试
- GET `/pdf_import/health` - 健康检查
- POST `/pdf_import/extract` - 提取信息
- POST `/pdf_import/upload_and_extract` - 上传并提取

### 10. 综合分析模块 (/api/v1/analytics)
- GET `/analytics/comprehensive` - 获取综合统计分析数据
- GET `/analytics/cache/stats` - 获取缓存统计信息
- POST `/analytics/cache/clear` - 清除分析缓存

### 11. 其他模块
- 系统管理 (/api/v1/admin)
- 数据备份 (/api/v1/backup)
- 自定义字段 (/api/v1/asset-custom-fields)
- 组织架构 (/api/v1/organizations)
- 枚举字段 (/api/v1/enum_field)
- 统一字典 (/api/v1/dictionaries)
- 历史记录 (/api/v1/history)
- 中文OCR (/api/v1/chinese_ocr)
- 性能监控 (/api/v1/performance)
- 数据导出 (/api/v1/export)
- 系统监控 (/api/v1/monitoring)

总计：约150+个API端点