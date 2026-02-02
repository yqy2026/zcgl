/**
 * DictionarySelect 组件测试
 * 覆盖默认渲染、loading 与过滤逻辑
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@/test/utils/test-helpers';
import type { ReactNode } from 'react';
import type { DictionaryOption } from '../../services/dictionary';

import DictionarySelect from '../DictionarySelect';
import { useDictionary } from '../../hooks/useDictionary';
import { dictionaryService } from '../../services/dictionary';

interface SelectMockProps {
  loading?: boolean;
  placeholder?: string;
  notFoundContent?: ReactNode;
  options?: DictionaryOption[];
  filterOption?: (input: string, option?: DictionaryOption) => boolean;
  virtual?: boolean;
  listHeight?: number;
  showSearch?: boolean;
}

interface SpinMockProps {
  size?: 'small' | 'default' | 'large' | number;
}

let lastFilterOption: SelectMockProps['filterOption'];

vi.mock('../../hooks/useDictionary', () => ({
  useDictionary: vi.fn(),
}));

vi.mock('../../services/dictionary', () => ({
  dictionaryService: {
    isTypeAvailable: vi.fn(() => true),
  },
}));

vi.mock('antd', () => ({
  Select: ({
    loading,
    placeholder,
    notFoundContent,
    options,
    filterOption,
    virtual,
    listHeight,
    showSearch,
  }: SelectMockProps) => {
    lastFilterOption = filterOption;
    return (
      <div
        data-testid="select"
        data-loading={loading}
        data-placeholder={placeholder}
        data-show-search={showSearch}
        data-virtual={virtual}
        data-list-height={listHeight}
      >
        <div data-testid="not-found">{notFoundContent}</div>
        {options?.map(option => (
          <div key={option.value} data-testid="option" data-value={option.value}>
            {option.label}
          </div>
        ))}
      </div>
    );
  },
  Spin: ({ size }: SpinMockProps) => <div data-testid="spin" data-size={size} />,
}));

describe('DictionarySelect', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    lastFilterOption = undefined;
    vi.mocked(useDictionary).mockReturnValue({
      options: [
        { label: '选项1', value: 'opt1' },
        { label: '选项2', value: 'opt2' },
      ],
      isLoading: false,
      error: null,
    });
  });

  it('renders options from useDictionary', () => {
    renderWithProviders(<DictionarySelect dictType="test_type" />);

    const options = screen.getAllByTestId('option');
    expect(options).toHaveLength(2);
    expect(options[0]).toHaveTextContent('选项1');
  });

  it('uses default placeholder derived from dictType', () => {
    renderWithProviders(<DictionarySelect dictType="asset_type" />);

    expect(screen.getByTestId('select')).toHaveAttribute('data-placeholder', '请选择assettype');
  });

  it('uses custom placeholder when provided', () => {
    renderWithProviders(<DictionarySelect dictType="test_type" placeholder="请选择" />);

    expect(screen.getByTestId('select')).toHaveAttribute('data-placeholder', '请选择');
  });

  it('shows Spin when loading', () => {
    vi.mocked(useDictionary).mockReturnValue({
      options: [],
      isLoading: true,
      error: null,
    });

    renderWithProviders(<DictionarySelect dictType="test_type" />);

    expect(screen.getByTestId('spin')).toBeInTheDocument();
  });

  it('uses notFoundContent when not loading', () => {
    vi.mocked(useDictionary).mockReturnValue({
      options: [],
      isLoading: false,
      error: null,
    });

    renderWithProviders(<DictionarySelect dictType="test_type" />);

    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });

  it('invokes useDictionary with dictType and isActive', () => {
    renderWithProviders(<DictionarySelect dictType="test_type" isActive={false} />);

    expect(useDictionary).toHaveBeenCalledWith('test_type', false);
  });

  it('checks dictionary type availability', () => {
    renderWithProviders(<DictionarySelect dictType="test_type" />);

    expect(dictionaryService.isTypeAvailable).toHaveBeenCalledWith('test_type');
  });

  it('filterOption matches string labels', () => {
    renderWithProviders(<DictionarySelect dictType="test_type" />);

    expect(lastFilterOption?.('选项', { label: '选项1', value: 'opt1' })).toBe(true);
    expect(lastFilterOption?.('其他', { label: '选项1', value: 'opt1' })).toBe(false);
  });

  it('filterOption matches React element labels', () => {
    renderWithProviders(<DictionarySelect dictType="test_type" />);

    const labelElement = <span>Alpha</span>;
    expect(lastFilterOption?.('alpha', { label: labelElement, value: 'opt3' })).toBe(true);
  });

  it('enables search and virtual list by default', () => {
    renderWithProviders(<DictionarySelect dictType="test_type" />);

    const select = screen.getByTestId('select');
    expect(select).toHaveAttribute('data-show-search', 'true');
    expect(select).toHaveAttribute('data-virtual', 'true');
    expect(select).toHaveAttribute('data-list-height', '256');
  });
});
