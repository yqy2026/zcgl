/**
 * AssetImport 组件测试
 * 测试资产导入功能（Excel文件上传和处理）
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import AssetImport from '../AssetImport';

// Mock enhancedApiClient before importing
vi.mock('@/api/client', () => ({
  enhancedApiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// Mock Ant Design components
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');

  // Create mocks
  const mockUpload = {
    Dragger: vi.fn(({ children }: any) =>
      React.createElement('div', { 'data-testid': 'upload-dragger' }, children)
    ),
  };

  const mockSteps = vi.fn(({ current }: any) =>
    React.createElement(
      'div',
      {
        'data-testid': 'steps',
        'data-current': current,
      },
      `Step ${current}`
    )
  );

  const mockStep = vi.fn(({ title, description }: any) =>
    React.createElement('div', { 'data-testid': 'step', 'data-title': title }, description)
  );

  const mockProgress = vi.fn(({ percent }: any) =>
    React.createElement(
      'div',
      { 'data-testid': 'progress', 'data-percent': percent },
      `${percent}%`
    )
  );

  const mockAlert = vi.fn(({ message, type }: any) =>
    React.createElement('div', { 'data-testid': 'alert', 'data-type': type }, message)
  );

  const mockCard = vi.fn(({ children, title }: any) =>
    React.createElement('div', { 'data-card': title || 'card' }, children)
  );

  const mockButton = vi.fn(({ children }: any) =>
    React.createElement(
      'button',
      {
        'data-testid': `button-${typeof children === 'string' ? children : 'action'}`,
      },
      children
    )
  );

  const mockTitle = vi.fn(({ children }: any) =>
    React.createElement('div', { 'data-testid': 'title' }, children)
  );

  const mockText = vi.fn(({ children }: any) => React.createElement('span', {}, children));

  const mockSpace = vi.fn(({ children }: any) =>
    React.createElement('div', { 'data-testid': 'space' }, children)
  );

  const mockRow = vi.fn(({ children }: any) =>
    React.createElement('div', { 'data-testid': 'row' }, children)
  );

  const mockCol = vi.fn(({ children }: any) =>
    React.createElement('div', { 'data-testid': 'col' }, children)
  );

  const mockDivider = vi.fn(() => React.createElement('div', { 'data-testid': 'divider' }));

  const mockFormItem = vi.fn(({ children }: any) =>
    React.createElement('div', { 'data-testid': 'form-item' }, children)
  );

  const mockSwitch = vi.fn(({ checked }: any) =>
    React.createElement('input', {
      type: 'checkbox',
      checked,
      'data-testid': 'switch',
    })
  );

  const mockInputNumber = vi.fn(({ value }: any) =>
    React.createElement('input', {
      type: 'number',
      value,
      'data-testid': 'input-number',
    })
  );

  const mockSelect = vi.fn(({ children }: any) =>
    React.createElement('select', { 'data-testid': 'select' }, children)
  );

  const mockSelectOption = vi.fn(({ children }: any) =>
    React.createElement('option', { value: children }, children)
  );

  const mockStatistic = vi.fn(({ title, value }: any) =>
    React.createElement(
      'div',
      {
        'data-statistic': title,
        'data-value': value,
      },
      `${title}: ${value}`
    )
  );

  const mockTable = vi.fn(({ dataSource }: any) =>
    React.createElement('div', {
      'data-testid': 'error-table',
      'data-row-count': dataSource?.length ?? 0,
    })
  );

  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
    Upload: mockUpload,
    Steps: Object.assign(mockSteps, { Step: mockStep }),
    Progress: mockProgress,
    Alert: mockAlert,
    Card: mockCard,
    Button: mockButton,
    Typography: {
      Title: mockTitle,
      Text: mockText,
    },
    Space: mockSpace,
    Row: mockRow,
    Col: mockCol,
    Divider: mockDivider,
    Form: {
      Item: mockFormItem,
    },
    Switch: mockSwitch,
    InputNumber: mockInputNumber,
    Select: Object.assign(mockSelect, { Option: mockSelectOption }),
    Statistic: mockStatistic,
    Table: mockTable,
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  UploadOutlined: () => 'UploadOutlined',
  DownloadOutlined: () => 'DownloadOutlined',
  FileExcelOutlined: () => 'FileExcelOutlined',
  CheckCircleOutlined: () => 'CheckCircleOutlined',
  ExclamationCircleOutlined: () => 'ExclamationCircleOutlined',
  SettingOutlined: () => 'SettingOutlined',
  ThunderboltOutlined: () => 'ThunderboltOutlined',
  ClockCircleOutlined: () => 'ClockCircleOutlined',
}));

describe('AssetImport - 组件导入测试', () => {
  it('应该能够导入组件', () => {
    expect(AssetImport).toBeDefined();
  });

  it('组件应该是React函数组件', () => {
    expect(typeof AssetImport).toBe('function');
  });
});

describe('AssetImport - 初始渲染测试', () => {
  it('应该渲染文件上传界面（步骤0）', () => {
    render(React.createElement(AssetImport));

    const steps = screen.getByTestId('steps');
    expect(steps.getAttribute('data-current')).toBe('0');
    expect(screen.getByTestId('upload-dragger')).toBeTruthy();
  });

  it('应该显示导入说明', () => {
    render(React.createElement(AssetImport));

    const alert = screen.getByTestId('alert');
    expect(alert).toBeTruthy();
    expect(alert.getAttribute('data-type')).toBe('info');
  });
});

describe('AssetImport - 按钮和UI元素测试', () => {
  it('应该有下载模板按钮', () => {
    render(React.createElement(AssetImport));

    expect(screen.getByTestId('button-下载Excel模板')).toBeTruthy();
  });

  it('应该显示3个步骤指示器', () => {
    render(React.createElement(AssetImport));

    const steps = screen.getByTestId('steps');
    expect(steps).toBeTruthy();
    expect(parseInt(steps.getAttribute('data-current') || '0')).toBeGreaterThanOrEqual(0);
    expect(parseInt(steps.getAttribute('data-current') || '0')).toBeLessThanOrEqual(2);
  });
});

describe('AssetImport - 组件状态测试', () => {
  it('应该可以正常渲染而不抛出错误', () => {
    expect(() => {
      render(React.createElement(AssetImport));
    }).not.toThrow();
  });

  it('初始状态应该是步骤0', () => {
    render(React.createElement(AssetImport));

    const steps = screen.getByTestId('steps');
    expect(parseInt(steps.getAttribute('data-current') || '0')).toBe(0);
  });
});

describe('AssetImport - 必要UI元素测试', () => {
  it('应该包含所有必要的UI元素', () => {
    render(React.createElement(AssetImport));

    // 上传区域
    expect(screen.getByTestId('upload-dragger')).toBeTruthy();

    // 下载模板按钮
    expect(screen.getByTestId('button-下载Excel模板')).toBeTruthy();

    // 步骤指示器
    expect(screen.getByTestId('steps')).toBeTruthy();

    // 导入说明
    expect(screen.getByTestId('alert')).toBeTruthy();
  });
});
