# 统一字典服务使用指南

## 概述

统一字典服务提供了简洁、高效的字典数据获取和管理功能，整合了原有的多套字典服务，消除了功能重叠和数据冗余。作为土地物业资产管理系统的重要组成部分，该服务为前端应用提供了完整的字典数据支持。

## 架构设计

```
frontend/src/services/dictionary/
├── config.ts      # 字典配置和备用数据
├── base.ts        # 基础字典服务（核心功能）
├── manager.ts     # 字典管理服务（管理功能）
├── index.ts       # 统一入口和向后兼容
└── README.md      # 使用指南
```

## 快速开始

### 1. 基础使用（组件中）

```typescript
import { useDictionary } from '@/hooks/useDictionary'

function MyComponent() {
  const { options, loading, error } = useDictionary('property_nature')

  if (loading) return <Spin />
  if (error) return <Alert message="加载失败" type="error" />

  return (
    <Select>
      {options.map(option => (
        <Option key={option.value} value={option.value}>
          {option.label}
        </Option>
      ))}
    </Select>
  )
}
```

### 2. 批量使用（表单中）

```typescript
import { useDictionaries } from '@/hooks/useDictionary'

function AssetForm() {
  const dictionaries = useDictionaries([
    'property_nature',
    'usage_status',
    'ownership_status'
  ])

  const propertyNatureOptions = dictionaries.property_nature.options
  const usageStatusOptions = dictionaries.usage_status.options

  // 使用选项...
}
```

### 3. 直接使用服务

```typescript
import { dictionaryService } from '@/services/dictionary'

// 获取单个字典
const result = await dictionaryService.getOptions('property_nature')
if (result.success) {
  console.log('数据来源:', result.source) // 'api' | 'fallback' | 'cache'
  console.log('选项:', result.data)
}

// 批量获取
const batchResults = await dictionaryService.getBatchOptions([
  'property_nature',
  'usage_status'
])

// 预加载
await dictionaryService.preload(['property_nature', 'usage_status'])

// 获取可用类型
const types = dictionaryService.getAvailableTypes()
```

## 核心特性

### 1. 智能缓存
- 5分钟自动缓存
- 手动缓存清理
- 智能缓存失效

```typescript
// 清除特定字典缓存
dictionaryService.clearCache('property_nature')

// 清除所有缓存
dictionaryService.clearCache()

// 获取缓存统计
const stats = dictionaryService.getStats()
```

### 2. 备用数据
- API失败时自动降级
- 集中配置备用数据
- 保证离线可用性

```typescript
// 强制使用备用数据
const result = await dictionaryService.getOptions('property_nature', {
  useFallback: true,
  useCache: false
})
```

### 3. 错误处理
- 详细的错误信息
- 数据来源标识
- 优雅的降级处理

```typescript
interface DictionaryServiceResult {
  success: boolean
  data: DictionaryOption[]
  error?: string
  source: 'api' | 'fallback' | 'cache'
}
```

## 管理功能

### 1. 枚举字段管理

```typescript
// 获取所有枚举类型
const types = await dictionaryService.getEnumFieldTypes()

// 获取特定类型的值
const values = await dictionaryService.getEnumFieldValues(typeId)

// 创建新类型
const newType = await dictionaryService.createEnumFieldType({
  name: '自定义字典',
  code: 'custom_dict',
  description: '自定义字典类型'
})

// 添加枚举值
const newValue = await dictionaryService.addEnumFieldValue(typeId, {
  label: '选项1',
  value: 'option1',
  sort_order: 1
})
```

### 2. 验证功能

```typescript
// 验证字典类型代码
const validation = dictionaryService.validateEnumTypeCode('my_dict')
if (validation.valid) {
  // 代码有效
} else {
  console.log('错误:', validation.errors)
}
```

### 3. 统计信息

```typescript
// 获取字典统计
const stats = await dictionaryService.getDictionaryStats()
console.log('总类型数:', stats.totalTypes)
console.log('活跃类型数:', stats.activeTypes)
console.log('总数值数:', stats.totalValues)
```

## 与RBAC权限系统的集成

