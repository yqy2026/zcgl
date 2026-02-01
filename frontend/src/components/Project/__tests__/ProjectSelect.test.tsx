/**
 * ProjectSelect 组件测试
 * 测试项目选择器
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { useQuery } from '@tanstack/react-query';

// Mock @tanstack/react-query
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({
    data: [
      {
        id: '1',
        name: '项目1',
        code: 'PROJ-001',
        children: [
          { id: '1-1', name: '子项目1', code: 'PROJ-001-1', children: [] },
        ],
      },
      { id: '2', name: '项目2', code: 'PROJ-002', children: [] },
    ],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
}));

// Mock services
vi.mock('@/services/projectService', () => ({
  projectService: {
    getProjectTree: vi.fn(() => Promise.resolve([])),
  },
}));

// Mock Ant Design
vi.mock('antd', () => {
  const TreeSelect = ({
    value,
    onChange,
    placeholder,
    treeData,
    multiple,
    allowClear,
    loading,
    disabled,
    showSearch,
  }: {
    value?: string | string[];
    onChange?: (value: string | string[]) => void;
    placeholder?: string;
    treeData?: Array<{ id: string; name: string }>;
    multiple?: boolean;
    allowClear?: boolean;
    loading?: boolean;
    disabled?: boolean;
    showSearch?: boolean;
  }) => (
    <div
      data-testid="tree-select"
      data-value={Array.isArray(value) ? value.join(',') : value}
      data-placeholder={placeholder}
      data-multiple={multiple}
      data-allow-clear={allowClear}
      data-loading={loading}
      data-disabled={disabled}
      data-show-search={showSearch}
      data-has-data={!!treeData?.length}
    >
      <select
        data-testid="select-input"
        value={Array.isArray(value) ? value[0] : value}
        onChange={e => {
          if (multiple) {
            onChange?.([e.target.value]);
          } else {
            onChange?.(e.target.value);
          }
        }}
        disabled={disabled}
      >
        <option value="">{placeholder}</option>
        {treeData?.map(item => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </select>
    </div>
  );
  TreeSelect.displayName = 'MockTreeSelect';

  const Spin = ({ spinning }: { spinning?: boolean }) => (
    <div data-testid="spin" data-spinning={spinning}>
      {spinning ? '加载中...' : null}
    </div>
  );
  Spin.displayName = 'MockSpin';

  const Empty = ({ description }: { description?: string }) => (
    <div data-testid="empty">{description || '暂无数据'}</div>
  );
  Empty.displayName = 'MockEmpty';

  const Tag = ({
    children,
    closable,
    onClose,
  }: {
    children: React.ReactNode;
    closable?: boolean;
    onClose?: () => void;
  }) => (
    <span data-testid="tag" data-closable={closable} onClick={onClose}>
      {children}
    </span>
  );
  Tag.displayName = 'MockTag';

  return {
    TreeSelect,
    Spin,
    Empty,
    Tag,
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => {
  const SearchOutlined = () => <span data-testid="icon-search">SearchIcon</span>;
  const FolderOutlined = () => <span data-testid="icon-folder">FolderIcon</span>;
  const CloseOutlined = () => <span data-testid="icon-close">CloseIcon</span>;
  const LoadingOutlined = () => <span data-testid="icon-loading">LoadingIcon</span>;

  SearchOutlined.displayName = 'SearchOutlined';
  FolderOutlined.displayName = 'FolderOutlined';
  CloseOutlined.displayName = 'CloseOutlined';
  LoadingOutlined.displayName = 'LoadingOutlined';

  return {
    SearchOutlined,
    FolderOutlined,
    CloseOutlined,
    LoadingOutlined,
  };
});

import ProjectSelect from '../ProjectSelect';

describe('ProjectSelect', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('基本渲染', () => {
    it('应该正确渲染TreeSelect组件', () => {
      render(<ProjectSelect />);

      expect(screen.getByTestId('tree-select')).toBeInTheDocument();
    });

    it('应该显示占位符', () => {
      render(<ProjectSelect placeholder="请选择项目" />);

      const treeSelect = screen.getByTestId('tree-select');
      expect(treeSelect).toHaveAttribute('data-placeholder', '请选择项目');
    });

    it('应该加载项目数据', () => {
      render(<ProjectSelect />);

      const treeSelect = screen.getByTestId('tree-select');
      expect(treeSelect).toHaveAttribute('data-has-data', 'true');
    });
  });

  describe('value属性', () => {
    it('应该接受value属性', () => {
      render(<ProjectSelect value="1" />);

      const treeSelect = screen.getByTestId('tree-select');
      expect(treeSelect).toHaveAttribute('data-value', '1');
    });

    it('多选模式应该接受数组value', () => {
      render(<ProjectSelect value={['1', '2']} multiple={true} />);

      const treeSelect = screen.getByTestId('tree-select');
      expect(treeSelect).toHaveAttribute('data-value', '1,2');
    });
  });

  describe('onChange回调', () => {
    it('选择项目应该触发onChange', () => {
      const handleChange = vi.fn();
      render(<ProjectSelect onChange={handleChange} />);

      const selectInput = screen.getByTestId('select-input');
      fireEvent.change(selectInput, { target: { value: '1' } });

      expect(handleChange).toHaveBeenCalledWith('1');
    });

    it('多选模式onChange应该返回数组', () => {
      const handleChange = vi.fn();
      render(<ProjectSelect onChange={handleChange} multiple={true} />);

      const selectInput = screen.getByTestId('select-input');
      fireEvent.change(selectInput, { target: { value: '1' } });

      expect(handleChange).toHaveBeenCalledWith(['1']);
    });
  });

  describe('disabled状态', () => {
    it('disabled时应该不可交互', () => {
      render(<ProjectSelect disabled={true} />);

      const treeSelect = screen.getByTestId('tree-select');
      expect(treeSelect).toHaveAttribute('data-disabled', 'true');
    });

    it('disabled时select应该被禁用', () => {
      render(<ProjectSelect disabled={true} />);

      const selectInput = screen.getByTestId('select-input');
      expect(selectInput).toBeDisabled();
    });
  });

  describe('allowClear属性', () => {
    it('allowClear为true时应该显示清除功能', () => {
      render(<ProjectSelect allowClear={true} value="1" />);

      const treeSelect = screen.getByTestId('tree-select');
      expect(treeSelect).toHaveAttribute('data-allow-clear', 'true');
    });
  });

  describe('多选模式', () => {
    it('multiple为true时应该支持多选', () => {
      render(<ProjectSelect multiple={true} />);

      const treeSelect = screen.getByTestId('tree-select');
      expect(treeSelect).toHaveAttribute('data-multiple', 'true');
    });
  });

  describe('搜索功能', () => {
    it('showSearch为true时应该支持搜索', () => {
      render(<ProjectSelect showSearch={true} />);

      const treeSelect = screen.getByTestId('tree-select');
      expect(treeSelect).toHaveAttribute('data-show-search', 'true');
    });
  });

  describe('加载状态', () => {
    it('加载时应该显示loading', () => {
      vi.mocked(useQuery).mockReturnValueOnce({
        data: undefined,
        isLoading: true,
        isError: false,
        refetch: vi.fn(),
      });

      render(<ProjectSelect />);

      const treeSelect = screen.getByTestId('tree-select');
      expect(treeSelect).toHaveAttribute('data-loading', 'true');
    });
  });

  describe('空状态', () => {
    it('没有数据时应该显示空状态', () => {
      vi.mocked(useQuery).mockReturnValueOnce({
        data: [],
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      });

      render(<ProjectSelect />);

      expect(screen.getByTestId('empty')).toBeInTheDocument();
    });
  });

  describe('默认值', () => {
    it('应该支持defaultValue', () => {
      render(<ProjectSelect defaultValue="1" />);

      expect(screen.getByTestId('tree-select')).toBeInTheDocument();
    });
  });
});
