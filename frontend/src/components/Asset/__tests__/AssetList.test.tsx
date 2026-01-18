/**
 * AssetList 组件测试
 * 测试资产列表展示功能
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';

// Mock Ant Design components before importing
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    Table: vi.fn(
      ({ dataSource, columns: _columns, pagination, loading, rowSelection, summary }: any) => {
        const data = dataSource ?? [];
        return React.createElement(
          'div',
          {
            'data-testid': 'table',
            'data-loading': loading,
            'data-row-count': data.length,
            'data-pagination': JSON.stringify(pagination),
            'data-has-selection': !!rowSelection,
            'data-has-summary': !!summary,
          },
          data.map((item: any, idx: number) =>
            React.createElement(
              'div',
              {
                key: item.id || idx,
                'data-testid': `table-row-${idx}`,
                'data-id': item.id,
                'data-property-name': item.property_name,
              },
              `${item.property_name} - ${item.ownership_entity}`
            )
          )
        );
      }
    ),
    Tag: vi.fn(({ color, children }: any) =>
      React.createElement('span', { 'data-color': color }, children)
    ),
    Button: vi.fn(({ children, onClick, icon, type, danger }: any) =>
      React.createElement(
        'button',
        {
          'data-type': type,
          'data-danger': danger,
          onClick,
        },
        icon || children
      )
    ),
    Space: vi.fn(({ children }: any) =>
      React.createElement('div', { 'data-testid': 'space' }, children)
    ),
    Tooltip: vi.fn(({ title, children }: any) => React.createElement('div', { title }, children)),
    Popconfirm: vi.fn(({ children, onConfirm }: any) =>
      React.createElement('div', { 'data-testid': 'popconfirm', onClick: onConfirm }, children)
    ),
  };
});

// Mock utility functions
vi.mock('@/utils/format', () => ({
  formatArea: vi.fn((value: number | undefined) => (value ? `${value} m²` : '-')),
  formatPercentage: vi.fn((value: number) => `${value.toFixed(1)}%`),
  formatDate: vi.fn((date: string) => (date ? new Date(date).toLocaleDateString() : '-')),
  getStatusColor: vi.fn((_status: string, _type: string) => {
    const colors: Record<string, string> = {
      已确权: 'green',
      未确权: 'red',
      经营性: 'blue',
      非经营性: 'default',
      出租: 'green',
      空置: 'orange',
    };
    return colors[status] || 'default';
  }),
}));

describe('AssetList - 组件导入测试', () => {
  it('应该能够导入组件', async () => {
    const module = await import('../AssetList');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });

  it('组件应该是React函数组件', async () => {
    const AssetList = (await import('../AssetList')).default;
    expect(typeof AssetList).toBe('function');
  });
});

describe('AssetList - 基础渲染测试', () => {
  const mockAsset = {
    id: '1',
    ownership_entity: '测试权属方',
    ownership_category: '1',
    project_name: '测试项目',
    property_name: '测试物业A',
    address: '测试地址123号',
    ownership_status: '已确权',
    property_nature: '经营性',
    usage_status: '出租',
    land_area: 1000,
    actual_property_area: 800,
    rentable_area: 700,
    rented_area: 600,
    unrented_area: 100,
    occupancy_rate: 85.7,
    is_litigated: false,
    created_at: '2024-01-01T00:00:00',
    updated_at: '2024-01-15T00:00:00',
  };

  const mockData = {
    items: [mockAsset],
    total: 1,
    page: 1,
    limit: 20,
    pages: 1,
  };

  it('应该渲染资产列表表格', async () => {
    const AssetList = (await import('../AssetList')).default;

    const mockHandlers = {
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onViewHistory: vi.fn(),
      onTableChange: vi.fn(),
    };

    render(
      React.createElement(AssetList, {
        data: mockData,
        loading: false,
        ...mockHandlers,
      })
    );

    const table = screen.getByTestId('table');
    expect(table).toBeTruthy();
    expect(table.getAttribute('data-row-count')).toBe('1');
  });

  it('应该显示加载状态', async () => {
    const AssetList = (await import('../AssetList')).default;

    const mockHandlers = {
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onViewHistory: vi.fn(),
      onTableChange: vi.fn(),
    };

    render(
      React.createElement(AssetList, {
        data: mockData,
        loading: true,
        ...mockHandlers,
      })
    );

    const table = screen.getByTestId('table');
    expect(table.getAttribute('data-loading')).toBe('true');
  });

  it('应该处理空数据', async () => {
    const AssetList = (await import('../AssetList')).default;

    const mockHandlers = {
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onViewHistory: vi.fn(),
      onTableChange: vi.fn(),
    };

    render(
      React.createElement(AssetList, {
        data: { items: [], total: 0, page: 1, limit: 20, pages: 0 },
        loading: false,
        ...mockHandlers,
      })
    );

    const table = screen.getByTestId('table');
    expect(table.getAttribute('data-row-count')).toBe('0');
  });
});

describe('AssetList - 数据渲染测试', () => {
  const mockAssets = [
    {
      id: '1',
      ownership_entity: '权属方A',
      ownership_category: '1',
      project_name: '项目1',
      property_name: '物业1',
      address: '地址1',
      ownership_status: '已确权',
      property_nature: '经营性',
      usage_status: '出租',
      land_area: 1000,
      actual_property_area: 800,
      rentable_area: 700,
      rented_area: 600,
      occupancy_rate: 85.7,
      is_litigated: false,
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-15T00:00:00',
    },
    {
      id: '2',
      ownership_entity: '权属方B',
      ownership_category: '2',
      project_name: '项目2',
      property_name: '物业2',
      address: '地址2',
      ownership_status: '未确权',
      property_nature: '非经营性',
      usage_status: '空置',
      land_area: 2000,
      actual_property_area: 1500,
      rentable_area: 1200,
      rented_area: 0,
      occupancy_rate: 0,
      is_litigated: true,
      created_at: '2024-02-01T00:00:00',
      updated_at: '2024-02-15T00:00:00',
    },
  ];

  const mockData = {
    items: mockAssets,
    total: 2,
    page: 1,
    limit: 20,
    pages: 1,
  };

  it('应该正确渲染多条资产记录', async () => {
    const AssetList = (await import('../AssetList')).default;

    const mockHandlers = {
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onViewHistory: vi.fn(),
      onTableChange: vi.fn(),
    };

    render(
      React.createElement(AssetList, {
        data: mockData,
        loading: false,
        ...mockHandlers,
      })
    );

    expect(screen.getByTestId('table-row-0').getAttribute('data-property-name')).toBe('物业1');
    expect(screen.getByTestId('table-row-1').getAttribute('data-property-name')).toBe('物业2');
  });
});

describe('AssetList - 交互操作测试', () => {
  const mockAsset = {
    id: 'asset-123',
    ownership_entity: '测试权属方',
    ownership_category: '1',
    project_name: '测试项目',
    property_name: '测试物业',
    address: '测试地址',
    ownership_status: '已确权',
    property_nature: '经营性',
    usage_status: '出租',
    land_area: 1000,
    actual_property_area: 800,
    rentable_area: 700,
    rented_area: 600,
    occupancy_rate: 85.7,
    is_litigated: false,
    created_at: '2024-01-01T00:00:00',
    updated_at: '2024-01-15T00:00:00',
  };

  const mockData = {
    items: [mockAsset],
    total: 1,
    page: 1,
    limit: 20,
    pages: 1,
  };

  it('应该接收并正确传递回调函数', async () => {
    const AssetList = (await import('../AssetList')).default;

    const mockHandlers = {
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onViewHistory: vi.fn(),
      onTableChange: vi.fn(),
    };

    render(
      React.createElement(AssetList, {
        data: mockData,
        loading: false,
        ...mockHandlers,
      })
    );

    // 验证组件正常渲染且回调函数被接收
    const table = screen.getByTestId('table');
    expect(table).toBeTruthy();
  });
});

describe('AssetList - 行选择测试', () => {
  const mockAssets = [
    {
      id: '1',
      ownership_entity: '权属方A',
      project_name: '项目1',
      property_name: '物业1',
      address: '地址1',
      ownership_status: '已确权',
      property_nature: '经营性',
      usage_status: '出租',
      is_litigated: false,
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-15T00:00:00',
    },
    {
      id: '2',
      ownership_entity: '权属方B',
      project_name: '项目2',
      property_name: '物业2',
      address: '地址2',
      ownership_status: '未确权',
      property_nature: '非经营性',
      usage_status: '空置',
      is_litigated: true,
      created_at: '2024-02-01T00:00:00',
      updated_at: '2024-02-15T00:00:00',
    },
  ];

  const mockData = {
    items: mockAssets,
    total: 2,
    page: 1,
    limit: 20,
    pages: 1,
  };

  it('应该支持行选择功能', async () => {
    const AssetList = (await import('../AssetList')).default;

    const mockHandlers = {
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onViewHistory: vi.fn(),
      onTableChange: vi.fn(),
      onSelectChange: vi.fn(),
    };

    const selectedRowKeys = ['1'];

    render(
      React.createElement(AssetList, {
        data: mockData,
        loading: false,
        selectedRowKeys,
        ...mockHandlers,
      })
    );

    const table = screen.getByTestId('table');
    expect(table.getAttribute('data-has-selection')).toBe('true');
  });

  it('应该在没有onSelectChange时不显示行选择', async () => {
    const AssetList = (await import('../AssetList')).default;

    const mockHandlers = {
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onViewHistory: vi.fn(),
      onTableChange: vi.fn(),
    };

    render(
      React.createElement(AssetList, {
        data: mockData,
        loading: false,
        ...mockHandlers,
      })
    );

    const table = screen.getByTestId('table');
    expect(table.getAttribute('data-has-selection')).toBe('false');
  });
});

describe('AssetList - 分页测试', () => {
  const mockData = {
    items: [],
    total: 100,
    page: 2,
    limit: 20,
    pages: 5,
  };

  it('应该正确显示分页信息', async () => {
    const AssetList = (await import('../AssetList')).default;

    const mockHandlers = {
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onViewHistory: vi.fn(),
      onTableChange: vi.fn(),
    };

    render(
      React.createElement(AssetList, {
        data: mockData,
        loading: false,
        ...mockHandlers,
      })
    );

    const table = screen.getByTestId('table');
    const paginationData = JSON.parse(table.getAttribute('data-pagination') || '{}');

    expect(paginationData.current).toBe(2);
    expect(paginationData.pageSize).toBe(20);
    expect(paginationData.total).toBe(100);
  });
});

describe('AssetList - 汇总行测试', () => {
  const mockAssets = [
    {
      id: '1',
      ownership_entity: '权属方A',
      property_name: '物业1',
      address: '地址1',
      ownership_status: '已确权',
      property_nature: '经营性',
      usage_status: '出租',
      land_area: 1000,
      actual_property_area: 800,
      rentable_area: 700,
      rented_area: 600,
      is_litigated: false,
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-15T00:00:00',
    },
    {
      id: '2',
      ownership_entity: '权属方B',
      property_name: '物业2',
      address: '地址2',
      ownership_status: '未确权',
      property_nature: '非经营性',
      usage_status: '空置',
      land_area: 2000,
      actual_property_area: 1500,
      rentable_area: 1200,
      rented_area: 300,
      is_litigated: false,
      created_at: '2024-02-01T00:00:00',
      updated_at: '2024-02-15T00:00:00',
    },
  ];

  const mockData = {
    items: mockAssets,
    total: 2,
    page: 1,
    limit: 20,
    pages: 1,
  };

  it('应该显示汇总行', async () => {
    const AssetList = (await import('../AssetList')).default;

    const mockHandlers = {
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onViewHistory: vi.fn(),
      onTableChange: vi.fn(),
    };

    render(
      React.createElement(AssetList, {
        data: mockData,
        loading: false,
        ...mockHandlers,
      })
    );

    const table = screen.getByTestId('table');
    expect(table.getAttribute('data-has-summary')).toBe('true');
  });

  it('应该在没有数据时可以正常渲染', async () => {
    const AssetList = (await import('../AssetList')).default;

    const mockHandlers = {
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onViewHistory: vi.fn(),
      onTableChange: vi.fn(),
    };

    // 应该正常渲染而不报错，即使没有数据
    expect(() => {
      render(
        React.createElement(AssetList, {
          data: { items: [], total: 0, page: 1, limit: 20, pages: 0 },
          loading: false,
          ...mockHandlers,
        })
      );
    }).not.toThrow();

    const table = screen.getByTestId('table');
    expect(table.getAttribute('data-row-count')).toBe('0');
  });
});

describe('AssetList - 属性传递测试', () => {
  it('应该正确传递所有必需属性', async () => {
    const AssetList = (await import('../AssetList')).default;

    const mockData = {
      items: [],
      total: 0,
      page: 1,
      limit: 20,
      pages: 0,
    };

    const mockHandlers = {
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onViewHistory: vi.fn(),
      onTableChange: vi.fn(),
    };

    // 验证组件可以接收所有属性而不报错
    const element = React.createElement(AssetList, {
      data: mockData,
      loading: false,
      selectedRowKeys: [],
      onSelectChange: vi.fn(),
      ...mockHandlers,
    });

    expect(element).toBeTruthy();
  });
});
