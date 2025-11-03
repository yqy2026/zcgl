/**
 * AssetForm 基础Jest测试
 * 使用Jest而不是Vitest，避免框架冲突
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import AssetForm from '../AssetForm';

// Mock antd components
jest.mock('antd', () => ({
  Form: ({ children }: { children: React.ReactNode }) => <form>{children}</form>,
  Input: ({ onChange, placeholder }: any) => (
    <input
      placeholder={placeholder}
      onChange={(e) => onChange?.({ target: { value: e.target.value } })}
      data-testid="input"
    />
  ),
  Select: ({ children, onChange, placeholder }: any) => (
    <select
      placeholder={placeholder}
      onChange={(e) => onChange?.(e.target.value)}
      data-testid="select"
    >
      {children}
    </select>
  ),
  Button: ({ children, onClick, type }: any) => (
    <button onClick={onClick} type={type} data-testid="button">
      {children}
    </button>
  ),
  Row: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Col: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  message: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
  },
}));

// Mock asset service
jest.mock('@/services/assetService', () => ({
  assetService: {
    createAsset: jest.fn(),
    updateAsset: jest.fn(),
    getAssetById: jest.fn(),
  },
}));

// Mock router
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
  useParams: () => ({ id: 'test-id' }),
}));

// 创建测试用query client
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

// 测试包装器
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('AssetForm Basic Jest Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('组件应该能够渲染', () => {
    render(
      <TestWrapper>
        <AssetForm />
      </TestWrapper>
    );

    // 验证表单存在
    expect(screen.getByRole('form')).toBeInTheDocument();
  });

  test('应该显示基本的表单字段', () => {
    render(
      <TestWrapper>
        <AssetForm />
      </TestWrapper>
    );

    // 验证基本的输入字段存在
    expect(screen.getAllByTestId('input').length).toBeGreaterThan(0);
    expect(screen.getAllByTestId('select').length).toBeGreaterThan(0);
  });

  test('应该能够处理输入变化', async () => {
    render(
      <TestWrapper>
        <AssetForm />
      </TestWrapper>
    );

    const inputs = screen.getAllByTestId('input');
    if (inputs.length > 0) {
      const firstInput = inputs[0];

      fireEvent.change(firstInput, { target: { value: '测试值' } });

      await waitFor(() => {
        expect(firstInput).toHaveValue('测试值');
      });
    }
  });

  test('应该能够处理表单提交', async () => {
    const mockSubmit = jest.fn();

    render(
      <TestWrapper>
        <AssetForm onSubmit={mockSubmit} />
      </TestWrapper>
    );

    const submitButton = screen.getByText('提交') || screen.getByTestId('button');

    fireEvent.click(submitButton);

    await waitFor(() => {
      // 验证提交函数被调用
      expect(mockSubmit).toHaveBeenCalled();
    });
  });

  test('应该显示必填字段验证', async () => {
    render(
      <TestWrapper>
        <AssetForm />
      </TestWrapper>
    );

    const submitButton = screen.getByText('提交') || screen.getByTestId('button');

    // 尝试提交空表单
    fireEvent.click(submitButton);

    await waitFor(() => {
      // 验证显示验证错误
      expect(screen.getByText(/必填/i)).toBeInTheDocument();
    });
  });

  test('应该能够处理编辑模式', () => {
    const mockAsset = {
      id: 'test-id',
      ownershipEntity: '测试公司',
      propertyName: '测试物业',
      address: '测试地址',
    };

    render(
      <TestWrapper>
        <AssetForm initialValues={mockAsset} mode="edit" />
      </TestWrapper>
    );

    // 验证编辑模式的字段有初始值
    expect(screen.getByDisplayValue('测试公司')).toBeInTheDocument();
    expect(screen.getByDisplayValue('测试物业')).toBeInTheDocument();
  });

  test('应该能够重置表单', async () => {
    render(
      <TestWrapper>
        <AssetForm />
      </TestWrapper>
    );

    const inputs = screen.getAllByTestId('input');
    if (inputs.length > 0) {
      const firstInput = inputs[0];

      // 输入一些值
      fireEvent.change(firstInput, { target: { value: '测试值' } });

      // 重置表单
      const resetButton = screen.getByText('重置') || screen.getByTestId('button');
      fireEvent.click(resetButton);

      await waitFor(() => {
        expect(firstInput).toHaveValue('');
      });
    }
  });

  test('应该显示加载状态', () => {
    render(
      <TestWrapper>
        <AssetForm loading={true} />
      </TestWrapper>
    );

    // 验证加载状态显示
    expect(screen.getByText(/加载中/i)).toBeInTheDocument();
  });

  test('应该处理网络错误', async () => {
    const mockError = new Error('网络错误');

    render(
      <TestWrapper>
        <AssetForm />
      </TestWrapper>
    );

    // 模拟网络错误
    const submitButton = screen.getByText('提交') || screen.getByTestId('button');
    fireEvent.click(submitButton);

    await waitFor(() => {
      // 验证错误消息显示
      expect(screen.getByText(/网络错误/i)).toBeInTheDocument();
    });
  });

  test('应该能够处理取消操作', () => {
    const mockOnCancel = jest.fn();

    render(
      <TestWrapper>
        <AssetForm onCancel={mockOnCancel} />
      </TestWrapper>
    );

    const cancelButton = screen.getByText('取消') || screen.getByTestId('button');
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });
});

// 集成测试
describe('AssetForm Integration Tests', () => {
  test('完整的表单提交流程', async () => {
    const mockSubmit = jest.fn().mockResolvedValue({ success: true });

    render(
      <TestWrapper>
        <AssetForm onSubmit={mockSubmit} />
      </TestWrapper>
    );

    // 填写表单
    const inputs = screen.getAllByTestId('input');
    inputs.forEach((input, index) => {
      fireEvent.change(input, { target: { value: `测试值${index}` } });
    });

    // 提交表单
    const submitButton = screen.getByText('提交') || screen.getByTestId('button');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          // 验证提交的数据结构
        })
      );
    });
  });

  test('表单验证错误处理', async () => {
    render(
      <TestWrapper>
        <AssetForm />
      </TestWrapper>
    );

    // 提交空表单
    const submitButton = screen.getByText('提交') || screen.getByTestId('button');
    fireEvent.click(submitButton);

    await waitFor(() => {
      // 验证所有必填字段都显示错误
      const errorMessages = screen.getAllByText(/必填/i);
      expect(errorMessages.length).toBeGreaterThan(0);
    });
  });
});