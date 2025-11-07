/**
 * 增强PDF导入上传组件测试
 */

import React from "react";
import "@testing-library/jest-dom";
import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";

import EnhancedPDFImportUploader from "../EnhancedPDFImportUploader";
import { pdfImportService } from "../../../services/pdfImportService";

// Mock服务
jest.mock("../../../services/pdfImportService");
const mockPdfImportService = pdfImportService as jest.Mocked<typeof pdfImportService>;

// Mock文件上传
const createMockFile = (name: string, size: number = 1024): File => {
  const file = new File(["mock content"], name, { type: "application/pdf" });
  Object.defineProperty(file, "size", { value: size });
  return file;
};

// 测试组件包装器
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ConfigProvider locale={zhCN}>{children}</ConfigProvider>
);

describe("EnhancedPDFImportUploader", () => {
  const mockOnUploadSuccess = jest.fn();
  const mockOnUploadError = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock系统信息
    mockPdfImportService.getEnhancedSystemInfo.mockResolvedValue({
      success: true,
      system_info: {
        ocr_engines: ["paddleocr", "tesseract"],
        processing_capabilities: ["text_extraction", "table_detection"],
        version: "1.0.0",
      },
    });

    // Mock上传响应
    mockPdfImportService.uploadPDFFileEnhanced.mockResolvedValue({
      success: true,
      session_id: "test-session-123",
      enhanced_status: {
        final_results: {
          extraction_quality: {
            processing_methods: ["hybrid"],
          },
        },
      },
    });

    // Mock进度查询
    mockPdfImportService.getEnhancedProgress.mockResolvedValue({
      success: true,
      session_status: {
        session_id: "test-session-123",
        status: "ready_for_review",
        progress: 100,
        current_step: "处理完成",
        enhanced_status: {
          document_analysis: {
            document_type: "mixed",
            quality_score: 8.5,
            recommendations: ["数据质量良好"],
          },
          final_results: {
            extraction_quality: {
              overall_quality: 9.0,
              validation_score: 8.8,
              processing_methods: ["hybrid", "multi_engine"],
            },
          },
        },
      },
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe("组件渲染", () => {
    it("应该正确渲染基本组件", () => {
      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      expect(screen.getByText("智能PDF导入")).toBeInTheDocument();
      expect(screen.getByText("点击或拖拽文件到此区域上传")).toBeInTheDocument();
      expect(screen.getByText("支持PDF文件，最大50MB")).toBeInTheDocument();
    });

    it("应该显示AI增强标签", async () => {
      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      await waitFor(() => {
        expect(screen.getByText("AI增强")).toBeInTheDocument();
      });
    });

    it("应该显示系统信息提示", async () => {
      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      await waitFor(() => {
        expect(screen.getByText("AI增强PDF处理系统已就绪")).toBeInTheDocument();
        expect(screen.getByText("多引擎处理")).toBeInTheDocument();
        expect(screen.getByText("中文优化")).toBeInTheDocument();
      });
    });

    it("应该显示高级选项按钮", () => {
      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      expect(screen.getByRole("button", { name: /高级选项/ })).toBeInTheDocument();
    });
  });

  describe("文件上传验证", () => {
    it("应该拒绝非PDF文件", async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      const file = new File(["content"], "test.txt", { type: "text/plain" });

      await user.upload(fileInput, file);

      await waitFor(() => {
        expect(screen.getByText("只能上传PDF文件！")).toBeInTheDocument();
      });
    });

    it("应该拒绝过大文件", async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
            maxSize={1} // 1MB限制
          />
        </TestWrapper>,
      );

      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      const file = createMockFile("large.pdf", 2 * 1024 * 1024); // 2MB

      await user.upload(fileInput, file);

      await waitFor(() => {
        expect(screen.getByText("文件大小不能超过 1MB！")).toBeInTheDocument();
      });
    });

    it("应该接受有效的PDF文件", async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      const file = createMockFile("valid.pdf");

      await user.upload(fileInput, file);

      // 不应该显示错误消息
      expect(screen.queryByText(/只能上传PDF文件/)).not.toBeInTheDocument();
      expect(screen.queryByText(/文件大小不能超过/)).not.toBeInTheDocument();
    });
  });

  describe("文件上传流程", () => {
    jest.useFakeTimers();

    it("应该开始上传并显示进度", async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      const file = createMockFile("test.pdf");

      await user.upload(fileInput, file);

      // 显示上传进度
      await waitFor(() => {
        expect(screen.getByText("文件上传成功，开始智能处理...")).toBeInTheDocument();
      });

      // 显示处理步骤
      expect(screen.getByText("文件上传")).toBeInTheDocument();
      expect(screen.getByText("文档分析")).toBeInTheDocument();
      expect(screen.getByText("文本提取")).toBeInTheDocument();
    });

    it("应该处理上传成功", async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      const file = createMockFile("success.pdf");

      await user.upload(fileInput, file);

      await waitFor(() => {
        expect(mockOnUploadSuccess).toHaveBeenCalledWith(
          "test-session-123",
          expect.objectContaining({
            name: "success.pdf",
            status: "done",
          }),
        );
      });

      // 快进时间，触发进度轮询
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      await waitFor(() => {
        expect(screen.getByText("文件处理完成！")).toBeInTheDocument();
      });
    });

    it("应该处理上传失败", async () => {
      const user = userEvent.setup();

      mockPdfImportService.uploadPDFFileEnhanced.mockRejectedValue(new Error("网络错误"));

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      const file = createMockFile("error.pdf");

      await user.upload(fileInput, file);

      await waitFor(() => {
        expect(mockOnUploadError).toHaveBeenCalledWith("网络错误");
        expect(screen.getByText("网络错误")).toBeInTheDocument();
      });
    });
  });

  describe("高级选项", () => {
    it("应该显示/隐藏高级选项", async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const advancedButton = screen.getByRole("button", { name: /高级选项/ });

      // 初始状态不显示高级选项
      expect(screen.queryByText("处理选项")).not.toBeInTheDocument();

      // 点击显示高级选项
      await user.click(advancedButton);

      expect(screen.getByText("处理选项")).toBeInTheDocument();
      expect(screen.getByText("置信度阈值")).toBeInTheDocument();
    });

    it("应该允许修改处理选项", async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      // 打开高级选项
      await user.click(screen.getByRole("button", { name: /高级选项/ }));

      // 修改置信度阈值
      const confidenceSlider = screen.getByRole("slider");
      await user.clear(confidenceSlider);
      await user.type(confidenceSlider, "0.8");

      expect(confidenceSlider).toHaveValue("0.8");

      // 切换OCR选项
      const ocrSwitch = screen.getByRole("switch", { name: /OCR/ });
      await user.click(ocrSwitch);

      expect(ocrSwitch).not.toBeChecked();
    });
  });

  describe("处理步骤显示", () => {
    it("应该正确显示处理步骤状态", async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const file = createMockFile("steps.pdf");
      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      await user.upload(fileInput, file);

      // 检查初始步骤状态
      await waitFor(() => {
        const steps = screen.getAllByRole("listitem");
        expect(steps).toHaveLength(6); // 6个处理步骤
      });

      // 快进时间，模拟处理完成
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      await waitFor(() => {
        expect(screen.getByText("文件处理完成！")).toBeInTheDocument();
      });
    });

    it("应该显示处理失败状态", async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

      mockPdfImportService.getEnhancedProgress.mockResolvedValue({
        success: true,
        session_status: {
          session_id: "test-session-123",
          status: "failed",
          progress: 45,
          error_message: "处理失败：无法识别文档内容",
        },
      });

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const file = createMockFile("failed.pdf");
      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      await user.upload(fileInput, file);

      // 快进时间，触发错误状态
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      await waitFor(() => {
        expect(screen.getByText("处理失败: 无法识别文档内容")).toBeInTheDocument();
      });
    });
  });

  describe("操作按钮", () => {
    it("应该显示取消处理按钮", async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const file = createMockFile("cancel.pdf");
      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      await user.upload(fileInput, file);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /取消处理/ })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /重新开始/ })).toBeInTheDocument();
      });
    });

    it("应该能够取消处理", async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      // 模拟上传中状态
      const file = createMockFile("cancel.pdf");
      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      await user.upload(fileInput, file);

      await waitFor(() => {
        const cancelButton = screen.getByRole("button", { name: /取消处理/ });
        user.click(cancelButton);
      });

      await waitFor(() => {
        expect(screen.getByText("已取消上传")).toBeInTheDocument();
      });
    });
  });

  describe("预览功能", () => {
    it("应该显示预览按钮", async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const file = createMockFile("preview.pdf");
      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      await user.upload(fileInput, file);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /预览处理结果/ })).toBeInTheDocument();
      });
    });

    it("应该显示处理结果预览", async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const file = createMockFile("preview.pdf");
      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      await user.upload(fileInput, file);

      // 快进时间，模拟处理完成
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      // 点击预览按钮
      await waitFor(async () => {
        const previewButton = screen.getByRole("button", { name: /预览处理结果/ });
        await user.click(previewButton);
      });

      await waitFor(() => {
        expect(screen.getByText("处理结果预览")).toBeInTheDocument();
        expect(screen.getByText("处理状态：")).toBeInTheDocument();
        expect(screen.getByText("文档分析结果：")).toBeInTheDocument();
        expect(screen.getByText("提取质量：")).toBeInTheDocument();
      });
    });
  });

  describe("性能测试", () => {
    it("应该在合理时间内完成渲染", () => {
      const startTime = performance.now();

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // 渲染时间应该少于100ms
      expect(renderTime).toBeLessThan(100);
    });

    it("应该正确处理大量状态更新", async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      const file = createMockFile("performance.pdf");
      const fileInput = screen.getByRole("button", { name: /点击或拖拽文件/ });
      await user.upload(fileInput, file);

      // 模拟多个进度更新
      for (let i = 0; i < 10; i++) {
        act(() => {
          jest.advanceTimersByTime(100);
        });
      }

      // 组件应该仍然响应
      expect(screen.getByRole("button", { name: /取消处理/ })).toBeInTheDocument();
    });
  });

  describe("无障碍性测试", () => {
    it("应该有正确的ARIA标签", () => {
      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      // 检查主要元素的ARIA标签
      expect(screen.getByRole("button", { name: /高级选项/ })).toBeInTheDocument();
    });

    it("应该支持键盘导航", async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <EnhancedPDFImportUploader
            onUploadSuccess={mockOnUploadSuccess}
            onUploadError={mockOnUploadError}
          />
        </TestWrapper>,
      );

      // Tab导航到高级选项按钮
      await user.tab();
      await user.tab();

      const advancedButton = screen.getByRole("button", { name: /高级选项/ });
      expect(advancedButton).toHaveFocus();

      // Enter键打开高级选项
      await user.keyboard("{Enter}");

      expect(screen.getByText("处理选项")).toBeInTheDocument();
    });
  });
});
