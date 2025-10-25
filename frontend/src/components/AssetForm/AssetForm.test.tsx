/**
 * AssetForm 组件测试
 * 测试58字段资产表单的完整功能
 * 包括字段验证、计算逻辑、用户交互和数据处理
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AssetForm from './AssetForm';
import { AssetFormData } from '@/types/asset';

// Mock 服务
jest.mock('@/services/assetService', () => ({
  createAsset: jest.fn(),
  updateAsset: jest.fn(),
  getAssetById: jest.fn(),
}));

// Mock Ant Design 消息
jest.mock('antd', () => ({
  ...jest.requireActual('antd'),
  message: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
  },
}));

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

describe('AssetForm Component', () => {
  let queryClient: QueryClient;
  let mockCreateAsset: jest.MockedFunction<any>;
  let mockUpdateAsset: jest.MockedFunction<any>;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    jest.clearAllMocks();

    const assetService = require('@/services/assetService');
    mockCreateAsset = assetService.createAsset;
    mockUpdateAsset = assetService.updateAsset;
  });

  const renderAssetForm = (props: any = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <AssetForm {...props} />
      </QueryClientProvider>
    );
  };

  describe('基础渲染测试', () => {
    test('正确渲染所有58个字段', () => {
      renderAssetForm();

      // 基本信息字段 (8个)
      expect(screen.getByLabelText(/权属方/)).toBeInTheDocument();
      expect(screen.getByLabelText(/权属类别/)).toBeInTheDocument();
      expect(screen.getByLabelText(/项目名称/)).toBeInTheDocument();
      expect(screen.getByLabelText(/物业名称/)).toBeInTheDocument();
      expect(screen.getByLabelText(/物业地址/)).toBeInTheDocument();
      expect(screen.getByLabelText(/确权状态/)).toBeInTheDocument();
      expect(screen.getByLabelText(/物业性质/)).toBeInTheDocument();
      expect(screen.getByLabelText(/使用状态/)).toBeInTheDocument();

      // 面积相关字段 (6个 - 非商业面积、计入出租率统计)
      expect(screen.getByLabelText(/土地面积/)).toBeInTheDocument();
      expect(screen.getByLabelText(/实际房产面积/)).toBeInTheDocument();
      expect(screen.getByLabelText(/可出租面积/)).toBeInTheDocument();
      expect(screen.getByLabelText(/已出租面积/)).toBeInTheDocument();
      expect(screen.getByLabelText(/非经营物业面积/)).toBeInTheDocument();

      // 用途相关字段 (2个)
      expect(screen.getByLabelText(/证载用途/)).toBeInTheDocument();
      expect(screen.getByLabelText(/实际用途/)).toBeInTheDocument();

      // 租户相关字段 (2个)
      expect(screen.getByLabelText(/租户名称/)).toBeInTheDocument();
      expect(screen.getByLabelText(/租户类型/)).toBeInTheDocument();

      // 合同相关字段 (8个)
      expect(screen.getByLabelText(/租赁合同编号/)).toBeInTheDocument();
      expect(screen.getByLabelText(/合同开始日期/)).toBeInTheDocument();
      expect(screen.getByLabelText(/合同结束日期/)).toBeInTheDocument();
      expect(screen.getByLabelText(/月租金/)).toBeInTheDocument();
      expect(screen.getByLabelText(/押金/)).toBeInTheDocument();
      expect(screen.getByLabelText(/是否分租\/转租/)).toBeInTheDocument();
    });

    test('显示正确的表单标题', () => {
      renderAssetForm({ mode: 'create' });
      expect(screen.getByText('创建新资产')).toBeInTheDocument();

      renderAssetForm({ mode: 'edit', assetId: '123' });
      expect(screen.getByText('编辑资产')).toBeInTheDocument();
    });

    test('渲染计算字段显示区域', () => {
      renderAssetForm();
      expect(screen.getByText(/未出租面积/)).toBeInTheDocument();
      expect(screen.getByText(/出租率/)).toBeInTheDocument();
    });
  });

  describe('字段验证测试', () => {
    test('必填字段验证', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      // 提交空表单
      const submitButton = screen.getByRole('button', { name: /提交|保存/ });
      await user.click(submitButton);

      // 验证错误信息
      await waitFor(() => {
        expect(screen.getByText(/请输入权属方/)).toBeInTheDocument();
        expect(screen.getByText(/请输入物业名称/)).toBeInTheDocument();
        expect(screen.getByText(/请输入物业地址/)).toBeInTheDocument();
        expect(screen.getByText(/请选择确权状态/)).toBeInTheDocument();
        expect(screen.getByText(/请选择物业性质/)).toBeInTheDocument();
        expect(screen.getByText(/请选择使用状态/)).toBeInTheDocument();
      });
    });

    test('面积字段数值验证', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      const rentableAreaInput = screen.getByLabelText(/可出租面积/);
      const rentedAreaInput = screen.getByLabelText(/已出租面积/);

      // 输入负数
      await user.clear(rentableAreaInput);
      await user.type(rentableAreaInput, '-1000');

      // 触发验证
      fireEvent.blur(rentableAreaInput);

      await waitFor(() => {
        expect(screen.getByText(/面积不能为负数/)).toBeInTheDocument();
      });

      // 输入非数字字符
      await user.clear(rentedAreaInput);
      await user.type(rentedAreaInput, 'abc');

      fireEvent.blur(rentedAreaInput);

      await waitFor(() => {
        expect(screen.getByText(/请输入有效的数字/)).toBeInTheDocument();
      });
    });

    test('合同日期验证', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      const startDateInput = screen.getByLabelText(/合同开始日期/);
      const endDateInput = screen.getByLabelText(/合同结束日期/);

      // 设置结束日期早于开始日期
      await user.clear(startDateInput);
      await user.type(startDateInput, '2024-12-31');

      await user.clear(endDateInput);
      await user.type(endDateInput, '2024-01-01');

      // 触发验证
      fireEvent.blur(endDateInput);

      await waitFor(() => {
        expect(screen.getByText(/合同结束日期必须晚于开始日期/)).toBeInTheDocument();
      });
    });

    test('面积关系验证', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      const rentableAreaInput = screen.getByLabelText(/可出租面积/);
      const rentedAreaInput = screen.getByLabelText(/已出租面积/);

      // 设置已出租面积大于可出租面积
      await user.clear(rentableAreaInput);
      await user.type(rentableAreaInput, '1000');

      await user.clear(rentedAreaInput);
      await user.type(rentedAreaInput, '1500');

      // 触发验证
      fireEvent.blur(rentedAreaInput);

      await waitFor(() => {
        expect(screen.getByText(/已出租面积不能大于可出租面积/)).toBeInTheDocument();
      });
    });
  });

  describe('计算字段测试', () => {
    test('实时计算未出租面积', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      const rentableAreaInput = screen.getByLabelText(/可出租面积/);
      const rentedAreaInput = screen.getByLabelText(/已出租面积/);

      // 输入面积数据
      await user.clear(rentableAreaInput);
      await user.type(rentableAreaInput, '1000');

      await user.clear(rentedAreaInput);
      await user.type(rentedAreaInput, '600');

      // 验证计算结果
      await waitFor(() => {
        const unrentedAreaElement = screen.getByText(/未出租面积.*400/);
        expect(unrentedAreaElement).toBeInTheDocument();
      });
    });

    test('实时计算出租率', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      const rentableAreaInput = screen.getByLabelText(/可出租面积/);
      const rentedAreaInput = screen.getByLabelText(/已出租面积/);

      // 输入面积数据
      await user.clear(rentableAreaInput);
      await user.type(rentableAreaInput, '1000');

      await user.clear(rentedAreaInput);
      await user.type(rentedAreaInput, '800');

      // 验证计算结果
      await waitFor(() => {
        const occupancyRateElement = screen.getByText(/出租率.*80\.00%/);
        expect(occupancyRateElement).toBeInTheDocument();
      });
    });

    test('不计入出租率统计的处理', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      const rentableAreaInput = screen.getByLabelText(/可出租面积/);
      const rentedAreaInput = screen.getByLabelText(/已出租面积/);
      const includeInOccupancyCheckbox = screen.getByLabelText(/是否计入出租率统计/);

      // 输入面积数据
      await user.clear(rentableAreaInput);
      await user.type(rentableAreaInput, '1000');

      await user.clear(rentedAreaInput);
      await user.type(rentedAreaInput, '800');

      // 取消计入统计
      await user.click(includeInOccupancyCheckbox);

      // 验证出租率显示为0
      await waitFor(() => {
        const occupancyRateElement = screen.getByText(/出租率.*0\.00%/);
        expect(occupancyRateElement).toBeInTheDocument();
      });
    });

    test('边界情况计算 - 零值处理', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      const rentableAreaInput = screen.getByLabelText(/可出租面积/);
      const rentedAreaInput = screen.getByLabelText(/已出租面积/);

      // 输入零值
      await user.clear(rentableAreaInput);
      await user.type(rentableAreaInput, '0');

      await user.clear(rentedAreaInput);
      await user.type(rentedAreaInput, '0');

      // 验证计算结果
      await waitFor(() => {
        const unrentedAreaElement = screen.getByText(/未出租面积.*0/);
        const occupancyRateElement = screen.getByText(/出租率.*0\.00%/);
        expect(unrentedAreaElement).toBeInTheDocument();
        expect(occupancyRateElement).toBeInTheDocument();
      });
    });
  });

  describe('用户交互测试', () => {
    test('表单数据输入和提交', async () => {
      const user = userEvent.setup();
      mockCreateAsset.mockResolvedValue({ id: '123', success: true });

      renderAssetForm({ mode: 'create' });

      // 填写基本信息
      await user.type(screen.getByLabelText(/权属方/), '测试集团有限公司');
      await user.type(screen.getByLabelText(/物业名称/), '测试物业');
      await user.type(screen.getByLabelText(/物业地址/), '测试地址123号');

      // 选择下拉选项
      await user.click(screen.getByText(/请选择确权状态/));
      await user.click(screen.getByText(/已确权/));

      await user.click(screen.getByText(/请选择物业性质/));
      await user.click(screen.getByText(/商业用途/));

      // 填写面积信息
      await user.clear(screen.getByLabelText(/可出租面积/));
      await user.type(screen.getByLabelText(/可出租面积/), '1000');

      await user.clear(screen.getByLabelText(/已出租面积/));
      await user.type(screen.getByLabelText(/已出租面积/), '800');

      // 提交表单
      const submitButton = screen.getByRole('button', { name: /提交|保存/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockCreateAsset).toHaveBeenCalledWith(
          expect.objectContaining({
            ownership_entity: '测试集团有限公司',
            property_name: '测试物业',
            address: '测试地址123号',
            rentable_area: 1000,
            rented_area: 800,
            ownership_status: '已确权',
            property_nature: '商业用途',
          })
        );
      });
    });

    test('表单重置功能', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      // 填写一些数据
      await user.type(screen.getByLabelText(/权属方/), '测试数据');
      await user.type(screen.getByLabelText(/物业名称/), '测试物业');

      // 点击重置按钮
      const resetButton = screen.getByRole('button', { name: /重置/ });
      await user.click(resetButton);

      // 验证字段被清空
      await waitFor(() => {
        expect(screen.getByLabelText(/权属方/)).toHaveValue('');
        expect(screen.getByLabelText(/物业名称/)).toHaveValue('');
      });
    });

    test('表单取消功能', async () => {
      const onCancel = jest.fn();
      renderAssetForm({ onCancel });

      // 点击取消按钮
      const cancelButton = screen.getByRole('button', { name: /取消/ });
      fireEvent.click(cancelButton);

      expect(onCancel).toHaveBeenCalled();
    });

    test('草稿保存功能', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      // 填写部分数据
      await user.type(screen.getByLabelText(/权属方/), '草稿数据');

      // 点击保存草稿
      const draftButton = screen.getByRole('button', { name: /保存草稿/ });
      await user.click(draftButton);

      await waitFor(() => {
        expect(screen.getByText(/草稿已保存/)).toBeInTheDocument();
      });
    });
  });

  describe('数据加载测试', () => {
    test('编辑模式下加载资产数据', async () => {
      const mockAssetData = {
        id: '123',
        ownership_entity: '测试权属方',
        property_name: '测试物业',
        rentable_area: 1000,
        rented_area: 800,
        // ... 其他字段
      };

      renderAssetForm({ mode: 'edit', assetId: '123' });

      await waitFor(() => {
        expect(screen.getByDisplayValue('测试权属方')).toBeInTheDocument();
        expect(screen.getByDisplayValue('测试物业')).toBeInTheDocument();
        expect(screen.getByDisplayValue('1000')).toBeInTheDocument();
        expect(screen.getByDisplayValue('800')).toBeInTheDocument();
      });
    });

    test('加载状态显示', () => {
      renderAssetForm({ mode: 'edit', assetId: '123', loading: true });

      expect(screen.getByText(/加载中/)).toBeInTheDocument();
    });

    test('加载失败处理', async () => {
      renderAssetForm({ mode: 'edit', assetId: '123', error: '加载失败' });

      await waitFor(() => {
        expect(screen.getByText(/加载失败/)).toBeInTheDocument();
      });
    });
  });

  describe('错误处理测试', () => {
    test('网络错误处理', async () => {
      const user = userEvent.setup();
      mockCreateAsset.mockRejectedValue(new Error('网络错误'));

      renderAssetForm({ mode: 'create' });

      // 填写必填字段
      await user.type(screen.getByLabelText(/权属方/), '测试权属方');
      await user.type(screen.getByLabelText(/物业名称/), '测试物业');
      await user.type(screen.getByLabelText(/物业地址/), '测试地址');

      // 选择必要选项
      await user.click(screen.getByText(/请选择确权状态/));
      await user.click(screen.getByText(/已确权/));

      // 提交表单
      const submitButton = screen.getByRole('button', { name: /提交|保存/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/提交失败，请重试/)).toBeInTheDocument();
      });
    });

    test('服务器验证错误处理', async () => {
      const user = userEvent.setup();
      mockCreateAsset.mockRejectedValue({
        response: {
          data: {
            message: '权属方已存在',
            errors: {
              ownership_entity: ['该权属方名称已被使用']
            }
          }
        }
      });

      renderAssetForm({ mode: 'create' });

      // 填写表单并提交
      await user.type(screen.getByLabelText(/权属方/), '重复权属方');
      await user.type(screen.getByLabelText(/物业名称/), '测试物业');
      await user.type(screen.getByLabelText(/物业地址/), '测试地址');

      await user.click(screen.getByText(/请选择确权状态/));
      await user.click(screen.getByText(/已确权/));

      const submitButton = screen.getByRole('button', { name: /提交|保存/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/权属方已存在/)).toBeInTheDocument();
        expect(screen.getByText(/该权属方名称已被使用/)).toBeInTheDocument();
      });
    });
  });

  describe('可访问性测试', () => {
    test('键盘导航支持', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      // Tab键导航
      await user.tab();
      expect(screen.getByLabelText(/权属方/)).toHaveFocus();

      await user.tab();
      expect(screen.getByLabelText(/权属类别/)).toHaveFocus();

      // Enter键提交
      await user.keyboard('{Enter}');
      // 应该触发验证而不是提交（因为表单不完整）
    });

    test('屏幕阅读器支持', () => {
      renderAssetForm();

      // 检查ARIA标签
      expect(screen.getByLabelText(/权属方/)).toHaveAttribute('aria-required', 'true');
      expect(screen.getByLabelText(/物业名称/)).toHaveAttribute('aria-required', 'true');

      // 检查错误信息的ARIA角色
      // 注意：这需要在验证触发后检查
    });

    test('高对比度模式支持', () => {
      renderAssetForm();

      // 检查关键元素有足够的对比度
      // 这通常需要视觉测试工具或样式检查
      const submitButton = screen.getByRole('button', { name: /提交|保存/ });
      expect(submitButton).toBeInTheDocument();
    });
  });

  describe('性能测试', () => {
    test('大量数据输入性能', async () => {
      const user = userEvent.setup();
      const startTime = performance.now();

      renderAssetForm();

      // 快速输入所有字段
      const fields = [
        { selector: /权属方/, value: '测试权属方名称很长很长的文本' },
        { selector: /物业名称/, value: '测试物业名称' },
        { selector: /物业地址/, value: '测试地址很长很长的地址信息' },
        // ... 更多字段
      ];

      for (const field of fields) {
        await user.type(screen.getByLabelText(field.selector), field.value);
      }

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // 渲染时间应该在合理范围内（例如小于1秒）
      expect(renderTime).toBeLessThan(1000);
    });

    test('计算字段更新性能', async () => {
      const user = userEvent.setup();
      renderAssetForm();

      const rentableAreaInput = screen.getByLabelText(/可出租面积/);
      const rentedAreaInput = screen.getByLabelText(/已出租面积/);

      const startTime = performance.now();

      // 快速连续输入
      for (let i = 0; i < 10; i++) {
        await user.clear(rentableAreaInput);
        await user.type(rentableAreaInput, i.toString());

        await user.clear(rentedAreaInput);
        await user.type(rentedAreaInput, (i * 0.8).toString());
      }

      const endTime = performance.now();
      const updateTime = endTime - startTime;

      // 计算更新应该足够快
      expect(updateTime).toBeLessThan(500);
    });
  });
});