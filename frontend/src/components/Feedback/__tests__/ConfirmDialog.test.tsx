/**
 * ConfirmDialog 组件测试
 * 测试确认对话框组件
 *
 * 修复说明：
 * - 移除 antd Modal, Typography, Space, Button 组件 mock
 * - 移除 @ant-design/icons mock
 * - 使用 className 和文本内容进行断言
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent } from '@/test/utils/test-helpers';
import type { ConfirmType } from '../ConfirmDialog';

describe('ConfirmDialog - 组件导入测试', () => {
  it('应该能够导入ConfirmDialog组件', async () => {
    const module = await import('../ConfirmDialog');
    expect(module).toBeDefined();
    expect(module.ConfirmDialog || module.default).toBeDefined();
  });

  it('应该导出预设组件', async () => {
    const module = await import('../ConfirmDialog');
    expect(module.DeleteConfirmDialog).toBeDefined();
    expect(module.EditConfirmDialog).toBeDefined();
    expect(module.SaveConfirmDialog).toBeDefined();
    expect(module.LogoutConfirmDialog).toBeDefined();
    expect(module.CancelConfirmDialog).toBeDefined();
  });

  it('应该导出便捷方法', async () => {
    const module = await import('../ConfirmDialog');
    expect(module.showDeleteConfirm).toBeDefined();
    expect(typeof module.showDeleteConfirm).toBe('function');
    expect(module.showSaveConfirm).toBeDefined();
    expect(typeof module.showSaveConfirm).toBe('function');
  });
});

describe('ConfirmDialog - 基础渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持title与content属性', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    renderWithProviders(
      <ConfirmDialog
        type="warning"
        visible={true}
        title="自定义标题"
        content={<div>自定义内容</div>}
      />
    );

    expect(screen.getByText('自定义标题')).toBeInTheDocument();
    expect(screen.getByText('自定义内容')).toBeInTheDocument();
  });

  it('visible为false时应该关闭对话框', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    const { container } = renderWithProviders(<ConfirmDialog type="warning" visible={false} />);

    // Modal 不显示时不会渲染到 DOM 中
    expect(container.querySelector('.ant-modal-open')).not.toBeInTheDocument();
  });
});

describe('ConfirmDialog - 预设类型测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each<[ConfirmType, string, string]>([
    ['delete', '确认删除', '删除'],
    ['edit', '确认编辑', '继续编辑'],
    ['save', '确认保存', '保存'],
    ['logout', '确认退出', '退出'],
    ['cancel', '确认取消', '确认取消'],
    ['warning', '警告', '确定'],
    ['info', '提示', '确定'],
  ])('type=%s 应该显示默认标题与按钮文案', async (type, title, okText) => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    renderWithProviders(<ConfirmDialog type={type} visible={true} />);

    const okPattern = new RegExp(String(okText).split('').join('\\s*'));
    expect(screen.getAllByText(String(title)).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { name: okPattern }).length).toBeGreaterThan(0);
  });
});

describe('ConfirmDialog - 回调与配置测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('点击确定应该触发onConfirm', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    const handleConfirm = vi.fn();
    renderWithProviders(<ConfirmDialog type="delete" visible={true} onConfirm={handleConfirm} />);

    fireEvent.click(screen.getByRole('button', { name: /删\s*除/ }));
    expect(handleConfirm).toHaveBeenCalledTimes(1);
  });

  it('点击取消应该触发onCancel', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    const handleCancel = vi.fn();
    renderWithProviders(<ConfirmDialog type="warning" visible={true} onCancel={handleCancel} />);

    fireEvent.click(screen.getByRole('button', { name: /取\s*消/ }));
    expect(handleCancel).toHaveBeenCalledTimes(1);
  });
});

describe('ConfirmDialog - 内容渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('delete类型应显示itemName与itemCount信息', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    renderWithProviders(
      <ConfirmDialog type="delete" visible={true} itemName="测试项目" itemCount={2} />
    );

    expect(screen.getByText('确定要删除这 2 个测试项目吗？')).toBeInTheDocument();
  });

  it('details应渲染在内容区域', async () => {
    const ConfirmDialog = (await import('../ConfirmDialog')).default;
    renderWithProviders(<ConfirmDialog type="save" visible={true} details={['更改1', '更改2']} />);

    expect(screen.getByText('更改1')).toBeInTheDocument();
    expect(screen.getByText('更改2')).toBeInTheDocument();
  });
});

describe('ConfirmDialog - 预设组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('DeleteConfirmDialog应该正确渲染', async () => {
    const { DeleteConfirmDialog } = await import('../ConfirmDialog');
    renderWithProviders(<DeleteConfirmDialog visible={true} />);
    expect(screen.getByText('确认删除')).toBeInTheDocument();
  });

  it('SaveConfirmDialog应该正确渲染', async () => {
    const { SaveConfirmDialog } = await import('../ConfirmDialog');
    renderWithProviders(<SaveConfirmDialog visible={true} />);
    expect(screen.getByText('确认保存')).toBeInTheDocument();
  });
});

describe('ConfirmDialog - 便捷方法测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('showDeleteConfirm应该返回Promise', async () => {
    const { showDeleteConfirm } = await import('../ConfirmDialog');
    const result = showDeleteConfirm({ title: '删除标题' });

    expect(result).toBeInstanceOf(Promise);
  });

  it('showSaveConfirm应该返回Promise', async () => {
    const { showSaveConfirm } = await import('../ConfirmDialog');
    const result = showSaveConfirm({ title: '保存标题' });

    expect(result).toBeInstanceOf(Promise);
  });
});
