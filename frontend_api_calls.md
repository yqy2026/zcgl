# 前端API调用清单

## 服务文件分析

### 1. assetService.ts
- GET `/excel/export` - Excel导出
- POST `/excel/export` - 导出选中资产
- POST `/assets/import` - 资产导入
- POST `/assets/batch-update` - 批量更新资产
- DELETE `/assets/{id}` - 删除资产
- GET `/assets` - 获取资产列表
- GET `/statistics/basic` - 基础统计
- GET `/assets/ownership-entities` - 获取权属方列表
- GET `/assets/business-categories` - 获取业态类别列表
- POST `/assets/validate` - 资产验证
- GET `/excel/export-status/{taskId}` - 获取导出状态
- GET `/excel/export-history` - 获取导出历史
- DELETE `/excel/export-history/{id}` - 删除导出历史
- POST `/excel/import` - Excel导入
- POST `/excel/preview` - Excel预览
- GET `/excel/template` - 获取Excel模板
- GET `/excel/import-status/{importId}` - 获取导入状态
- GET `/excel/import-history` - 获取导入历史
- DELETE `/excel/import-history/{id}` - 删除导入历史
- POST `/assets/{assetId}/attachments` - 上传资产附件
- GET `/assets/{assetId}/attachments` - 获取资产附件列表
- DELETE `/assets/{assetId}/attachments/{attachmentId}` - 删除资产附件
- GET `/statistics/occupancy-rate/overall` - 整体出租率
- GET `/statistics/asset-distribution` - 资产分布统计
- GET `/statistics/area-statistics` - 面积统计
- GET `/statistics/comprehensive` - 综合统计
- GET `/statistics/area-summary` - 面积汇总
- GET `/statistics/financial-summary` - 财务汇总
- GET `/statistics/occupancy-rate/by-category` - 分类出租率
- GET `/system-dictionaries` - 获取系统字典
- GET `/system-dictionaries/{id}` - 获取字典详情
- POST `/system-dictionaries` - 创建字典
- PUT `/system-dictionaries/{id}` - 更新字典
- DELETE `/system-dictionaries/{id}` - 删除字典
- POST `/system-dictionaries/batch-update` - 批量更新字典
- GET `/system-dictionaries/types/list` - 获取字典类型列表
- GET `/asset-custom-fields` - 获取自定义字段
- GET `/asset-custom-fields/{id}` - 获取自定义字段详情
- POST `/asset-custom-fields` - 创建自定义字段
- PUT `/asset-custom-fields/{id}` - 更新自定义字段
- DELETE `/asset-custom-fields/{id}` - 删除自定义字段
- GET `/assets/{assetId}/custom-fields` - 获取资产自定义字段
- PUT `/assets/{assetId}/custom-fields` - 更新资产自定义字段
- POST `/assets/batch-custom-fields` - 批量更新自定义字段
- POST `/asset-custom-fields/validate` - 验证自定义字段
- GET `/field-options` - 获取字段选项

### 2. statisticsService.ts
- GET `/statistics/dashboard` - 仪表板数据
- GET `/statistics/basic` - 基础统计
- GET `/statistics/ownership-distribution` - 权属分布
- GET `/statistics/property-nature-distribution` - 物业性质分布
- GET `/statistics/usage-status-distribution` - 使用状态分布
- GET `/statistics/occupancy-rate/by-category` - 出租率分布
- GET `/statistics/area-summary` - 面积统计
- GET `/statistics/trend/{metric}` - 趋势数据
- POST `/statistics/report/{reportType}` - 生成报表
- GET `/statistics/comparison/{metric}` - 对比数据

### 3. excelService.ts
- POST `/excel/import` - Excel导入
- POST `/excel/export` - Excel导出
- GET `/excel/download/{filename}` - 下载文件
- GET `/excel/import/template` - 获取导入模板
- GET `/excel/import/history` - 导入历史
- GET `/excel/export/history` - 导出历史
- GET `/excel/import/status/{taskId}` - 导入状态
- GET `/excel/export/status/{taskId}` - 导出状态
- POST `/excel/import/cancel/{taskId}` - 取消导入
- POST `/excel/export/cancel/{taskId}` - 取消导出
- POST `/excel/validate` - 验证Excel
- GET `/excel/formats` - 获取格式
- GET `/excel/field-mapping` - 获取字段映射
- POST `/excel/field-mapping` - 更新字段映射

