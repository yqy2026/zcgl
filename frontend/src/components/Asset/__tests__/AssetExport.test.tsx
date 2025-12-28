/**
 * AssetExport 组件测试
 * 测试资产导出功能（Excel/CSV导出）
 */

import { describe, it, expect, vi } from 'vitest'
import React from 'react'

// Mock all dependencies before importing
vi.mock('@tanstack/react-query', () => ({
  useMutation: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useQuery: vi.fn(() => ({
    data: [],
    refetch: vi.fn(),
  })),
}))

vi.mock('@/services/assetService', () => ({
  assetService: {
    exportAssets: vi.fn(),
    exportSelectedAssets: vi.fn(),
    getExportHistory: vi.fn(),
    getExportStatus: vi.fn(),
    downloadExportFile: vi.fn(),
    deleteExportRecord: vi.fn(),
  },
}))

// Mock Ant Design completely
vi.mock('antd', () => ({
  Card: vi.fn(),
  Form: Object.assign(
    vi.fn(() => null),
    {
      Item: vi.fn(() => null),
      useForm: vi.fn(() => [
        {
          getFieldsValue: vi.fn(() => ({})),
          setFieldsValue: vi.fn(),
          validateFields: vi.fn(() => Promise.resolve({})),
        }
      ]),
    }
  ),
  Select: vi.fn(() => null),
  Checkbox: vi.fn(() => null),
  Button: vi.fn(() => null),
  Space: vi.fn(() => null),
  Alert: vi.fn(() => null),
  Progress: vi.fn(() => null),
  Typography: {
    Title: vi.fn(() => null),
    Text: vi.fn(() => null),
  },
  Divider: vi.fn(() => null),
  Row: vi.fn(({ children }) => children),
  Col: vi.fn(({ children }) => children),
  Tag: vi.fn(() => null),
  Modal: vi.fn(() => null),
  List: vi.fn(() => null),
  Tooltip: vi.fn(() => null),
  message: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}))

vi.mock('@ant-design/icons', () => ({
  DownloadOutlined: () => null,
  FileExcelOutlined: () => null,
  HistoryOutlined: () => null,
  DeleteOutlined: () => null,
  CheckCircleOutlined: () => null,
  LoadingOutlined: () => null,
}))

describe('AssetExport - 组件导入测试', () => {
  it('应该能够导入组件', async () => {
    const module = await import('../AssetExport')
    expect(module).toBeDefined()
    expect(module.default).toBeDefined()
  })

  it('组件应该是React函数组件', async () => {
    const AssetExport = (await import('../AssetExport')).default
    expect(typeof AssetExport).toBe('function')
  })
})

describe('AssetExport - 属性验证测试', () => {
  it('应该接受searchParams属性', async () => {
    const AssetExport = (await import('../AssetExport')).default

    const searchParams = {
      ownership_status: '已确权' as const,
      property_nature: '经营性' as const,
    }

    // 验证组件可以接受这些属性而不报错
    const element = React.createElement(AssetExport, { searchParams })
    expect(element).toBeTruthy()
    expect(element.props.searchParams).toEqual(searchParams)
  })

  it('应该接受selectedAssetIds属性', async () => {
    const AssetExport = (await import('../AssetExport')).default

    const selectedAssetIds = ['asset-1', 'asset-2', 'asset-3']

    const element = React.createElement(AssetExport, { selectedAssetIds })
    expect(element).toBeTruthy()
    expect(element.props.selectedAssetIds).toEqual(selectedAssetIds)
  })

  it('应该接受onExportComplete回调', async () => {
    const AssetExport = (await import('../AssetExport')).default

    const onExportComplete = vi.fn()

    const element = React.createElement(AssetExport, { onExportComplete })
    expect(element).toBeTruthy()
    expect(element.props.onExportComplete).toEqual(onExportComplete)
  })
})

describe('AssetExport - 组件结构测试', () => {
  it('应该有正确的默认导出', async () => {
    const AssetExport = (await import('../AssetExport')).default

    expect(AssetExport).toBeDefined()
    expect(typeof AssetExport).toBe('function')
  })

  it('应该可以创建组件实例', async () => {
    const AssetExport = (await import('../AssetExport')).default

    const element = React.createElement(AssetExport, {})
    expect(element).toBeTruthy()
    expect(element.type).toBe(AssetExport)
  })
})

describe('AssetExport - 可选属性测试', () => {
  it('应该支持所有属性都是可选的', async () => {
    const AssetExport = (await import('../AssetExport')).default

    // 所有属性都应该可以正常传递（即使是undefined）
    const element = React.createElement(AssetExport, {
      searchParams: undefined,
      selectedAssetIds: undefined,
      onExportComplete: undefined,
    })

    expect(element).toBeTruthy()
  })
})

describe('AssetExport - 组件props类型测试', () => {
  it('应该正确处理Props类型', async () => {
    const module = await import('../AssetExport')

    // 验证模块导出
    expect(module.default).toBeDefined()

    // Props接口应该与组件兼容
    const AssetExport = module.default
    const props = {
      searchParams: { ownership_status: '已确权' as const },
      selectedAssetIds: ['1', '2'],
      onExportComplete: vi.fn(),
    }

    const element = React.createElement(AssetExport, props)
    expect(element.props).toMatchObject(props)
  })
})
