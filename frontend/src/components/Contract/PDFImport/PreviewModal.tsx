/**
 * 预览模态框组件
 */

import React from 'react';
import { Modal, Button, Typography, Tag, Divider } from 'antd';
import { usePDFImportContext } from './PDFImportContext';

const { Paragraph } = Typography;

// 增强状态类型定义 - 保持灵活性用于显示目的
interface DisplayEnhancedStatus {
  document_analysis?: {
    document_type?: string;
    quality_score?: number;
    recommendations?: string[];
  };
  final_results?: {
    extraction_quality?: {
      overall_quality?: number;
      processing_methods?: string[];
    };
    validation_score?: number;
  };
}

const PreviewModal: React.FC = () => {
  const { showPreviewModal, setShowPreviewModal, processingProgress } = usePDFImportContext();

  // 安全地提取enhanced_status用于显示
  const getEnhancedStatus = (): DisplayEnhancedStatus | undefined => {
    if (processingProgress === null) {
      return undefined;
    }
    // 访问可能存在的enhanced_status属性
    const progress = processingProgress as { enhanced_status?: DisplayEnhancedStatus };
    return progress.enhanced_status;
  };

  const enhancedStatus = getEnhancedStatus();

  return (
    <Modal
      title="处理结果预览"
      open={showPreviewModal}
      onCancel={() => setShowPreviewModal(false)}
      footer={[
        <Button key="close" onClick={() => setShowPreviewModal(false)}>
          关闭
        </Button>,
      ]}
      width={800}
    >
      {processingProgress !== null && (
        <div>
          <Paragraph>
            <Typography.Text strong>处理状态：</Typography.Text>
            <Tag color={processingProgress.status === 'ready_for_review' ? 'green' : 'blue'}>
              {processingProgress.status}
            </Tag>
          </Paragraph>

          {enhancedStatus !== undefined && (
            <div>
              <Divider />
              <Paragraph>
                <Typography.Text strong>文档分析结果：</Typography.Text>
              </Paragraph>
              <ul>
                <li>文档类型：{enhancedStatus.document_analysis?.document_type ?? '未知'}</li>
                <li>质量评分：{enhancedStatus.document_analysis?.quality_score ?? 0}/10</li>
                <li>
                  建议：{enhancedStatus.document_analysis?.recommendations?.join('；') ?? '无'}
                </li>
              </ul>

              <Paragraph>
                <Typography.Text strong>提取质量：</Typography.Text>
              </Paragraph>
              <ul>
                <li>
                  总体质量：{enhancedStatus.final_results?.extraction_quality?.overall_quality ?? 0}
                  /10
                </li>
                <li>验证分数：{enhancedStatus.final_results?.validation_score ?? 0}/10</li>
                <li>
                  处理方法：
                  {enhancedStatus.final_results?.extraction_quality?.processing_methods?.join(
                    '、'
                  ) ?? '未知'}
                </li>
              </ul>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
};

export default PreviewModal;
