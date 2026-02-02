/**
 * PDFUploadArea 组件测试
 */

import React from 'react';
import { screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PDFUploadArea from '../PDFUploadArea';

// Mock MessageManager
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
  },
}));

import { MessageManager } from '@/utils/messageManager';

// Mock PDFImportContext
const mockHandleUpload = vi.fn();

vi.mock('../PDFImportContext', () => ({
  usePDFImportContext: vi.fn(() => ({
    uploading: false,
    currentSession: null,
    maxSize: 50,
  })),
  usePDFImportUpload: vi.fn(() => mockHandleUpload),
}));

import { usePDFImportContext } from '../PDFImportContext';

describe('PDFUploadArea', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('渲染条件', () => {
    it('当 currentSession 为 null 时渲染上传区域', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: false,
        currentSession: null,
        maxSize: 50,
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PDFUploadArea />);
      expect(screen.getByText('点击或拖拽文件到此区域上传')).toBeInTheDocument();
    });

    it('当 currentSession 存在时不渲染', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: false,
        currentSession: 'session-123',
        maxSize: 50,
      } as ReturnType<typeof usePDFImportContext>);

      const { container } = renderWithProviders(<PDFUploadArea />);
      expect(container.firstChild).toBeNull();
    });

    it('显示最大文件大小提示', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: false,
        currentSession: null,
        maxSize: 100,
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PDFUploadArea />);
      expect(screen.getByText('支持PDF文件，最大100MB')).toBeInTheDocument();
    });

    it('uploading 为 true 时禁用上传', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: true,
        currentSession: null,
        maxSize: 50,
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PDFUploadArea />);
      const uploadArea = document.querySelector('.ant-upload-disabled');
      expect(uploadArea).toBeInTheDocument();
    });
  });

  describe('文件验证', () => {
    beforeEach(() => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: false,
        currentSession: null,
        maxSize: 50,
      } as ReturnType<typeof usePDFImportContext>);
    });

    it('拒绝非 PDF 文件', async () => {
      renderWithProviders(<PDFUploadArea />);

      const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;

      Object.defineProperty(input, 'files', {
        value: [file],
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(MessageManager.error).toHaveBeenCalledWith('只能上传PDF文件！');
      });
    });

    it('拒绝超过大小限制的文件', async () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: false,
        currentSession: null,
        maxSize: 1, // 1MB
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PDFUploadArea />);

      // 创建一个大于 1MB 的文件
      const largeContent = new Array(1024 * 1024 * 2).fill('a').join('');
      const file = new File([largeContent], 'large.pdf', { type: 'application/pdf' });

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;

      Object.defineProperty(input, 'files', {
        value: [file],
      });

      fireEvent.change(input);

      await waitFor(() => {
        expect(MessageManager.error).toHaveBeenCalledWith('文件大小不能超过 1MB！');
      });
    });

    it('接受有效的 PDF 文件 (通过 MIME 类型)', () => {
      renderWithProviders(<PDFUploadArea />);

      const file = new File(['%PDF-1.4'], 'valid.pdf', { type: 'application/pdf' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;

      // 文件验证通过时不会调用 error
      Object.defineProperty(input, 'files', {
        value: [file],
      });

      fireEvent.change(input);

      // 验证 error 没有被调用（验证通过）
      expect(MessageManager.error).not.toHaveBeenCalled();
    });

    it('接受 .pdf 扩展名的文件', () => {
      renderWithProviders(<PDFUploadArea />);

      // 即使 MIME 类型不是 application/pdf，扩展名是 .pdf 也应该通过
      const file = new File(['content'], 'document.pdf', { type: '' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;

      Object.defineProperty(input, 'files', {
        value: [file],
      });

      fireEvent.change(input);

      expect(MessageManager.error).not.toHaveBeenCalled();
    });
  });

  describe('上传配置', () => {
    it('只允许单文件上传', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: false,
        currentSession: null,
        maxSize: 50,
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PDFUploadArea />);

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      expect(input).not.toHaveAttribute('multiple');
    });

    it('accept 属性正确设置', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: false,
        currentSession: null,
        maxSize: 50,
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PDFUploadArea />);

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      expect(input.getAttribute('accept')).toBe('.pdf,application/pdf');
    });
  });

  describe('UI 元素', () => {
    beforeEach(() => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        uploading: false,
        currentSession: null,
        maxSize: 50,
      } as ReturnType<typeof usePDFImportContext>);
    });

    it('显示上传图标', () => {
      renderWithProviders(<PDFUploadArea />);
      expect(document.querySelector('.ant-upload-drag-icon')).toBeInTheDocument();
    });

    it('显示拖拽提示文本', () => {
      renderWithProviders(<PDFUploadArea />);
      expect(screen.getByText('点击或拖拽文件到此区域上传')).toBeInTheDocument();
    });
  });
});
