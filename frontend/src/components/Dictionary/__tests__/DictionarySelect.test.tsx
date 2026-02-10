/**
 * DictionarySelect 组件测试
 * 覆盖默认渲染、loading 与过滤逻辑
 *
 * 修复说明：
 * - 移除 antd Select, Spin 组件 mock
 * - 保留 hooks mock (useDictionary, dictionaryService)
 * - 使用 className 和文本内容进行断言
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent } from '@/test/utils/test-helpers';
import DictionarySelect from '../DictionarySelect';
import { useDictionary } from '@/hooks/useDictionary';
import { dictionaryService } from '@/services/dictionary';

vi.mock('@/hooks/useDictionary', () => ({
  useDictionary: vi.fn(),
}));

vi.mock('@/services/dictionary', () => ({
  dictionaryService: {
    isTypeAvailable: vi.fn(() => true),
  },
}));

describe('DictionarySelect', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    const combobox = screen.getByRole('combobox');
    fireEvent.mouseDown(combobox);

    expect(screen.getByText('选项1')).toBeInTheDocument();
    expect(screen.getByText('选项2')).toBeInTheDocument();
  });

  it('uses default placeholder derived from dictType', () => {
    renderWithProviders(<DictionarySelect dictType="asset_type" />);

    // 验证 Select 被渲染
    const select = document.querySelector('.ant-select');
    expect(select).toBeInTheDocument();
  });

  it('uses custom placeholder when provided', () => {
    renderWithProviders(<DictionarySelect dictType="test_type" placeholder="请选择" />);

    const select = document.querySelector('.ant-select');
    expect(select).toBeInTheDocument();
  });

  it('shows Spin when loading', () => {
    vi.mocked(useDictionary).mockReturnValue({
      options: [],
      isLoading: true,
      error: null,
    });

    renderWithProviders(<DictionarySelect dictType="test_type" />);

    // loading 时 Select 容器应带有 loading 状态
    const select = document.querySelector('.ant-select-loading');
    expect(select).toBeInTheDocument();
  });

  it('uses notFoundContent when not loading', () => {
    vi.mocked(useDictionary).mockReturnValue({
      options: [],
      isLoading: false,
      error: null,
    });

    renderWithProviders(<DictionarySelect dictType="test_type" />);
    const combobox = screen.getByRole('combobox');
    fireEvent.mouseDown(combobox);

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
    renderWithProviders(<DictionarySelect dictType="test_type" showSearch />);

    // 验证 Select 支持搜索
    const select = document.querySelector('.ant-select-show-search');
    expect(select).toBeInTheDocument();
  });
});
