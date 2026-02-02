/**
 * PreviewModal 组件测试
 */

import React from 'react';
import { renderWithProviders, screen, fireEvent } from '@/test/utils/test-helpers';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PreviewModal from '../PreviewModal';

// Mock PDFImportContext
const mockSetShowPreviewModal = vi.fn();

vi.mock('../PDFImportContext', () => ({
  usePDFImportContext: vi.fn(() => ({
    showPreviewModal: false,
    setShowPreviewModal: mockSetShowPreviewModal,
    processingProgress: null,
  })),
}));

import { usePDFImportContext } from '../PDFImportContext';

describe('PreviewModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('模态框显示控制', () => {
    it('当 showPreviewModal 为 false 时不显示模态框', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        showPreviewModal: false,
        setShowPreviewModal: mockSetShowPreviewModal,
        processingProgress: null,
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PreviewModal />);

      expect(screen.queryByText('处理结果预览')).not.toBeInTheDocument();
    });

    it('当 showPreviewModal 为 true 时显示模态框', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        showPreviewModal: true,
        setShowPreviewModal: mockSetShowPreviewModal,
        processingProgress: {
          status: 'ready_for_review',
          progress: 100,
        },
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PreviewModal />);

      expect(screen.getByText('处理结果预览')).toBeInTheDocument();
    });
  });

  describe('关闭模态框', () => {
    beforeEach(() => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        showPreviewModal: true,
        setShowPreviewModal: mockSetShowPreviewModal,
        processingProgress: {
          status: 'ready_for_review',
          progress: 100,
        },
      } as ReturnType<typeof usePDFImportContext>);
    });

    it('点击关闭按钮调用 setShowPreviewModal(false)', () => {
      renderWithProviders(<PreviewModal />);

      const closeButton = screen.getByRole('button', { name: /关\s*闭/ });
      fireEvent.click(closeButton);

      expect(mockSetShowPreviewModal).toHaveBeenCalledWith(false);
    });

    it('点击模态框关闭图标调用 setShowPreviewModal(false)', () => {
      renderWithProviders(<PreviewModal />);

      const closeIcon = document.querySelector('.ant-modal-close');
      if (closeIcon) {
        fireEvent.click(closeIcon);
        expect(mockSetShowPreviewModal).toHaveBeenCalledWith(false);
      }
    });
  });

  describe('处理状态显示', () => {
    it('显示处理状态标签', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        showPreviewModal: true,
        setShowPreviewModal: mockSetShowPreviewModal,
        processingProgress: {
          status: 'ready_for_review',
          progress: 100,
        },
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PreviewModal />);

      expect(screen.getByText('处理状态：')).toBeInTheDocument();
      expect(screen.getByText('ready_for_review')).toBeInTheDocument();
    });

    it('ready_for_review 状态显示绿色标签', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        showPreviewModal: true,
        setShowPreviewModal: mockSetShowPreviewModal,
        processingProgress: {
          status: 'ready_for_review',
          progress: 100,
        },
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PreviewModal />);

      const tag = screen.getByText('ready_for_review');
      expect(tag.closest('.ant-tag')).toHaveClass('ant-tag-green');
    });

    it('其他状态显示蓝色标签', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        showPreviewModal: true,
        setShowPreviewModal: mockSetShowPreviewModal,
        processingProgress: {
          status: 'processing',
          progress: 50,
        },
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PreviewModal />);

      const tag = screen.getByText('processing');
      expect(tag.closest('.ant-tag')).toHaveClass('ant-tag-blue');
    });
  });

  describe('处理详情显示', () => {
    it('显示文档分析结果', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        showPreviewModal: true,
        setShowPreviewModal: mockSetShowPreviewModal,
        processingProgress: {
          status: 'ready_for_review',
          progress: 100,
          processing_status: {
            document_analysis: {
              document_type: '租赁合同',
              quality_score: 8,
              recommendations: ['建议核对日期', '检查签名'],
            },
            final_results: {
              extraction_quality: {
                overall_quality: 9,
                processing_methods: ['OCR', 'NLP'],
              },
              validation_score: 7,
            },
          },
        },
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PreviewModal />);

      expect(screen.getByText('文档分析结果：')).toBeInTheDocument();
      expect(screen.getByText(/文档类型：租赁合同/)).toBeInTheDocument();
      expect(screen.getByText(/质量评分：8\/10/)).toBeInTheDocument();
      expect(screen.getByText(/建议核对日期；检查签名/)).toBeInTheDocument();
    });

    it('显示提取质量信息', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        showPreviewModal: true,
        setShowPreviewModal: mockSetShowPreviewModal,
        processingProgress: {
          status: 'ready_for_review',
          progress: 100,
          processing_status: {
            document_analysis: {
              document_type: '租赁合同',
              quality_score: 8,
            },
            final_results: {
              extraction_quality: {
                overall_quality: 9,
                processing_methods: ['OCR', 'NLP'],
              },
              validation_score: 7,
            },
          },
        },
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PreviewModal />);

      expect(screen.getByText('提取质量：')).toBeInTheDocument();
      expect(screen.getByText(/总体质量：9\/10/)).toBeInTheDocument();
      expect(screen.getByText(/验证分数：7\/10/)).toBeInTheDocument();
      expect(screen.getByText(/处理方法：OCR、NLP/)).toBeInTheDocument();
    });

    it('处理 undefined 值时显示默认值', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        showPreviewModal: true,
        setShowPreviewModal: mockSetShowPreviewModal,
        processingProgress: {
          status: 'ready_for_review',
          progress: 100,
          processing_status: {
            document_analysis: {},
            final_results: {
              extraction_quality: {},
            },
          },
        },
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PreviewModal />);

      expect(screen.getByText(/文档类型：未知/)).toBeInTheDocument();
      expect(screen.getByText(/质量评分：0\/10/)).toBeInTheDocument();
      expect(screen.getByText(/建议：无/)).toBeInTheDocument();
    });
  });

  describe('空状态处理', () => {
    it('processingProgress 为 null 时不显示内容', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        showPreviewModal: true,
        setShowPreviewModal: mockSetShowPreviewModal,
        processingProgress: null,
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PreviewModal />);

      expect(screen.queryByText('处理状态：')).not.toBeInTheDocument();
    });

    it('没有 processing_status 时不显示详情', () => {
      vi.mocked(usePDFImportContext).mockReturnValue({
        showPreviewModal: true,
        setShowPreviewModal: mockSetShowPreviewModal,
        processingProgress: {
          status: 'processing',
          progress: 50,
        },
      } as ReturnType<typeof usePDFImportContext>);

      renderWithProviders(<PreviewModal />);

      expect(screen.queryByText('文档分析结果：')).not.toBeInTheDocument();
    });
  });
});