字典服务与系统的RBAC权限管理模块紧密集成，确保只有具有相应权限的用户才能管理字典数据：

- 字典类型管理需要 `dict_type:manage` 权限
- 字典值管理需要 `dict_value:manage` 权限
- 字典数据查看需要 `dict:read` 权限

## 配置字典

### 添加新字典类型

在 `config.ts` 中添加新的配置：

```typescript
export const DICTIONARY_CONFIGS: Record<string, DictionaryConfig> = {
  // 现有字典...
  
  // 资产管理相关字典
  property_nature: {
    code: 'property_nature',
    name: '物业性质',
    category: '资产管理',
    description: '物业的性质分类',
    apiEndpoint: '/api/v1/dictionaries/property_nature/options',
    fallbackOptions: [
      { label: '商业', value: 'commercial', sort_order: 1 },
      { label: '办公', value: 'office', sort_order: 2 },
      { label: '住宅', value: 'residential', sort_order: 3 }
    ]
  },

  usage_status: {
    code: 'usage_status',
    name: '使用状态',
    category: '资产管理',
    description: '资产的使用状态',
    apiEndpoint: '/api/v1/dictionaries/usage_status/options',
    fallbackOptions: [
      { label: '自用', value: 'self_use', sort_order: 1 },
      { label: '出租', value: 'rented', sort_order: 2 },
      { label: '空置', value: 'vacant', sort_order: 3 }
    ]
  },

  new_dictionary_type: {
    code: 'new_dictionary_type',
    name: '新字典类型',
    category: '分类',
    description: '新字典类型的描述',
    apiEndpoint: '/api/v1/dictionaries/new_dictionary_type/options',
    fallbackOptions: [
      { label: '选项1', value: 'option1', sort_order: 1 },
      { label: '选项2', value: 'option2', sort_order: 2 }
    ]
  }
}
```

## 迁移指南

### 从旧服务迁移

#### 1. 替换导入

```typescript
// 旧的方式
import { dictionaryService } from '@/services/dictionaryService'

// 新的方式
import { dictionaryService } from '@/services/dictionary'
```

#### 2. 更新调用方式

```typescript
// 旧的方式
const data = await dictionaryService.getOptions(dictType)

// 新的方式
const result = await dictionaryService.getOptions(dictType)
const data = result.success ? result.data : []
```

#### 3. 使用新特性

```typescript
// 使用批量加载
const results = await dictionaryService.getBatchOptions(dictTypes)

// 使用缓存控制
const result = await dictionaryService.getOptions(dictType, {
  useCache: true,
  useFallback: true
})
```

## 系统集成

字典服务与土地物业资产管理系统深度集成：

- 为58个资产字段提供字典数据支持
- 支持资产表单中的下拉选择和数据验证
- 与统计分析模块集成，提供维度分类
- 与权限管理模块集成，控制访问权限
- 支持组织架构相关的字典数据

## 最佳实践

### 1. 组件中使用
- 优先使用 `useDictionary` Hook
- 处理加载和错误状态
- 利用缓存提高性能

### 2. 表单中使用
- 使用 `useDictionaries` 批量加载
- 预加载常用字典类型
- 合理处理备用数据

### 3. 管理界面中使用
- 使用管理功能API
- 实现完整的CRUD操作
- 添加数据验证

### 4. 性能优化
- 合理使用缓存
- 批量加载减少请求
- 预加载常用数据

## 故障排除

### 1. 字典类型不存在
- 检查 `config.ts` 中是否有配置
- 确认字典类型代码正确
- 查看控制台错误信息

### 2. API请求失败
- 检查网络连接
- 确认后端服务正常运行
- 查看浏览器开发者工具

### 3. 数据为空
- 检查API响应
- 确认数据库中有数据
- 查看备用数据配置

### 4. 缓存问题
- 清除缓存重试
- 检查缓存配置
- 查看缓存统计信息

## 向后兼容

为了保持向后兼容性，统一服务导出了以下别名：

```typescript
export const unifiedDictionaryService = dictionaryService
export const enumFieldService = dictionaryManagerService
```

旧的代码可以继续工作，但建议逐步迁移到新的API。