### 4. organizationService.ts
- GET `/organizations` - 获取组织列表
- GET `/organizations/tree` - 获取组织树
- GET `/organizations/search` - 搜索组织
- POST `/organizations/advanced-search` - 高级搜索
- GET `/organizations/statistics` - 获取组织统计
- GET `/organizations/{id}` - 获取组织详情
- GET `/organizations/{id}/children` - 获取子组织
- GET `/organizations/{id}/path` - 获取组织路径
- GET `/organizations/{id}/history` - 获取组织历史
- POST `/organizations` - 创建组织
- PUT `/organizations/{id}` - 更新组织
- DELETE `/organizations/{id}` - 删除组织
- POST `/organizations/{id}/move` - 移动组织
- POST `/organizations/batch` - 批量操作
- GET `/organizations/export` - 导出组织
- POST `/organizations/import` - 导入组织

### 5. ownershipService.ts
- GET `/ownerships` - 获取权属方列表
- POST `/ownershipssearch` - 搜索权属方
- GET `/ownerships/{id}` - 获取权属方详情
- POST `/ownerships` - 创建权属方
- PUT `/ownerships/{id}` - 更新权属方
- DELETE `/ownerships/{id}` - 删除权属方
- POST `/ownerships/{id}/toggle-status` - 切换权属方状态
- GET `/ownershipsstatistics/summary` - 获取权属方统计
- GET `/ownershipsdropdown-options` - 获取权属方选项
- PUT `/ownerships/{ownershipId}/projects` - 更新权属方项目

### 6. projectService.ts
- GET `/projects` - 获取项目列表
- POST `/projectssearch` - 搜索项目
- GET `/projects/{id}` - 获取项目详情
- POST `/projects` - 创建项目
- PUT `/projects/{id}` - 更新项目
- DELETE `/projects/{id}` - 删除项目
- POST `/projects/{id}/toggle-status` - 切换项目状态
- GET `/projectsstatistics/summary` - 获取项目统计
- GET `/projectsdropdown-options` - 获取项目选项

### 7. rentContractService.ts
- GET `/rent_contract/contracts` - 获取租金合同列表
- GET `/rent_contract/contracts/{id}` - 获取合同详情
- POST `/rent_contract/contracts` - 创建合同
- PUT `/rent_contract/contracts/{id}` - 更新合同
- DELETE `/rent_contract/contracts/{id}` - 删除合同
- GET `/rent_contract/contracts/{contractId}/terms` - 获取合同条款
- POST `/rent_contract/contracts/{contractId}/terms` - 添加合同条款
- GET `/rent_contract/ledger` - 获取租金台账
- GET `/rent_contract/ledger/{id}` - 获取台账详情
- PUT `/rent_contract/ledger/{id}` - 更新台账
- PUT `/rent_contract/ledger/batch` - 批量更新台账
- POST `/rent_contract/ledger/generate` - 生成台账
- GET `/rent_contract/statistics/overview` - 获取统计概览
- GET `/rent_contract/statistics/ownership` - 权属方统计
- GET `/rent_contract/statistics/asset` - 资产统计
- GET `/rent_contract/statistics/monthly` - 月度统计
- GET `/rent_contract/statistics/export` - 导出统计
- GET `/rent_contract/contracts/{contractId}/ledger` - 获取合同台账
- GET `/rent_contract/assets/{assetId}/contracts` - 获取资产合同
- GET `/rent_contract/contracts/export` - 导出合同
- GET `/rent_contract/ledger/export` - 导出台账

### 8. dictionaryService.ts
- GET `dictionaries/{dictType}/options` - 获取字典选项
- POST `dictionaries/{dictType}/quick-create` - 快速创建字典
- GET `dictionaries/types` - 获取字典类型
- POST `dictionaries/{dictType}/values` - 添加字典值
- DELETE `dictionaries/{dictType}` - 删除字典

### 9. backupService.ts
- GET `/backup/info/{filename}` - 获取备份信息
- DELETE `/backup/{filename}` - 删除备份
- POST `/backup/cleanup` - 清理备份
- GET `/backup/scheduler/status` - 获取调度状态
- POST `/backup/validate/{filename}` - 验证备份
- GET `/backup/statistics` - 获取备份统计

总计：约120+个API调用