/**
 * ActionButtons 组件测试
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ActionButtons from '../ActionButtons';

// Mock PDFImportContext
const mockHandleCancel = vi.fn();
const mockHandleReset = vi.fn();

vi.mock('../PDFImportContext', async () => {
  const actual = await vi.importActual('../PDFImportContext');
  return {
    ...actual,
    usePDFImportContext: vi.fn(() => ({
      uploading: false,
      currentSession: null,
      handleCancel: mockHandleCancel,
      handleReset: mockHandleReset,
    })),
  };
});

import { usePDFImportContext } from '../PDFImportContext';

describe('ActionButtons', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('渲染条件', () => {
    it('当 uploading 为 false 且 currentSession 为 null 时不渲染', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: false,
        currentSession: null,
        handleCancel: mockHandleCancel,
        handleReset: mockHandleReset,
      } as ReturnType<typeof usePDFImportContext>);

      const { container } = render(<ActionButtons />);
      expect(container.firstChild).toBeNull();
    });

    it('当 uploading 为 true 时渲染按钮', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: true,
        currentSession: null,
        handleCancel: mockHandleCancel,
        handleReset: mockHandleReset,
      } as ReturnType<typeof usePDFImportContext>);

      render(<ActionButtons />);
      expect(screen.getByText('取消处理')).toBeInTheDocument();
      expect(screen.getByText('重新开始')).toBeInTheDocument();
    });

    it('当 currentSession 存在时渲染按钮', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: false,
        currentSession: 'session-123',
        handleCancel: mockHandleCancel,
        handleReset: mockHandleReset,
      } as ReturnType<typeof usePDFImportContext>);

      render(<ActionButtons />);
      expect(screen.getByText('取消处理')).toBeInTheDocument();
      expect(screen.getByText('重新开始')).toBeInTheDocument();
    });

    it('当 uploading 为 undefined 且 currentSession 为 undefined 时不渲染', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: undefined,
        currentSession: undefined,
        handleCancel: mockHandleCancel,
        handleReset: mockHandleReset,
      } as unknown as ReturnType<typeof usePDFImportContext>);

      const { container } = render(<ActionButtons />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('按钮交互', () => {
    beforeEach(() => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: true,
        currentSession: 'session-123',
        handleCancel: mockHandleCancel,
        handleReset: mockHandleReset,
      } as ReturnType<typeof usePDFImportContext>);
    });

    it('点击取消按钮调用 handleCancel', () => {
      render(<ActionButtons />);

      const cancelButton = screen.getByText('取消处理');
      fireEvent.click(cancelButton);

      expect(mockHandleCancel).toHaveBeenCalledTimes(1);
    });

    it('点击重新开始按钮调用 handleReset', () => {
      render(<ActionButtons />);

      const resetButton = screen.getByText('重新开始');
      fireEvent.click(resetButton);

      expect(mockHandleReset).toHaveBeenCalledTimes(1);
    });

    it('取消按钮有 danger 样式', () => {
      render(<ActionButtons />);

      const cancelButton = screen.getByText('取消处理');
      expect(cancelButton.closest('button')).toHaveClass('ant-btn-dangerous');
    });
  });

  describe('样式', () => {
    it('按钮容器居中对齐', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: true,
        currentSession: null,
        handleCancel: mockHandleCancel,
        handleReset: mockHandleReset,
      } as ReturnType<typeof usePDFImportContext>);

      render(<ActionButtons />);

      const container = screen.getByText('取消处理').closest('.ant-space')?.parentElement;
      expect(container).not.toBeNull();
      expect(container as HTMLElement).toHaveStyle({ textAlign: 'center' });
    });
  });
});
