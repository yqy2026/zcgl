/**
 * PDF导入上传组件 - 类型定义
 */

import type { UploadFile } from 'antd';
import type { SessionProgress, SystemInfoResponse } from '../../../services/pdfImportService';

export interface EnhancedPDFImportUploaderProps {
  onUploadSuccess: (sessionId: string, fileInfo: UploadFile) => void;
  onUploadError: (error: string) => void;
  maxSize?: number; // MB
  className?: string;
}

export interface ProcessingStep {
  title: string;
  description: string;
  status: 'wait' | 'process' | 'finish' | 'error' | 'uploading' | 'completed' | 'failed';
  progress?: number;
  duration?: number;
}

export interface UploadStats {
  uploadSpeed: number; // KB/s
  estimatedTime: number; // seconds
  fileAnalysis: {
    type: 'scanned' | 'digital' | 'mixed' | 'unknown';
    quality: 'excellent' | 'good' | 'fair' | 'poor';
    recommendedMethod: string;
  };
}

export interface ProcessingOptions {
  prefer_ocr: boolean;
  enable_chinese_optimization: boolean;
  enable_table_detection: boolean;
  enable_seal_detection: boolean;
  confidence_threshold: number;
  use_template_learning: boolean;
  enable_multi_engine_fusion: boolean;
  enable_semantic_validation: boolean;
}

export interface PDFImportContextType {
  // State
  uploading: boolean;
  uploadProgress: number;
  currentSession: string | null;
  processingProgress: SessionProgress | null;
  showAdvancedOptions: boolean;
  systemInfo: SystemInfoResponse | null;
  uploadStats: UploadStats | null;
  processingSteps: ProcessingStep[];
  showPreviewModal: boolean;
  processingOptions: ProcessingOptions;
  maxSize: number;

  // Actions
  setShowAdvancedOptions: (show: boolean) => void;
  setShowPreviewModal: (show: boolean) => void;
  setProcessingOptions: React.Dispatch<React.SetStateAction<ProcessingOptions>>;
  handleCancel: () => void;
  handleReset: () => void;
  getStepIcon: (step: ProcessingStep) => React.ReactNode;
}

export const DEFAULT_PROCESSING_OPTIONS: ProcessingOptions = {
  prefer_ocr: true,
  enable_chinese_optimization: true,
  enable_table_detection: true,
  enable_seal_detection: true,
  confidence_threshold: 0.7,
  use_template_learning: true,
  enable_multi_engine_fusion: true,
  enable_semantic_validation: true,
};
